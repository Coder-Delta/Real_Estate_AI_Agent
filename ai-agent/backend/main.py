"""FastAPI entrypoint for the conversational real-estate sales assistant."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import save_lead as save_lead_to_database
from emailer import send_email
from logic import AssistantPayload, ChatMessage, build_assistant_payload
from llm import maybe_generate_assistant_payload
from utils.config import get_settings
from utils.sheets import save_lead


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


class MessagePayload(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=2_000)


class ChatRequest(BaseModel):
    message: str | None = Field(default=None, min_length=1, max_length=2_000)
    messages: list[MessagePayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload(self) -> "ChatRequest":
        if not self.message and not self.messages:
            raise ValueError("Provide either `message` or `messages`.")
        return self


class ChatResponse(BaseModel):
    status: str
    intent: str
    name: str | None
    budget: int | None
    location: str | None
    timeline: str | None
    action: str
    reply: str
    lead_summary: str | None = None
    suggested_meeting_date: str | None = None


settings = get_settings()

app = FastAPI(
    title="Real Estate AI Sales Assistant",
    version="2.0.0",
    description="Conversational assistant for capturing and qualifying premium real-estate leads.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        conversation = _normalize_messages(request)
        payload = maybe_generate_assistant_payload(conversation)
        if payload is None:
            logger.info("Using local assistant fallback for %d messages.", len(conversation))
            payload = build_assistant_payload(conversation)

        if payload.status == "completed":
            _persist_completed_lead(payload, conversation)
            _notify(payload)

        return ChatResponse(**payload.to_dict())
    except ValueError as exc:
        logger.warning("Chat request rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected chat processing failure.")
        raise HTTPException(
            status_code=500,
            detail="The assistant could not process the conversation.",
        ) from exc


def _normalize_messages(request: ChatRequest) -> list[ChatMessage]:
    if request.messages:
        return [
            ChatMessage(role=message.role, content=message.content.strip())
            for message in request.messages
            if message.content.strip()
        ]

    if not request.message:
        raise ValueError("Message cannot be empty.")

    return [ChatMessage(role="user", content=request.message.strip())]


def _persist_completed_lead(payload: AssistantPayload, conversation: list[ChatMessage]) -> None:
    transcript = "\n".join(
        f"{message.role}: {message.content}"
        for message in conversation
        if message.role in {"user", "assistant"}
    )
    lead_payload = {
        "intent": payload.intent,
        "name": payload.name,
        "budget": str(payload.budget) if payload.budget else None,
        "location": payload.location,
        "timeline": payload.timeline,
        "status": payload.status,
        "action": payload.action,
        "lead_summary": payload.lead_summary,
        "suggested_meeting_date": payload.suggested_meeting_date,
        "reply": payload.reply,
        "transcript": transcript,
    }

    saved_to_database = save_lead_to_database(lead_payload)
    if not saved_to_database:
        save_lead(lead_payload)


def _notify(payload: AssistantPayload) -> None:
    if not settings.notification_email or not payload.lead_summary:
        return

    try:
        send_email(
            subject=f"New {payload.intent} lead for {payload.location or 'unknown location'}",
            message=(
                f"{payload.lead_summary}\n"
                f"Suggested meeting date: {payload.suggested_meeting_date or 'Not set'}\n"
                f"Reply: {payload.reply}"
            ),
        )
    except Exception:
        return
