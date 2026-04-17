"""CSV persistence helper for appending finalized lead records."""

from __future__ import annotations

import csv
from pathlib import Path

from utils.config import get_settings


def save_lead(payload: dict[str, str]) -> Path:
    settings = get_settings()
    lead_log_path = settings.lead_log_path
    lead_log_path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = lead_log_path.exists()
    fieldnames = [
        "intent",
        "name",
        "budget",
        "location",
        "timeline",
        "status",
        "action",
        "lead_summary",
        "suggested_meeting_date",
        "reply",
        "transcript",
    ]

    with lead_log_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({key: payload.get(key, "") for key in fieldnames})

    return lead_log_path
