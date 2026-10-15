# Agentic AI Smart Travel Planning System

A CrewAI travel planner that researches destinations, compares accommodation and transport, calculates a budget, optimizes over-budget trips, and produces a day-by-day itinerary.

## Features

- Five focused CrewAI agents.
- OpenRouter and Ollama LLM configuration.
- Web search, weather, maps, hotel, flight/transport, currency, and calculator tools.
- Structured Pydantic request and result models.
- Explicit demo mode for local execution without paid API keys.
- Bounded budget optimization with recalculation.
- Provider failures are reported to the agents instead of being silently swallowed.

## Quick start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Choose an LLM provider in `.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=ollama/llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

Or use OpenRouter:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=openrouter/openai/gpt-4o-mini
```

For a no-key smoke run:

```bash
DEMO_MODE=true python -m travel_planner.main
```

For a real run, configure the provider API keys in `.env` and run:

```bash
python -m travel_planner.main
```

## Web application

Start the local web interface from the project root:

```bash
source .venv/bin/activate
python -m travel_planner.web
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000). The form creates a
personalized itinerary through the same planner workflow as the CLI. To listen
on a different interface or port, use `python -m travel_planner.web --host
0.0.0.0 --port 8000`.

The sample request can be replaced with a JSON file:

```bash
python -m travel_planner.main --request request.json
```

## Provider configuration

The tool adapters use the following optional integrations:

| Capability | Provider | Environment variables |
|---|---|---|
| Web search | Tavily | `TAVILY_API_KEY` |
| Weather | OpenWeatherMap | `OPENWEATHER_API_KEY` |
| Maps | Google Maps | `GOOGLE_MAPS_API_KEY` |
| Hotels and flights | Amadeus | `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET` |
| Currency | Frankfurter | no key required |

Set `FAIL_ON_MISSING_API=true` to fail fast instead of returning an explicit unavailable result. In normal mode, unavailable providers are surfaced in the task context and final-plan warnings.

## Project layout

```text
src/travel_planner/
├── agents/       Agent definitions
├── config/       Settings and CrewAI YAML configuration
├── crews/        Main and optimization crews
├── models/       Typed request and result contracts
├── services/     Provider clients and workflow orchestration
├── tasks/        Task definitions
├── tools/        CrewAI tool adapters
└── main.py       CLI/sample execution
```

## Notes

Search prices and availability are time-sensitive estimates. The final plan never represents a reservation as confirmed. Live provider APIs may require commercial approval and must be used according to their terms.
