"""Request and response bodies for the chat endpoint."""

from pydantic import BaseModel, Field, field_validator

CHAT_MAX_CHARS = 500


class ChatRequest(BaseModel):
    message: str = Field(max_length=CHAT_MAX_CHARS * 4)
    session_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("message")
    @classmethod
    def _clean_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        if len(value) > CHAT_MAX_CHARS:
            raise ValueError(f"Message must be at most {CHAT_MAX_CHARS} characters.")
        return value


class ChatResponse(BaseModel):
    reply: str
