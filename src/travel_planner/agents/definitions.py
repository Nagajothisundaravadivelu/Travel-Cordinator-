from crewai import Agent

from travel_planner.config.settings import get_settings
from travel_planner.tools.calculator import PythonCalculatorTool
from travel_planner.tools.logistics import FlightSearchTool, HotelSearchTool
from travel_planner.tools.maps import MapsTool
from travel_planner.tools.search import WebSearchTool
from travel_planner.tools.weather import WeatherTool


def _llm():
    settings = get_settings()
    kwargs = {"model": settings.llm}
    if settings.llm_provider.lower() == "ollama":
        kwargs["base_url"] = settings.ollama_base_url
    else:
        kwargs["api_key"] = settings.openrouter_api_key
        kwargs["base_url"] = settings.openrouter_base_url
    from crewai import LLM
    return LLM(**kwargs)


def travel_coordinator() -> Agent:
    return Agent(role="Travel Coordinator", goal="Validate requirements, coordinate specialists, resolve conflicts, and produce an accurate final travel plan.", backstory="You are a senior travel coordinator who values explicit assumptions, realistic schedules, and honest pricing.", llm=_llm(), allow_delegation=False, verbose=True)


def destination_researcher() -> Agent:
    return Agent(role="Destination Research Specialist", goal="Find relevant attractions, authentic local experiences, seasonal information, and weather considerations.", backstory="You research from reliable sources and separate verified facts from estimates.", tools=[WebSearchTool(), WeatherTool(), MapsTool()], llm=_llm(), allow_delegation=False, verbose=True)


def hotel_transport_agent() -> Agent:
    return Agent(role="Hotel and Transport Specialist", goal="Compare practical accommodation and transport options with complete costs, timing, and restrictions.", backstory="You are a logistics specialist who optimizes for value without hiding trade-offs.", tools=[HotelSearchTool(), FlightSearchTool(), MapsTool()], llm=_llm(), allow_delegation=False, verbose=True)


def budget_analyst() -> Agent:
    return Agent(role="Budget Analyst", goal="Calculate all trip costs, compare them against the budget, and identify measurable savings.", backstory="You use deterministic calculations and never declare budget compliance without checking every cost category.", tools=[PythonCalculatorTool()], llm=_llm(), allow_delegation=False, verbose=True)


def itinerary_planner() -> Agent:
    return Agent(role="Itinerary Planner", goal="Create a realistic day-by-day plan using the approved research, logistics, weather, and budget.", backstory="You group nearby activities, protect rest time, and avoid impossible schedules.", tools=[MapsTool()], llm=_llm(), allow_delegation=False, verbose=True)
