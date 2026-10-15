from typing import Type

from pydantic import BaseModel, Field

from travel_planner.config.settings import get_settings
from travel_planner.services.provider import request_json, retrieved_at, unavailable
from travel_planner.tools.base import TravelTool


class SearchInput(BaseModel):
    query: str = Field(min_length=3)
    max_results: int = Field(default=5, ge=1, le=10)


class WebSearchTool(TravelTool):
    name: str = "web_search"
    description: str = "Search the web for current destination facts, attractions, and local experiences."
    args_schema: Type[BaseModel] = SearchInput

    def run(self, query: str, max_results: int = 5) -> dict:
        settings = get_settings()
        if settings.demo_mode:
            return {
                "status": "ok",
                "provider": "demo",
                "retrieved_at": retrieved_at(),
                "results": [
                    {"title": f"Official destination information for {query}", "url": "https://example.com", "snippet": "Use official tourism sources to verify opening hours and prices."},
                    {"title": f"Local experiences in {query}", "url": "https://example.com/local", "snippet": "Popular neighborhoods, markets, museums, and walking experiences."},
                ][:max_results],
            }
        if not settings.tavily_api_key:
            return unavailable("Tavily", "TAVILY_API_KEY is not configured")
        return request_json(
            "https://api.tavily.com/search",
            method="POST",
            headers={"Content-Type": "application/json"},
            json_body={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": False,
            },
        )
