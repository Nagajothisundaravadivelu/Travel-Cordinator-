from typing import Type

from pydantic import BaseModel, Field

from travel_planner.config.settings import get_settings
from travel_planner.services.provider import request_json, retrieved_at, unavailable
from travel_planner.tools.base import TravelTool


class WeatherInput(BaseModel):
    destination: str = Field(min_length=2)
    start_date: str
    end_date: str


class WeatherTool(TravelTool):
    name: str = "weather"
    description: str = "Retrieve forecast or seasonal weather information for a destination."
    args_schema: Type[BaseModel] = WeatherInput

    def run(self, destination: str, start_date: str, end_date: str) -> dict:
        settings = get_settings()
        if settings.demo_mode:
            return {"status": "ok", "provider": "demo", "retrieved_at": retrieved_at(), "summary": f"Mild seasonal weather expected in {destination} from {start_date} to {end_date}. Check the forecast closer to departure.", "forecast": []}
        if not settings.openweather_api_key:
            return unavailable("OpenWeatherMap", "OPENWEATHER_API_KEY is not configured")
        return request_json("https://api.openweathermap.org/data/2.5/forecast", params={"q": destination, "appid": settings.openweather_api_key, "units": "metric"})
