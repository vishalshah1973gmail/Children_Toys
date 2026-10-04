"""Shopper chatbot endpoint. Public; no account required."""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import api_error
from app.db.session import get_db
from app.schemas.chat import ChatProduct, ChatRequest, ChatResponse
from app.services import chat_products, chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _cards_for(db: Session, reply: str) -> list[ChatProduct]:
    return [
        ChatProduct.from_product(product)
        for product in chat_products.find_mentioned_products(db, reply)
    ]


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest, request: Request, db: Session = Depends(get_db)
) -> ChatResponse:
    if not settings.lyzr_api_key or not settings.lyzr_agent_id:
        raise api_error(503, "chat_not_configured", "The chat assistant is not set up yet.")
    client_key = request.client.host if request.client else "unknown"
    if not chat_service.rate_limiter.allow(client_key):
        raise api_error(429, "rate_limited", "You're sending messages too quickly. Please wait a moment.")
    try:
        reply = await chat_service.ask_agent(payload.message, payload.session_id)
    except chat_service.ChatUnavailable:
        raise api_error(
            503,
            "chat_unavailable",
            "The assistant is having trouble right now. Please try again in a moment.",
        )
    # Cards are an extra: a failed lookup must never cost the shopper their answer.
    try:
        products = await run_in_threadpool(_cards_for, db, reply)
    except Exception:
        logger.exception("Product lookup for a chat reply failed")
        products = []
    return ChatResponse(reply=reply, products=products)
