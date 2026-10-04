"""Tests for POST /api/chat with Lyzr mocked."""

import pytest

from app.core.config import settings
from app.services import chat_service

VALID = {"message": "How much is shipping?", "session_id": "abcd1234-session"}


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    monkeypatch.setattr(settings, "lyzr_api_key", "test-key")
    monkeypatch.setattr(settings, "lyzr_agent_id", "test-agent")
    chat_service.rate_limiter.reset()


def test_returns_agent_reply(client, monkeypatch):
    async def fake(message, session_id):
        return "Shipping is $5.99."

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    response = client.post("/api/chat", json=VALID)
    assert response.status_code == 200
    assert response.json() == {"reply": "Shipping is $5.99."}


@pytest.mark.parametrize("message", ["", "   ", "x" * 501])
def test_rejects_bad_messages_without_calling_lyzr(client, monkeypatch, message):
    async def boom(message, session_id):
        raise AssertionError("Lyzr must not be called")

    monkeypatch.setattr(chat_service, "ask_agent", boom)
    response = client.post("/api/chat", json={**VALID, "message": message})
    assert response.status_code == 422


def test_rejects_bad_session_id(client):
    response = client.post("/api/chat", json={**VALID, "session_id": "no spaces/allowed!"})
    assert response.status_code == 422


def test_lyzr_failure_is_503_with_friendly_message(client, monkeypatch):
    async def fail(message, session_id):
        raise chat_service.ChatUnavailable("timeout")

    monkeypatch.setattr(chat_service, "ask_agent", fail)
    response = client.post("/api/chat", json=VALID)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "chat_unavailable"


def test_missing_key_is_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "lyzr_api_key", "")
    response = client.post("/api/chat", json=VALID)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "chat_not_configured"


def test_rate_limit_returns_429(client, monkeypatch):
    async def ok(message, session_id):
        return "ok"

    monkeypatch.setattr(chat_service, "ask_agent", ok)
    for _ in range(settings.chat_rate_limit_per_minute):
        assert client.post("/api/chat", json=VALID).status_code == 200
    response = client.post("/api/chat", json=VALID)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


def test_service_parses_reply_and_rejects_malformed(monkeypatch):
    import asyncio

    import httpx

    def make_client(payload, status=200):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status, json=payload)

        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(chat_service, "_http_client", lambda: make_client({"response": "Hi!"}))
    assert asyncio.run(chat_service.ask_agent("hello", "abcd1234")) == "Hi!"

    monkeypatch.setattr(chat_service, "_http_client", lambda: make_client({"nope": 1}))
    with pytest.raises(chat_service.ChatUnavailable):
        asyncio.run(chat_service.ask_agent("hello", "abcd1234"))

    monkeypatch.setattr(chat_service, "_http_client", lambda: make_client({}, status=500))
    with pytest.raises(chat_service.ChatUnavailable):
        asyncio.run(chat_service.ask_agent("hello", "abcd1234"))
