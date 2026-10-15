from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TravelRequest(BaseModel):
    destination: str = Field(min_length=2)
    starting_location: str = Field(min_length=2)
    travel_start: date
    travel_end: date
    duration_days: int | None = Field(default=None, ge=1, le=90)
    budget: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    preferred_activities: list[str] = Field(default_factory=list)
    travelers: int = Field(default=1, ge=1, le=20)
    flexible_dates: bool = False
    hotel_category: str = "mid-range"

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()

    def model_post_init(self, __context: object) -> None:
        if self.travel_end < self.travel_start:
            raise ValueError("travel_end must be on or after travel_start")
        calculated = (self.travel_end - self.travel_start).days + 1
        if self.duration_days is not None and self.duration_days != calculated:
            raise ValueError("duration_days does not match travel_start and travel_end")
        if self.duration_days is None:
            self.duration_days = calculated

    @property
    def nights(self) -> int:
        return max(self.duration_days - 1, 0)


class SourceReference(BaseModel):
    source: str
    url: str | None = None
    retrieved_at: str


class Activity(BaseModel):
    name: str
    description: str
    category: str
    estimated_cost: float = Field(ge=0)
    currency: str = "USD"
    duration_hours: float = Field(default=2, gt=0)
    location: str
    indoor: bool = False
    source: SourceReference | None = None


class DestinationResearch(BaseModel):
    overview: str
    activities: list[Activity] = Field(default_factory=list)
    weather_summary: str
    seasonal_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)


class TransportOption(BaseModel):
    provider: str
    mode: Literal["flight", "train", "bus", "car", "local_transit", "other"]
    origin: str
    destination: str
    departure: str
    arrival: str
    duration_hours: float = Field(gt=0)
    stops: int = Field(default=0, ge=0)
    total_cost: float = Field(ge=0)
    currency: str = "USD"
    restrictions: list[str] = Field(default_factory=list)
    source: str = "demo"


class HotelOption(BaseModel):
    name: str
    location: str
    nightly_rate: float = Field(ge=0)
    total_cost: float = Field(ge=0)
    currency: str = "USD"
    rating: float = Field(default=0, ge=0, le=5)
    distance_to_center_km: float = Field(default=0, ge=0)
    amenities: list[str] = Field(default_factory=list)
    cancellation_policy: str = "Unknown"
    source: str = "demo"


class LogisticsResult(BaseModel):
    transport_options: list[TransportOption] = Field(default_factory=list)
    hotel_options: list[HotelOption] = Field(default_factory=list)
    local_transport_estimate: float = Field(default=0, ge=0)
    currency: str = "USD"
    warnings: list[str] = Field(default_factory=list)


class BudgetItem(BaseModel):
    category: str
    amount: float = Field(ge=0)
    currency: str = "USD"
    assumption: str


class BudgetReport(BaseModel):
    items: list[BudgetItem] = Field(default_factory=list)
    total_estimated_cost: float = Field(ge=0)
    budget_limit: float = Field(ge=0)
    remaining_or_overage: float
    status: Literal["within_budget", "over_budget_with_alternatives", "over_budget_unavoidable", "insufficient_data"]
    alternatives: list[str] = Field(default_factory=list)
    rounds: int = 0
    warnings: list[str] = Field(default_factory=list)


class ItineraryDay(BaseModel):
    day: int
    date: date
    morning: str
    afternoon: str
    evening: str
    estimated_cost: float = Field(ge=0)
    travel_notes: str = ""


class Itinerary(BaseModel):
    days: list[ItineraryDay] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FinalTravelPlan(BaseModel):
    trip_summary: str
    request: TravelRequest
    destination_research: DestinationResearch
    logistics: LogisticsResult
    budget: BudgetReport
    itinerary: Itinerary
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
