from __future__ import annotations

import argparse
from concurrent.futures import Future, ThreadPoolExecutor
from functools import lru_cache
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from threading import Lock
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError

from travel_planner.models.contracts import TravelRequest
from travel_planner.services.workflow import run_travel_planner

logger = logging.getLogger(__name__)
WEB_ROOT = Path(__file__).with_name("web")
MAX_REQUEST_BYTES = 64 * 1024
PLAN_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="travel-plan")
PLAN_JOBS: dict[str, Future[dict[str, Any]]] = {}
PLAN_JOBS_LOCK = Lock()


class TravelPlannerHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        job_match = re.fullmatch(r"/api/plan/([0-9a-f-]{36})", self.path)
        if job_match:
            job_id = job_match.group(1)
            with PLAN_JOBS_LOCK:
                future = PLAN_JOBS.get(job_id)
            if future is None:
                self._send_json(404, {"error": "This travel plan request was not found."})
            elif not future.done():
                self._send_json(200, {"status": "running"})
            else:
                self._send_json(200, future.result())
            return
        if self.path not in {"/", "/index.html"}:
            self.send_error(404, "Not found")
            return
        try:
            page = (WEB_ROOT / "index.html").read_bytes()
        except OSError:
            logger.exception("Could not read the travel planner web interface")
            self.send_error(500, "Web interface is unavailable")
            return
        self._send_response(200, page, "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/api/plan":
            self.send_error(404, "Not found")
            return

        content_length = self.headers.get("Content-Length")
        try:
            body_size = int(content_length) if content_length is not None else -1
        except ValueError:
            body_size = -1
        if body_size < 0:
            self._send_json(400, {"error": "A valid Content-Length header is required."})
            return
        if body_size > MAX_REQUEST_BYTES:
            self._send_json(413, {"error": "The request is too large."})
            return

        try:
            payload = json.loads(self.rfile.read(body_size))
            request = TravelRequest.model_validate(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON."})
            return
        except ValidationError as error:
            self._send_json(
                422,
                {"error": "Please correct the travel details.", "details": error.errors()},
            )
            return

        job_id = str(uuid4())
        future = PLAN_EXECUTOR.submit(_generate_plan, request)
        with PLAN_JOBS_LOCK:
            PLAN_JOBS[job_id] = future
        self._send_json(202, {"job_id": job_id, "status": "queued"})

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self._send_response(status, body, "application/json; charset=utf-8")

    def _send_response(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), format % args)


def _parse_plan(raw: str) -> dict[str, Any] | None:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = candidate[3:].lstrip()
        if candidate[:4].lower() == "json":
            candidate = candidate[4:].lstrip()
        if candidate.endswith("```"):
            candidate = candidate[:-3].rstrip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        parsed = None
        for index, character in enumerate(candidate):
            if character != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate[index:])
                break
            except json.JSONDecodeError:
                continue
    if isinstance(parsed, list):
        return {"itinerary": parsed}
    if isinstance(parsed, dict):
        for wrapper in ("final_travel_plan", "final_plan", "travel_plan"):
            nested = parsed.get(wrapper)
            if isinstance(nested, dict):
                return nested
    return parsed if isinstance(parsed, dict) else None


def _generate_plan(request: TravelRequest) -> dict[str, Any]:
    try:
        result = run_travel_planner(request)
        raw = getattr(result, "raw", result)
        if isinstance(raw, str):
            raw_text = raw
        elif isinstance(raw, (dict, list)):
            raw_text = json.dumps(raw, default=str)
        else:
            raw_text = str(raw)
        plan = _parse_plan(raw_text)
        if plan is not None:
            plan = _add_budget_summary(plan, request)
        return {"status": "completed", "raw": raw_text, "plan": plan}
    except Exception:
        logger.exception("Travel planning request failed")
        return {
            "status": "failed",
            "error": "The travel plan could not be generated. Check the server logs and try again.",
        }


