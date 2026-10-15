from crewai import Crew, Process

from travel_planner.agents.definitions import (
    budget_analyst,
    destination_researcher,
    hotel_transport_agent,
    itinerary_planner,
    travel_coordinator,
)
from travel_planner.tasks.definitions import (
    budget_task,
    destination_task,
    final_plan_task,
    itinerary_task,
    logistics_task,
    validation_task,
)


def build_travel_crew(request: str) -> Crew:
    coordinator = travel_coordinator()
    researcher = destination_researcher()
    logistics = hotel_transport_agent()
    budget = budget_analyst()
    planner = itinerary_planner()
    tasks = [
        validation_task(request),
        destination_task(),
        logistics_task(),
        budget_task(),
        itinerary_task(),
        final_plan_task(),
    ]
    tasks[0].agent = coordinator
    tasks[1].agent = researcher
    tasks[2].agent = logistics
    tasks[3].agent = budget
    tasks[4].agent = planner
    tasks[5].agent = coordinator
    return Crew(agents=[coordinator, researcher, logistics, budget, planner], tasks=tasks, process=Process.sequential, verbose=True)


def build_optimization_crew(request: str) -> Crew:
    """Build a small second pass used only when the first budget is over limit."""
    coordinator = travel_coordinator()
    logistics = hotel_transport_agent()
    budget = budget_analyst()
    from travel_planner.tasks.definitions import optimization_task

    optimize = optimization_task()
    optimize.agent = logistics
    recalculate = budget_task()
    recalculate.agent = budget
    return Crew(
        agents=[coordinator, logistics, budget],
        tasks=[optimize, recalculate],
        process=Process.sequential,
        verbose=True,
    )


def build_completion_crew(request: str) -> Crew:
    """Finish itinerary and final-plan generation after an optimization pass."""
    planner = itinerary_planner()
    coordinator = travel_coordinator()
    itinerary = itinerary_task()
    itinerary.agent = planner
    final = final_plan_task()
    final.agent = coordinator
    return Crew(
        agents=[planner, coordinator],
        tasks=[itinerary, final],
        process=Process.sequential,
        verbose=True,
    )
