from travel_planner.tools.calculator import PythonCalculatorTool


def test_calculator_applies_contingency() -> None:
    result = PythonCalculatorTool().run([100, 50], 10)
    assert result["subtotal"] == 150
    assert result["total"] == 165
