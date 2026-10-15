from __future__ import annotations

import logging
import os
from datetime import date, timedelta

import httpx
import streamlit as st
from pydantic import ValidationError

from travel_planner.config.settings import get_settings
from travel_planner.models.contracts import TravelRequest
from travel_planner.services.workflow import run_travel_planner

_SECRET_NAMES = (
    "LLM_PROVIDER",
    "OLLAMA_MODEL",
    "OLLAMA_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "OPENROUTER_BASE_URL",
    "DEMO_MODE",
    "FAIL_ON_MISSING_API",
    "MAX_BUDGET_OPTIMIZATION_ROUNDS",
    "CONTINGENCY_PERCENT",
    "TAVILY_API_KEY",
    "OPENWEATHER_API_KEY",
    "GOOGLE_MAPS_API_KEY",
    "AMADEUS_CLIENT_ID",
    "AMADEUS_CLIENT_SECRET",
)
logger = logging.getLogger(__name__)


def _load_streamlit_secrets() -> None:
    try:
        secrets = st.secrets
        for name in _SECRET_NAMES:
            value = secrets.get(name)
            if value is not None and str(value).strip() and not os.environ.get(name):
                os.environ[name] = str(value)
    except FileNotFoundError:
        return


_load_streamlit_secrets()

st.set_page_config(page_title="Wayfarer Travel Planner", page_icon="✈️", layout="centered")
st.title("Wayfarer Travel Planner")
st.write("Build a personalized itinerary with destination research, transport, stays, and a budget.")

settings = get_settings()
if settings.llm_provider.lower() == "openrouter" and not settings.openrouter_api_key:
    st.warning("Add OPENROUTER_API_KEY to Streamlit Cloud → Settings → Secrets before generating a plan.")
elif settings.llm_provider.lower() == "ollama":
    st.info("Ollama must be reachable at the configured OLLAMA_BASE_URL from the deployed app.")

with st.form("travel_request"):
    destination = st.text_input("Destination", placeholder="Lisbon, Portugal")
    starting_location = st.text_input("Starting location", placeholder="Boston, USA")
    start_col, end_col = st.columns(2)
    with start_col:
        travel_start = st.date_input("Departure", value=date.today() + timedelta(days=14))
    with end_col:
        travel_end = st.date_input("Return", value=date.today() + timedelta(days=17))
    budget_col, currency_col = st.columns(2)
    with budget_col:
        budget = st.number_input("Total budget", min_value=1.0, value=1600.0, step=100.0)
    with currency_col:
        currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD", "AUD", "INR"])
    travelers = st.number_input("Travelers", min_value=1, max_value=20, value=1, step=1)
    hotel_category = st.selectbox("Hotel category", ["budget", "mid-range", "luxury"], index=1)
    activities = st.text_input("Preferred activities", placeholder="local food, museums, coastal views")
    flexible_dates = st.checkbox("My travel dates are flexible")
    submitted = st.form_submit_button("Create my itinerary", type="primary")

if submitted:
    try:
        request = TravelRequest(
            destination=destination,
            starting_location=starting_location,
            travel_start=travel_start,
            travel_end=travel_end,
            budget=budget,
            currency=currency,
            preferred_activities=[item.strip() for item in activities.split(",") if item.strip()],
            travelers=travelers,
            flexible_dates=flexible_dates,
            hotel_category=hotel_category,
        )
    except ValidationError as error:
        st.error("Please check the travel details.")
        for issue in error.errors():
            field = ".".join(str(part) for part in issue["loc"]) or "request"
            st.write(f"- {field}: {issue['msg']}")
    else:
        if settings.llm_provider.lower() == "openrouter" and not settings.openrouter_api_key:
            st.error("OpenRouter is selected, but OPENROUTER_API_KEY is not configured.")
        else:
            try:
                with st.spinner("Researching your trip and building the itinerary..."):
                    result = run_travel_planner(request)
                raw_result = getattr(result, "raw", result)
                st.subheader("Your travel plan")
                st.code(str(raw_result))
            except (httpx.ConnectError, ConnectionError):
                logger.exception("Could not connect to the configured LLM provider")
                st.error(
                    "Could not connect to the configured LLM provider. Check the provider base URL, "
                    "Streamlit Cloud secrets, and whether the deployment can reach that provider."
                )
            except Exception as error:
                logger.exception("Travel plan generation failed")
                st.error(f"Travel plan generation failed ({type(error).__name__}). Check the app logs.")
