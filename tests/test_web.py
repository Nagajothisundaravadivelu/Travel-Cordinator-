import json
import threading
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from travel_planner.models.contracts import TravelRequest
from travel_planner.web import _add_budget_summary, _parse_plan, create_server


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('```JSON\n{"trip_summary":"Hello"}\n```', {"trip_summary": "Hello"}),
        ('Crew result:\n{"summary":"A trip","itinerary":[{"date":"2027-06-10"}]}', {"summary": "A trip", "itinerary": [{"date": "2027-06-10"}]}),
        ('[{"date":"2027-06-10"}]', {"itinerary": [{"date": "2027-06-10"}]}),
        ('{"final_travel_plan":{"destination_info":{"destination":"Japan"}}}', {"destination_info": {"destination": "Japan"}}),
    ],
)
def test_parse_plan_handles_fenced_and_legacy_json(raw: str, expected: dict) -> None:
    assert _parse_plan(raw) == expected


def test_budget_summary_calculates_total_and_uses_requested_budget() -> None:
    request = TravelRequest.model_validate({
        "destination": "Lisbon",
        "starting_location": "Boston",
        "travel_start": "2027-06-10",
        "travel_end": "2027-06-12",
        "budget": 1000,
        "currency": "USD",
        "travelers": 1,
    })
    plan = _add_budget_summary({
        "destination_info": {"destination": "Lisbon"},
        "transport_options": {"options": [
            {"mode": "flight", "provider": "Air", "total_cost": 280, "currency": "USD"},
            {"mode": "train", "provider": "Rail", "total_cost": 160, "currency": "USD"},
        ]},
        "hotel_options": {"options": [
            {"name": "Central", "total_cost": 330, "nightly_rate": 110, "currency": "USD"},
            {"name": "Budget Inn", "total_cost": 216, "nightly_rate": 72, "currency": "USD"},
        ]},
    }, request)

    summary = plan["budget_summary"]
    assert summary["estimated_total_cost"] == 559.6
    assert summary["budget"] == 1000
    assert summary["budget_status"] == "✅ Within Budget"
    assert summary["remaining_budget"] == 440.4
    assert summary["breakdown"]["transport"]["amount"] == 160
    assert summary["breakdown"]["hotel"]["amount"] == 216
    assert summary["breakdown"]["food"]["estimated"] is True


def test_budget_summary_converts_prices_to_requested_currency(monkeypatch) -> None:
    from travel_planner import web

    monkeypatch.setattr(web, "_exchange_rate", lambda source, target: 80.0)
    request = TravelRequest.model_validate({
        "destination": "Tokyo",
        "starting_location": "Boston",
        "travel_start": "2027-06-10",
        "travel_end": "2027-06-12",
        "budget": 100000,
        "currency": "INR",
        "travelers": 1,
    })
    plan = _add_budget_summary({
        "transport_options": [{"mode": "flight", "total_cost": 100, "currency": "USD"}],
        "hotel_options": [{"name": "Stay", "total_cost": 200, "nightly_rate": 100, "currency": "USD"}],
    }, request)

    summary = plan["budget_summary"]
    assert summary["currency"] == "INR"
    assert summary["breakdown"]["transport"]["amount"] == 8000
    assert summary["breakdown"]["hotel"]["amount"] == 16000
    assert summary["estimated_total_cost"] > 24000


@pytest.fixture
def web_server():
    server = create_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()
    thread.join()


def test_homepage_is_served(web_server: str) -> None:
    with urlopen(web_server) as response:
        html = response.read().decode("utf-8")

    assert response.status == 200
    assert "Let’s plan your trip" in html
    assert 'id="trip-form"' in html


def test_plan_endpoint_runs_planner_and_returns_parsed_plan(web_server: str, monkeypatch) -> None:
    from travel_planner import web

    monkeypatch.setattr(
        web,
        "run_travel_planner",
        lambda request: SimpleNamespace(
            raw=json.dumps({"trip_summary": "A few days in Lisbon", "request": {"destination": "Lisbon"}})
        ),
    )
    payload = {
        "destination": "Lisbon, Portugal",
        "starting_location": "Boston, USA",
        "travel_start": "2027-06-10",
        "travel_end": "2027-06-13",
        "budget": 1600,
        "currency": "USD",
        "preferred_activities": ["local food"],
        "travelers": 1,
    }
    request = Request(
        f"{web_server}/api/plan",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request) as response:
        queued = json.loads(response.read())

    assert response.status == 202
    assert queued["status"] == "queued"
    for _ in range(100):
        with urlopen(f"{web_server}/api/plan/{queued['job_id']}") as response:
            result = json.loads(response.read())
        if result["status"] != "running":
            break
        time.sleep(0.01)

    assert result["status"] == "completed"
    assert result["plan"]["trip_summary"] == "A few days in Lisbon"
    assert "Lisbon" in result["raw"]


def test_plan_endpoint_reports_invalid_request(web_server: str) -> None:
    request = Request(
        f"{web_server}/api/plan",
        data=json.dumps({"destination": "Lisbon"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with pytest.raises(HTTPError) as error:
        urlopen(request)

    assert error.value.code == 422
    assert json.loads(error.value.read())["error"] == "Please correct the travel details."
