from datetime import date

import pytest
from pydantic import ValidationError

from travel_planner.models.contracts import TravelRequest


def test_request_calculates_duration_and_nights() -> None:
    request = TravelRequest(
        destination="Lisbon",
        starting_location="Boston",
        travel_start=date(2026, 6, 10),
        travel_end=date(2026, 6, 13),
        budget=1000,
    )
    assert request.duration_days == 4
    assert request.nights == 3


def test_request_rejects_inconsistent_duration() -> None:
    with pytest.raises(ValidationError):
        TravelRequest(
            destination="Lisbon",
            starting_location="Boston",
            travel_start=date(2026, 6, 10),
            travel_end=date(2026, 6, 13),
            duration_days=3,
            budget=1000,
        )
