"""Optional Supabase-backed lead persistence helpers."""

from __future__ import annotations

import logging
from typing import Any

import requests

from utils.config import get_settings


logger = logging.getLogger(__name__)


def is_database_enabled() -> bool:
    settings = get_settings()
    return bool(settings.supabase_url and settings.supabase_key)


def save_lead(payload: dict[str, str]) -> bool:
    settings = get_settings()
    if not is_database_enabled():
        return False

    endpoint = f"{settings.supabase_url}/rest/v1/{settings.supabase_table}"
    headers = {
        "apikey": settings.supabase_key,
        "Authorization": f"Bearer {settings.supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    try:
        response = requests.post(
            endpoint,
            json=_build_record(payload),
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("Supabase lead persistence failed.")
        return False


def _build_record(payload: dict[str, str]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "intent": payload.get("intent") or None,
        "name": payload.get("name") or None,
        "budget": _coerce_int(payload.get("budget")),
        "location": payload.get("location") or None,
        "timeline": payload.get("timeline") or None,
        "status": payload.get("status") or None,
        "action": payload.get("action") or None,
        "lead_summary": payload.get("lead_summary") or None,
        "suggested_meeting_date": payload.get("suggested_meeting_date") or None,
        "reply": payload.get("reply") or None,
        "transcript": payload.get("transcript") or None,
    }
    return record


def _coerce_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return int(digits) if digits else None
