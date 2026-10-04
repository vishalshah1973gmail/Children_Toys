"""Proxy to the Lyzr agent plus a small in-memory rate limiter."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatUnavailable(Exception):
    """The Lyzr agent could not produce a usable reply."""


class RateLimiter:
    """Sliding one-minute window per key. In-process only, which is fine for one instance."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= settings.chat_rate_limit_per_minute:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = RateLimiter()


def _http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.lyzr_timeout_seconds)


async def ask_agent(message: str, session_id: str) -> str:
    """Send one message to the Lyzr agent and return its text reply."""
    body = {  # LYZR SHAPE
        "user_id": session_id,
        "agent_id": settings.lyzr_agent_id,
        "session_id": session_id,
        "message": message,
    }
    headers = {"x-api-key": settings.lyzr_api_key}  # LYZR SHAPE
    try:
        async with _http_client() as client:
            response = await client.post(settings.lyzr_api_url, json=body, headers=headers)
        response.raise_for_status()
        reply = response.json().get("response")  # LYZR SHAPE
    except (httpx.HTTPError, ValueError, AttributeError) as error:
        logger.error("Lyzr request failed: %s", error)
        raise ChatUnavailable(str(error)) from error
    if not isinstance(reply, str) or not reply.strip():
        logger.error("Lyzr reply missing text: %r", reply)
        raise ChatUnavailable("empty or malformed reply")
    return reply.strip()
