from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from travel_planner.config.settings import get_settings

logger = logging.getLogger(__name__)


def retrieved_at() -> str:
    return datetime.now(UTC).isoformat()


class ProviderError(RuntimeError):
    """Raised when an external provider cannot return a usable response."""


def request_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, url, params=params, headers=headers, json=json_body)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError(f"Provider request failed for {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProviderError(f"Provider returned an unexpected response for {url}")
    return payload


def unavailable(provider: str, reason: str) -> dict[str, Any]:
    message = f"{provider} unavailable: {reason}"
    logger.warning(message)
    if get_settings().fail_on_missing_api:
        raise ProviderError(message)
    return {
        "status": "unavailable",
        "provider": provider,
        "reason": reason,
        "retrieved_at": retrieved_at(),
    }
