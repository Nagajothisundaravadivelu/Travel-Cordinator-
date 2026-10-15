from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from travel_planner.models.contracts import TravelRequest
from travel_planner.services.workflow import run_travel_planner


SAMPLE_REQUEST = {
    "destination": "Lisbon, Portugal",
    "starting_location": "Boston, USA",
    "travel_start": "2026-06-10",
    "travel_end": "2026-06-13",
    "budget": 1600,
    "currency": "USD",
    "preferred_activities": ["local food", "historic neighborhoods", "coastal views"],
    "travelers": 1,
    "flexible_dates": False,
    "hotel_category": "mid-range",
}


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the CrewAI smart travel planner.")
    parser.add_argument("--request", type=Path, help="Path to a JSON travel request.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    payload = json.loads(args.request.read_text()) if args.request else SAMPLE_REQUEST
    request = TravelRequest.model_validate(payload)
    result = run_travel_planner(request)
    if hasattr(result, "raw"):
        print(result.raw)
    else:
        print(result)


if __name__ == "__main__":
    main()