@lru_cache(maxsize=32)
def _exchange_rate(source: str, target: str) -> float:
    if source == target:
        return 1.0
    try:
        response = httpx.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"base": source, "symbols": target},
            timeout=8.0,
        )
        response.raise_for_status()
        rate = response.json()["rates"][target]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"Could not convert {source} prices to {target}: {error}") from error
    if not isinstance(rate, (int, float)) or rate <= 0:
        raise RuntimeError(f"Currency service returned an invalid {source}/{target} rate")
    return float(rate)


def _amount(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if value >= 0 else None
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        try:
            parsed = float(cleaned)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def _options(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    nested = value.get("options")
    if isinstance(nested, list):
        return [item for item in nested if isinstance(item, dict)]
    return [{"mode": key, **item} for key, item in value.items() if isinstance(item, dict)]


def _add_budget_summary(plan: dict[str, Any], request: TravelRequest) -> dict[str, Any]:
    plan = dict(plan)
    destination_info = plan.get("destination_info") or {}
    itinerary = plan.get("itinerary") or {}
    logistics = plan.get("logistics") or {}
    if not isinstance(destination_info, dict):
        destination_info = {}
    if not isinstance(itinerary, dict):
        itinerary = {}
    if not isinstance(logistics, dict):
        logistics = {}

    target_currency = request.currency.upper()
    travelers = request.travelers
    days = request.duration_days or 1
    nights = request.nights

    transport_data = logistics.get("transport_options") or plan.get("transport_options") or plan.get("transport")
    transport_options = _options(transport_data)
    selected_transport = min(
        transport_options,
        key=lambda option: _amount(option.get("total_cost", option.get("cost"))) or float("inf"),
        default={},
    )
    transport_amount = _amount(selected_transport.get("total_cost", selected_transport.get("cost")))
    transport_source_currency = str(selected_transport.get("currency") or "USD").upper()

    hotel_data = logistics.get("hotel_options") or plan.get("hotel_options") or plan.get("hotels")
    hotel_options = _options(hotel_data)
    accommodation = itinerary.get("accommodation")
    if isinstance(accommodation, dict) and (
        _amount(accommodation.get("total_cost")) is not None
        or _amount(accommodation.get("nightly_rate")) is not None
    ):
        selected_hotel = accommodation
    else:
        selected_hotel = min(
            hotel_options,
            key=lambda hotel: _amount(hotel.get("total_cost")) or float("inf"),
            default={},
        )
    hotel_amount = _amount(selected_hotel.get("total_cost"))
    hotel_source_currency = str(selected_hotel.get("currency") or "USD").upper()
    if hotel_amount is None:
        nightly_rate = _amount(selected_hotel.get("nightly_rate"))
        if nightly_rate is not None:
            hotel_amount = nightly_rate * nights

    def convert(amount: float, source_currency: str) -> float:
        return round(amount * _exchange_rate(source_currency, target_currency), 2)

    existing_breakdown = (
        plan.get("budget_breakdown")
        or plan.get("cost_breakdown")
        or plan.get("budget", {}).get("items", [])
        if isinstance(plan.get("budget"), dict)
        else plan.get("budget_breakdown") or plan.get("cost_breakdown") or []
    )
    aliases = {
        "transport": ("transport", "transportation", "flight", "travel"),
        "hotel": ("hotel", "accommodation", "lodging"),
        "food": ("food", "meals", "dining"),
        "local_transport": ("local transport", "local_transport", "ground transport"),
        "attractions": ("attractions", "activities", "sightseeing", "entrance fees"),
        "miscellaneous": ("miscellaneous", "misc", "contingency", "fees"),
    }
    provided_amounts: dict[str, tuple[float, str]] = {}
    if isinstance(existing_breakdown, dict):
        breakdown_entries = [{"category": key, "amount": value} for key, value in existing_breakdown.items()]
    elif isinstance(existing_breakdown, list):
        breakdown_entries = existing_breakdown
    else:
        breakdown_entries = []
    for entry in breakdown_entries:
        if not isinstance(entry, dict):
            continue
        category = str(entry.get("category") or entry.get("name") or "").lower().replace("_", " ")
        amount = _amount(entry.get("amount", entry.get("cost", entry.get("total_cost"))))
        if amount is None:
            continue
        for canonical, category_aliases in aliases.items():
            if any(alias in category for alias in category_aliases):
                provided_amounts[canonical] = (amount, str(entry.get("currency") or target_currency).upper())
                break

    if transport_amount is None:
        transport_amount = 350.0 * travelers
        transport_source_currency = "USD"
        transport_estimated = True
    else:
        transport_estimated = False
    if hotel_amount is None:
        hotel_amount = 90.0 * nights * max(1, (travelers + 1) // 2)
        hotel_source_currency = "USD"
        hotel_estimated = True
    else:
        hotel_estimated = False

    hotel_nightly = _amount(selected_hotel.get("nightly_rate"))
    if hotel_nightly is None and hotel_amount and nights:
        hotel_nightly = hotel_amount / nights
    daily_reference = hotel_nightly or 80.0
    fallback_per_person_day = {
        "food": daily_reference * 0.4,
        "local_transport": daily_reference * 0.15,
        "attractions": daily_reference * 0.2,
        "miscellaneous": daily_reference * 0.1,
    }
    breakdown: dict[str, dict[str, Any]] = {}
    fixed_values = {
        "transport": (transport_amount, transport_source_currency, transport_estimated),
        "hotel": (hotel_amount, hotel_source_currency, hotel_estimated),
    }
    fixed_values.update({
        category: (amount, source_currency, False)
        for category, (amount, source_currency) in provided_amounts.items()
        if category in {"transport", "hotel"}
    })

    def add_item(category: str, amount: float, source_currency: str, estimated: bool) -> None:
        breakdown[category] = {
            "amount": convert(amount, source_currency),
            "currency": target_currency,
            "estimated": estimated,
        }

    for category in ("transport", "hotel"):
        amount, source_currency, estimated = fixed_values[category]
        add_item(category, amount, source_currency, estimated)

    for category, fallback in fallback_per_person_day.items():
        if category in provided_amounts:
            amount, source_currency = provided_amounts[category]
            add_item(category, amount, source_currency, False)
        else:
            add_item(category, fallback * days * travelers, "USD", True)

    total = round(sum(item["amount"] for item in breakdown.values()), 2)
    remaining = round(request.budget - total, 2)
    status = "✅ Within Budget" if remaining >= 0 else "⚠️ Over Budget"
    hotel_name = selected_hotel.get("name") or selected_hotel.get("hotel_name") or "Recommended available stay"
    transport_name = selected_transport.get("mode") or selected_transport.get("provider") or "Recommended available transport"
    recommendation = (
        f"Estimated at {total:,.2f} {target_currency}, this trip is "
        f"{'within' if remaining >= 0 else 'over'} your {request.budget:,.2f} {target_currency} budget. "
        f"Best listed options: {transport_name} and {hotel_name}. "
        "Unpriced daily categories are clearly marked estimates."
    )
    plan["budget_summary"] = {
        "currency": target_currency,
        "budget": request.budget,
        "breakdown": breakdown,
        "estimated_total_cost": total,
        "budget_status": status,
        "remaining_budget": remaining,
        "recommendation": recommendation,
        "transport_option": selected_transport,
        "hotel_option": selected_hotel,
    }
    plan.setdefault("destination_info", {}).setdefault("destination", request.destination)
    plan.setdefault("itinerary", {}).setdefault("travel_dates", {
        "start": request.travel_start.isoformat(),
        "end": request.travel_end.isoformat(),
    })
    return plan


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), TravelPlannerHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the smart travel planner web application.")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000).")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    server = create_server(args.host, args.port)
    logger.info("Travel planner web app is running at http://%s:%s", *server.server_address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down the travel planner web app")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
