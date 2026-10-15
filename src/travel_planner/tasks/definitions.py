from crewai import Task

from travel_planner.agents.definitions import (
    budget_analyst,
    destination_researcher,
    hotel_transport_agent,
    itinerary_planner,
    travel_coordinator,
)


def validation_task(request: str) -> Task:
    return Task(description=f"""Validate and normalize this customer request: {request}. Confirm dates, duration, currency, travelers, budget, and preferred activities. Return structured JSON with assumptions and warnings.""", expected_output="Validated travel request JSON.", agent=travel_coordinator())


def destination_task() -> Task:
    return Task(description="Research the destination using web search and weather tools. Find attractions and local experiences matching the request, with costs, duration, location, seasonal notes, warnings, and source URLs. Return structured JSON.", expected_output="Destination research JSON.", agent=destination_researcher())


def logistics_task() -> Task:
    return Task(description="Find and rank transport and hotel options. Include total costs, timing, distances, restrictions, cancellation policies, and price timestamps. Return structured JSON and clearly mark estimates.", expected_output="Logistics JSON.", agent=hotel_transport_agent())


def budget_task() -> Task:
    return Task(description="Calculate transport, hotel, local transport, activities, meals, fees, and contingency. Use the calculator tool. Use the exact currency from the customer request for every amount; convert provider prices where needed and label unavailable prices as estimates. Always return numeric amounts for transport, hotel, food, local transport, attractions, and miscellaneous; calculate the estimated total, compare it numerically with the budget, and report the remaining budget (negative when over budget). The status must be exactly within_budget or over_budget_with_alternatives, never ready or pending. Include specific cheaper alternatives when over budget.", expected_output="Budget report JSON with numeric cost categories, estimated total, exact-currency budget comparison, remaining budget, status, and alternatives.", agent=budget_analyst())


def optimization_task() -> Task:
    return Task(description="The previous budget exceeded the limit. Select cheaper options while preserving the most important preferences, then return revised logistics and a revised budget calculation. Do not change dates unless flexibility is explicitly allowed.", expected_output="Optimized logistics and budget JSON.", agent=hotel_transport_agent())


def itinerary_task() -> Task:
    return Task(description="Create a practical day-by-day itinerary from the supplied research, logistics, weather, and approved budget. Group nearby activities, include travel time and rest, and return structured JSON.", expected_output="Itinerary JSON.", agent=itinerary_planner())


def final_plan_task() -> Task:
    return Task(description="""Review all specialist outputs and produce the final customer-facing travel plan as valid JSON (no markdown fences). Preserve the user's exact currency for every price. Include destination, duration, travel dates, user budget, accommodation options with costs, transport options with costs, a day-by-day itinerary, food estimate, local transport estimate, attraction costs, and a detailed budget breakdown with transport, hotel, food, local transport, attractions, and miscellaneous. Always calculate a numeric estimated_total_cost, compare it against the numeric user budget, set budget_status to exactly "✅ Within Budget" or "⚠️ Over Budget", and calculate remaining_budget (negative when over budget). Never use "ready", "pending", or null for a cost when research/options provide prices; otherwise provide a realistic clearly labeled estimate. Include a brief travel recommendation and mark estimates as estimates, not bookings.""", expected_output="Valid JSON containing a complete, itemized, same-currency travel plan with numeric total, budget status, remaining budget, recommendations, itinerary, transport, and accommodation.", agent=travel_coordinator())
