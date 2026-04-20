"""Optional Gemini-backed response generation for the sales assistant."""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic import AssistantPayload, ChatMessage
from utils.config import get_settings

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - optional dependency at runtime
    genai = None


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are Aria, a warm and professional AI sales assistant for a premium real estate agency.

Rules:
- Hold a natural conversation with potential real estate clients.
- Silently track name, budget, location, timeline, and intent.
- Silently track name, budget, location, timeline, intent, email, phone, preferred_contact_method, and preferred_contact_time.
- Never ask more than one question per message.
- Never reveal that you are tracking the user.
- Never use markdown or any text outside a JSON object.
- Return JSON only with these keys:
  status, intent, name, budget, location, timeline, email, phone, preferred_contact_method, preferred_contact_time, action, reply
- Only include lead_summary and suggested_meeting_date when status is "completed".
- intent must be one of: buy, sell, inquiry, greeting.
- status must be one of: ongoing, completed.
- action must be "none" when ongoing and "finalize_lead" when completed.
- budget must be numeric or null.
- Keep reply warm, brief, and conversational, with 1 to 3 sentences max.
- Ask only one question in reply.
- Do not guess budget, location, or timeline.
- Prefer asking about location before budget.

Completion rules:
- Mark completed when intent is buy or sell and at least two of budget, location, timeline are known.
- Also mark completed when the user signals readiness such as asking to connect, schedule, book, or be contacted.
- Only use completed for buy or sell leads.

Meeting date:
- If completed, include a specific suggested_meeting_date like "Tuesday, April 22 at 2:00 PM".
""".strip()


def maybe_generate_assistant_payload(messages: list[ChatMessage]) -> AssistantPayload | None:
    settings = get_settings()
    if not settings.enable_gemini:
        return None
    if not settings.gemini_api_key or settings.gemini_api_key.strip().lower() == "your_gemini_api_key":
        logger.warning(
            "Gemini is enabled, but GEMINI_API_KEY is still a placeholder. Falling back to local assistant logic."
        )
        return None
    if genai is None:
        logger.warning(
            "Gemini is enabled, but the google-generativeai package is not available. Falling back to local assistant logic."
        )
        return None

    transcript = "\n".join(
        f"{message.role}: {message.content.strip()}"
        for message in messages
        if message.content.strip()
    )

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "Return a single valid JSON object for the next assistant response.\n"
        "Use today's date context when suggesting a meeting date.\n\n"
        f"Conversation:\n{transcript}"
    )

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        response = model.generate_content(
            prompt,
            request_options={"timeout": settings.gemini_timeout_seconds},
        )
        raw_text = getattr(response, "text", "") or ""
        payload = _extract_json_object(raw_text)
        return _normalize_payload(payload)
    except Exception as exc:
        logger.exception(
            "Gemini request failed for model=%s with %d messages. Falling back to local assistant logic.",
            settings.gemini_model,
            len(messages),
        )
        return None


def _extract_json_object(text: str) -> dict[str, object]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Model response did not contain valid JSON.")
    return json.loads(match.group(0))


def _normalize_payload(payload: dict[str, object]) -> AssistantPayload:
    status = str(payload.get("status", "ongoing")).strip().lower()
    intent = str(payload.get("intent", "greeting")).strip().lower()
    action = str(payload.get("action", "none")).strip()
    reply = str(payload.get("reply", "")).strip()
    lead_summary = payload.get("lead_summary")
    suggested_meeting_date = payload.get("suggested_meeting_date")

    if status not in {"ongoing", "completed"}:
        raise ValueError("Invalid status returned by model.")
    if intent not in {"buy", "sell", "inquiry", "greeting"}:
        raise ValueError("Invalid intent returned by model.")
    if not reply:
        raise ValueError("Reply is required.")

    normalized_action = "finalize_lead" if status == "completed" else "none"
    if status == "completed" and intent not in {"buy", "sell"}:
        raise ValueError("Completed responses must be buy or sell leads.")

    budget = _coerce_budget(payload.get("budget"))

    return AssistantPayload(
        status=status,
        intent=intent,
        name=_clean_text(payload.get("name")),
        budget=budget,
        location=_clean_text(payload.get("location")),
        timeline=_clean_text(payload.get("timeline")),
        email=_clean_text(payload.get("email")),
        phone=_clean_text(payload.get("phone")),
        preferred_contact_method=_clean_text(payload.get("preferred_contact_method")),
        preferred_contact_time=_clean_text(payload.get("preferred_contact_time")),
        action=normalized_action if action else normalized_action,
        reply=reply,
        lead_summary=_clean_text(lead_summary) if status == "completed" else None,
        suggested_meeting_date=_clean_text(suggested_meeting_date)
        if status == "completed"
        else None,
    )


def _coerce_budget(value: object) -> int | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, (int, float)):
        return int(value)

    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


def _clean_text(value: object) -> str | None:
    if value in (None, "", "null"):
        return None
    cleaned = str(value).strip()
    return cleaned or None
