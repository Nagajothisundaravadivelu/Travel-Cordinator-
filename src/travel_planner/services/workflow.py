from __future__ import annotations

import json
import logging
from typing import Any

from travel_planner.config.settings import get_settings
from travel_planner.crews.travel_crew import build_completion_crew, build_optimization_crew, build_travel_crew
from travel_planner.models.contracts import BudgetReport, TravelRequest

logger = logging.getLogger(__name__)


def run_travel_planner(request: TravelRequest) -> Any:
    settings = get_settings()
    prompt = json.dumps(request.model_dump(mode="json"), indent=2)
    crew = build_travel_crew(prompt)
    result = crew.kickoff()
    budget = _extract_budget(result)
    for round_number in range(1, settings.max_budget_optimization_rounds + 1):
        if budget is None or budget.status == "within_budget":
            break
        logger.info("Budget optimization round %s of %s", round_number, settings.max_budget_optimization_rounds)
        optimization_prompt = json.dumps(
            {
                "request": request.model_dump(mode="json"),
                "initial_result": _raw_result(result),
                "budget_status": budget.model_dump(mode="json"),
                "round": round_number,
            },
            indent=2,
        )
        result = build_optimization_crew(optimization_prompt).kickoff()
        budget = _extract_budget(result)
    if budget is not None and budget.status != "within_budget":
        logger.warning("No within-budget result was produced after the configured optimization rounds")
    if budget is not None and budget.status != "within_budget":
        completion_prompt = json.dumps(
            {
                "request": request.model_dump(mode="json"),
                "optimized_result": _raw_result(result),
                "budget_status": budget.model_dump(mode="json"),
            },
            indent=2,
        )
        result = build_completion_crew(completion_prompt).kickoff()
    return result


def _raw_result(result: Any) -> Any:
    raw = getattr(result, "raw", result)
    return raw if isinstance(raw, (dict, list)) else str(raw)


def _extract_budget(result: Any) -> BudgetReport | None:
    raw = getattr(result, "raw", result)
    if isinstance(raw, dict):
        candidate = raw.get("budget") or raw.get("budget_report")
        if candidate:
            try:
                return BudgetReport.model_validate(candidate)
            except Exception:
                logger.warning("Crew output contained an invalid budget report")
    if isinstance(raw, str):
        try:
            payload = json.loads(raw)
            candidate = payload.get("budget") or payload.get("budget_report")
            return BudgetReport.model_validate(candidate) if candidate else None
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Crew output was not parseable JSON; budget optimization cannot be evaluated")
    return None


def run_from_dict(payload: dict[str, Any]) -> Any:
    return run_travel_planner(TravelRequest.model_validate(payload))
