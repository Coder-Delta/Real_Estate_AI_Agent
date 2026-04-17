"""Conversation logic for the real-estate sales assistant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo


READINESS_PATTERNS = (
    "call me",
    "give me a call",
    "let's talk",
    "lets talk",
    "let's connect",
    "lets connect",
    "contact me",
    "reach out",
    "book a call",
    "book a meeting",
    "book",
    "schedule",
    "set up a time",
    "i'm ready",
    "im ready",
    "what's next",
    "whats next",
)

BUY_KEYWORDS = (
    "buy",
    "purchase",
    "looking for",
    "looking to move",
    "need a home",
    "need an apartment",
    "need a condo",
    "need a house",
)

SELL_KEYWORDS = (
    "sell",
    "listing",
    "list my",
    "put my home on the market",
    "put my house on the market",
)

INQUIRY_KEYWORDS = (
    "exploring",
    "curious",
    "information",
    "learn more",
    "question",
    "inquiry",
)

NAME_STOPWORDS = {
    "looking",
    "searching",
    "interested",
    "ready",
    "thinking",
    "planning",
    "moving",
    "selling",
    "buying",
    "exploring",
}

LOCATION_GUARD_WORDS = {
    "budget",
    "range",
    "price",
    "timeline",
    "month",
    "months",
    "week",
    "weeks",
    "day",
    "days",
    "asap",
    "soon",
}


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(slots=True)
class LeadState:
    intent: str = "greeting"
    name: str | None = None
    budget: int | None = None
    location: str | None = None
    timeline: str | None = None


@dataclass(slots=True)
class AssistantPayload:
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

    def to_dict(self) -> dict[str, str | int | None]:
        payload: dict[str, str | int | None] = {
            "status": self.status,
            "intent": self.intent,
            "name": self.name,
            "budget": self.budget,
            "location": self.location,
            "timeline": self.timeline,
            "action": self.action,
            "reply": self.reply,
        }
        if self.lead_summary:
            payload["lead_summary"] = self.lead_summary
        if self.suggested_meeting_date:
            payload["suggested_meeting_date"] = self.suggested_meeting_date
        return payload


def build_assistant_payload(messages: list[ChatMessage]) -> AssistantPayload:
    user_messages = [message.content.strip() for message in messages if message.role == "user" and message.content.strip()]
    if not user_messages:
        return AssistantPayload(
            status="ongoing",
            intent="greeting",
            name=None,
            budget=None,
            location=None,
            timeline=None,
            action="none",
            reply="Hi, it’s lovely to connect. Are you looking to buy, sell, or just explore your options right now?",
        )

    state = LeadState()
    for text in user_messages:
        _merge_state(state, text)

    latest_message = user_messages[-1]
    is_completed = _should_finalize(state, latest_message)

    if is_completed:
        meeting_date = suggest_meeting_date(state.timeline)
        return AssistantPayload(
            status="completed",
            intent=state.intent if state.intent in {"buy", "sell"} else "buy",
            name=state.name,
            budget=state.budget,
            location=state.location,
            timeline=state.timeline,
            action="finalize_lead",
            reply=_build_closing_reply(state, meeting_date),
            lead_summary=build_lead_summary(state),
            suggested_meeting_date=meeting_date,
        )

    return AssistantPayload(
        status="ongoing",
        intent=state.intent,
        name=state.name,
        budget=state.budget,
        location=state.location,
        timeline=state.timeline,
        action="none",
        reply=_build_next_reply(state),
    )


def build_lead_summary(state: LeadState) -> str:
    subject = state.name or "Client"
    intent_phrase = "buy" if state.intent == "buy" else "sell"
    parts = [f"{subject} is looking to {intent_phrase} real estate"]

    if state.location:
        parts.append(f"in {state.location}")
    if state.timeline:
        parts.append(f"within {state.timeline}")
    if state.budget is not None:
        parts.append(f"with a budget of up to ${state.budget:,}")

    summary = " ".join(parts).strip()
    if not summary.endswith("."):
        summary += "."
    return summary


def suggest_meeting_date(timeline: str | None, *, timezone_name: str = "America/New_York") -> str:
    now = datetime.now(ZoneInfo(timezone_name))
    normalized = (timeline or "").lower()

    if any(marker in normalized for marker in ("asap", "immediately", "urgent", "this week", "few days")):
        meeting = _next_business_slot(now, days_ahead=1, hour=10)
    elif "week" in normalized:
        meeting = _next_business_slot(now, days_ahead=2, hour=11)
    elif any(marker in normalized for marker in ("month", "end of year", "quarter", "next year")):
        meeting = _next_business_slot(now, days_ahead=3, hour=14)
    else:
        meeting = _next_business_slot(now, days_ahead=2, hour=10)

    time_display = meeting.strftime("%I:%M %p").lstrip("0")
    return f"{meeting.strftime('%A')}, {meeting.strftime('%B')} {meeting.day} at {time_display}"


def _next_business_slot(start: datetime, *, days_ahead: int, hour: int) -> datetime:
    meeting = start + timedelta(days=days_ahead)
    while meeting.weekday() >= 5:
        meeting += timedelta(days=1)
    return meeting.replace(hour=hour, minute=0, second=0, microsecond=0)


def _merge_state(state: LeadState, text: str) -> None:
    intent = _extract_intent(text)
    if intent != "greeting":
        state.intent = intent
    elif state.intent == "greeting" and text.strip():
        state.intent = "inquiry" if _contains_any(text, INQUIRY_KEYWORDS) else state.intent

    name = _extract_name(text)
    if not name and state.name is None:
        name = _extract_bare_name(text, state)
    if name:
        state.name = name

    budget = _extract_budget(text)
    if budget is not None:
        state.budget = budget

    location = _extract_location(text)
    if not location and state.location is None:
        location = _extract_bare_location(text, state)
    if location:
        state.location = location

    timeline = _extract_timeline(text)
    if not timeline and state.timeline is None:
        timeline = _extract_bare_timeline(text)
    if timeline:
        state.timeline = timeline


def _extract_intent(text: str) -> str:
    normalized = text.lower()
    if _contains_any(normalized, SELL_KEYWORDS):
        return "sell"
    if _contains_any(normalized, BUY_KEYWORDS):
        return "buy"
    if _contains_any(normalized, INQUIRY_KEYWORDS):
        return "inquiry"
    if any(word in normalized for word in ("hi", "hello", "hey")) and len(normalized.split()) <= 4:
        return "greeting"
    return "greeting"


def _extract_name(text: str) -> str | None:
    patterns = (
        r"\bmy name is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        r"\bi am ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        r"\bi'm ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        r"\bthis is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        r"\bcall me ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = _sanitize_name(match.group(1))
            if not candidate:
                continue
            first_word = candidate.split()[0].lower()
            if first_word not in NAME_STOPWORDS:
                return candidate
    return None


def _extract_budget(text: str) -> int | None:
    patterns = (
        r"(?i)(?:budget|around|about|up to|under|max(?:imum)? of|price range of)?\s*\$?\s*(\d+(?:\.\d+)?)\s*([km])\b",
        r"(?i)(?:budget|around|about|up to|under|max(?:imum)? of|price range of)?\s*\$?\s*(\d[\d,]{4,})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        number = float(match.group(1).replace(",", ""))
        suffix = match.group(2).lower() if len(match.groups()) > 1 and match.group(2) else ""
        if suffix == "m":
            number *= 1_000_000
        elif suffix == "k":
            number *= 1_000
        return int(number)
    return None


def _extract_location(text: str) -> str | None:
    patterns = (
        r"(?i)\b(?:in|around|near|at|within|from)\s+([A-Za-z][A-Za-z\s\.-]*(?:,\s*[A-Za-z]{2})?)",
        r"(?i)\b(?:looking in|looking around|interested in|buy in|sell in|selling in)\s+([A-Za-z][A-Za-z\s\.-]*(?:,\s*[A-Za-z]{2})?)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = _sanitize_location(match.group(1))
        if candidate and candidate.lower() not in LOCATION_GUARD_WORDS:
            return candidate
    return None


def _extract_timeline(text: str) -> str | None:
    patterns = (
        r"(?i)\b(?:in|within|after|next)\s+(\d+\s+(?:day|days|week|weeks|month|months))\b",
        r"(?i)\b(asap|immediately|soon|this month|next month|end of year|by year end)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _should_finalize(state: LeadState, latest_message: str) -> bool:
    if state.intent not in {"buy", "sell"}:
        return False

    known_fields = sum(
        value is not None for value in (state.budget, state.location, state.timeline)
    )
    if known_fields >= 2:
        return True

    return _contains_any(latest_message.lower(), READINESS_PATTERNS)


def _build_next_reply(state: LeadState) -> str:
    if state.intent in {"greeting", "inquiry"}:
        return "I’d love to help. Are you looking to buy, sell, or just explore the market right now?"

    if not state.location:
        if state.intent == "sell":
            return "That makes sense. Which area is the property in?"
        return "That sounds exciting. Which area are you hoping to focus on?"

    if state.budget is None:
        return "That’s a helpful starting point. What price range feels right for you?"

    if not state.timeline:
        return "That gives me a good sense of the search. How soon are you hoping to make a move?"

    if not state.name:
        return "You’ve given me a clear picture so far. What name should I use?"

    return f"Thanks for sharing that, {state.name}. What would feel most helpful as a next step?"


def _build_closing_reply(state: LeadState, meeting_date: str) -> str:
    location_phrase = f" in {state.location}" if state.location else ""
    budget_phrase = (
        f" around ${state.budget:,}" if state.budget is not None else ""
    )
    opening = f"{state.name}, you’ve" if state.name else "You’ve"

    if state.intent == "sell":
        return (
            f"{opening} shared enough for us to line up the right listing specialist{location_phrase}{budget_phrase}. "
            f"I can tee up a conversation and hold {meeting_date} if that works for you."
        )

    return (
        f"{opening} shared enough for us to match you with the right property specialist{location_phrase}{budget_phrase}. "
        f"I can set aside {meeting_date} for a quick call and walk you through the best next options."
    )


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(pattern in normalized for pattern in patterns)


def _extract_bare_location(text: str, state: LeadState) -> str | None:
    cleaned = text.strip()
    if state.intent not in {"buy", "sell"}:
        return None
    if _extract_budget(cleaned) is not None or _extract_timeline(cleaned):
        return None
    if len(cleaned.split()) > 4 or not re.fullmatch(r"[A-Za-z][A-Za-z\s\.-]*(?:,\s*[A-Za-z]{2})?", cleaned):
        return None
    if cleaned.lower() in LOCATION_GUARD_WORDS:
        return None
    return _format_location(cleaned)


def _extract_bare_timeline(text: str) -> str | None:
    cleaned = text.strip()
    match = re.fullmatch(
        r"(?i)(\d+\s+(?:day|days|week|weeks|month|months)|asap|immediately|soon|this month|next month|end of year|by year end)",
        cleaned,
    )
    if match:
        return match.group(1)
    return None


def _extract_bare_name(text: str, state: LeadState) -> str | None:
    cleaned = text.strip()
    if state.location is None or state.intent not in {"buy", "sell"}:
        return None
    if _extract_budget(cleaned) is not None or _extract_timeline(cleaned):
        return None
    if not re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+)?", cleaned):
        return None
    candidate = _sanitize_name(cleaned)
    if candidate.split()[0].lower() in NAME_STOPWORDS:
        return None
    return candidate


def _sanitize_name(candidate: str) -> str:
    cleaned = re.split(r"(?i)\b(?:and|with|looking|budget|in)\b", candidate, maxsplit=1)[0]
    return cleaned.strip().title()


def _sanitize_location(candidate: str) -> str | None:
    cleaned = re.sub(
        r"(?i)\b(with|budget|looking|wanting|hoping|and|next|within|after|by)\b.*$",
        "",
        candidate,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,")
    if not cleaned:
        return None
    return _format_location(cleaned)


def _format_location(location: str) -> str:
    parts = [part.strip() for part in location.split(",")]
    formatted_parts: list[str] = []
    for index, part in enumerate(parts):
        if index > 0 and re.fullmatch(r"[A-Za-z]{2}", part):
            formatted_parts.append(part.upper())
        else:
            formatted_parts.append(" ".join(word.capitalize() for word in part.split()))
    return ", ".join(formatted_parts)
