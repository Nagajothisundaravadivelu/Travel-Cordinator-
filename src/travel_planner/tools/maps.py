from typing import Type

from pydantic import BaseModel, Field

from travel_planner.config.settings import get_settings
from travel_planner.services.provider import request_json, retrieved_at, unavailable
from travel_planner.tools.base import TravelTool


class MapsInput(BaseModel):
    origin: str = Field(min_length=2)
    destination: str = Field(min_length=2)
    mode: str = "transit"


class MapsTool(TravelTool):
    name: str = "maps"
    description: str = "Estimate route distance and travel time between two places."
    args_schema: Type[BaseModel] = MapsInput

    def run(self, origin: str, destination: str, mode: str = "transit") -> dict:
        settings = get_settings()
        if settings.demo_mode:
            return {"status": "ok", "provider": "demo", "retrieved_at": retrieved_at(), "origin": origin, "destination": destination, "mode": mode, "distance_km": 5.0, "duration_minutes": 25}
        if not settings.google_maps_api_key:
            return unavailable("Google Maps", "GOOGLE_MAPS_API_KEY is not configured")
        return request_json("https://maps.googleapis.com/maps/api/directions/json", params={"origin": origin, "destination": destination, "mode": mode, "key": settings.google_maps_api_key})
