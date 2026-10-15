from typing import Type

from pydantic import BaseModel, Field

from travel_planner.tools.base import TravelTool


class CalculatorInput(BaseModel):
    values: list[float] = Field(min_length=1)
    contingency_percent: float = Field(default=0, ge=0, le=100)


class PythonCalculatorTool(TravelTool):
    name: str = "python_calculator"
    description: str = "Safely sum expense values and apply a contingency percentage."
    args_schema: Type[BaseModel] = CalculatorInput

    def run(self, values: list[float], contingency_percent: float = 0) -> dict:
        subtotal = sum(values)
        contingency = subtotal * contingency_percent / 100
        return {
            "status": "ok",
            "subtotal": round(subtotal, 2),
            "contingency": round(contingency, 2),
            "total": round(subtotal + contingency, 2),
        }
