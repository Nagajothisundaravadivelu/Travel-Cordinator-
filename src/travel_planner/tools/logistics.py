from typing import Type

from pydantic import BaseModel, Field

from travel_planner.config.settings import get_settings
from travel_planner.services.provider import request_json, retrieved_at, unavailable
from travel_planner.tools.base import TravelTool


class HotelInput(BaseModel):
    destination: str = Field(min_length=2)
    check_in: str
    check_out: str
    travelers: int = Field(default=1, ge=1)
    hotel_category: str = "mid-range"


class HotelSearchTool(TravelTool):
    name: str = "hotel_search"
    description: str = "Find hotel options with rates, ratings, and cancellation information."
    args_schema: Type[BaseModel] = HotelInput

    def run(self, destination: str, check_in: str, check_out: str, travelers: int = 1, hotel_category: str = "mid-range") -> dict:
        settings = get_settings()
        if settings.demo_mode:
            return {"status": "ok", "provider": "demo", "retrieved_at": retrieved_at(), "options": [{"name": f"{destination} Central Hotel", "location": "Central district", "nightly_rate": 110, "total_cost": 330, "currency": "USD", "rating": 4.2, "distance_to_center_km": 1.2, "amenities": ["Wi-Fi", "Breakfast"], "cancellation_policy": "Free cancellation until 48 hours before check-in"}, {"name": f"{destination} Budget Inn", "location": "Transit district", "nightly_rate": 72, "total_cost": 216, "currency": "USD", "rating": 3.8, "distance_to_center_km": 3.5, "amenities": ["Wi-Fi"], "cancellation_policy": "Non-refundable"}]}
        if not (settings.amadeus_client_id and settings.amadeus_client_secret):
            return unavailable("Amadeus Hotels", "AMADEUS_CLIENT_ID/AMADEUS_CLIENT_SECRET are not configured")
        return unavailable("Amadeus Hotels", "OAuth token acquisition and offer normalization must be configured for production")


class TransportInput(BaseModel):
    origin: str = Field(min_length=2)
    destination: str = Field(min_length=2)
    departure_date: str
    return_date: str
    travelers: int = Field(default=1, ge=1)


class FlightSearchTool(TravelTool):
    name: str = "flight_transport_search"
    description: str = "Find flight or transport options and estimated fares."
    args_schema: Type[BaseModel] = TransportInput

    def run(self, origin: str, destination: str, departure_date: str, return_date: str, travelers: int = 1) -> dict:
        settings = get_settings()
        if settings.demo_mode:
            return {"status": "ok", "provider": "demo", "retrieved_at": retrieved_at(), "options": [{"provider": "Demo Air", "mode": "flight", "origin": origin, "destination": destination, "departure": f"{departure_date}T09:00", "arrival": f"{departure_date}T12:00", "duration_hours": 3, "stops": 0, "total_cost": 280, "currency": "USD", "restrictions": ["Estimated fare"]}, {"provider": "Demo Rail", "mode": "train", "origin": origin, "destination": destination, "departure": f"{departure_date}T07:30", "arrival": f"{departure_date}T14:30", "duration_hours": 7, "stops": 1, "total_cost": 160, "currency": "USD", "restrictions": ["Estimated fare"]}]}
        if not (settings.amadeus_client_id and settings.amadeus_client_secret):
            return unavailable("Amadeus Flights", "AMADEUS_CLIENT_ID/AMADEUS_CLIENT_SECRET are not configured")
        return unavailable("Amadeus Flights", "OAuth token acquisition and offer normalization must be configured for production")
