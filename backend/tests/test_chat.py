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


from tests.conftest import auth_headers  # noqa: E402


@pytest.fixture(autouse=True)
def _signed_in(client, customer_user):
    """Chat needs a signed-in user; individual tests drop the header to test the gate."""
    client.headers.update(auth_headers(client, "shopper", "Customer123!"))


def test_chat_requires_login(client, monkeypatch):
    async def boom(message, session_id):
        raise AssertionError("Lyzr must not be called")

    monkeypatch.setattr(chat_service, "ask_agent", boom)
    client.headers.pop("Authorization")
    response = client.post("/api/chat", json=VALID)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_chat_rejects_a_garbage_token(client, monkeypatch):
    async def boom(message, session_id):
        raise AssertionError("Lyzr must not be called")

    monkeypatch.setattr(chat_service, "ask_agent", boom)
    client.headers["Authorization"] = "Bearer not-a-token"
    assert client.post("/api/chat", json=VALID).status_code == 401


def test_returns_agent_reply(client, monkeypatch):
    async def fake(message, session_id):
        return "Shipping is $5.99."

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    response = client.post("/api/chat", json=VALID)
    assert response.status_code == 200
    assert response.json() == {"reply": "Shipping is $5.99.", "products": []}


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


def _timeout_handler(request):
    import httpx

    raise httpx.ReadTimeout("t")


def _not_json_handler(request):
    import httpx

    return httpx.Response(200, content=b"not json")


def _non_dict_handler(request):
    import httpx

    return httpx.Response(200, json=["x"])


@pytest.mark.parametrize(
    "handler",
    [_timeout_handler, _not_json_handler, _non_dict_handler],
    ids=["timeout", "non_json", "non_dict_json"],
)
def test_service_failures_raise_chat_unavailable_and_are_logged(monkeypatch, caplog, handler):
    import asyncio
    import logging

    import httpx

    monkeypatch.setattr(
        chat_service,
        "_http_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    with caplog.at_level(logging.ERROR, logger="app.services.chat_service"):
        with pytest.raises(chat_service.ChatUnavailable):
            asyncio.run(chat_service.ask_agent("hello", "abcd1234"))
    assert any(record.levelno == logging.ERROR for record in caplog.records)


def test_reply_includes_product_cards(client, db, product_factory, monkeypatch):
    product = product_factory(slug="red-ball", price_cents=1999, stock=5)
    product.name = "Rocket Race Family Board Game"
    db.commit()

    async def fake(message, session_id):
        return "Try the Rocket Race Family Board Game, it is great."

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    body = client.post("/api/chat", json=VALID).json()
    assert body["reply"].startswith("Try the Rocket Race")
    assert body["products"] == [
        {
            "slug": "red-ball",
            "name": "Rocket Race Family Board Game",
            "brand": "Fixture Co",
            "category_name": "Test Blocks",
            "price_cents": 1999,
            "in_stock": True,
            "min_age_months": 36,
            "max_age_months": 96,
            "image_url": "/static/uploads/red-ball.svg",
        }
    ]


def test_out_of_stock_card_is_flagged(client, db, product_factory, monkeypatch):
    product = product_factory(slug="sold-out", stock=0)
    product.name = "Sold Out Robot Kit"
    db.commit()

    async def fake(message, session_id):
        return "The Sold Out Robot Kit is popular."

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    products = client.post("/api/chat", json=VALID).json()["products"]
    assert [item["in_stock"] for item in products] == [False]


def test_card_without_an_image_has_null_image_url(client, db, product_factory, monkeypatch):
    product = product_factory(slug="plain-toy", stock=3)
    product.name = "Plain Wooden Toy Cart"
    product.images.clear()
    db.commit()

    async def fake(message, session_id):
        return "The Plain Wooden Toy Cart is simple and sturdy."

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    products = client.post("/api/chat", json=VALID).json()["products"]
    assert [item["image_url"] for item in products] == [None]
    assert products[0]["slug"] == "plain-toy"


def test_lookup_failure_still_returns_the_reply(client, monkeypatch, caplog):
    async def fake(message, session_id):
        return "Shipping is $5.99."

    def explode(db, reply):
        raise RuntimeError("database went away")

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    monkeypatch.setattr("app.services.chat_products.find_mentioned_products", explode)
    with caplog.at_level("ERROR", logger="app.routers.chat"):
        response = client.post("/api/chat", json=VALID)
    assert response.status_code == 200
    assert response.json() == {"reply": "Shipping is $5.99.", "products": []}
    assert any(record.levelname == "ERROR" for record in caplog.records)
