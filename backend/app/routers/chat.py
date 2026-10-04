"""Shopper chatbot endpoint. Public; no account required."""

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.errors import api_error
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
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
    return ChatResponse(reply=reply)
