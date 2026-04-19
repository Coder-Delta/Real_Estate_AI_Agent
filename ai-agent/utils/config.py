"""Environment-backed settings loader shared by backend and frontend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file)


@dataclass(frozen=True, slots=True)
class Settings:
    backend_url: str
    enable_gemini: bool
    gemini_api_key: str
    gemini_model: str
    gemini_timeout_seconds: int
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    notification_email: str
    cors_origins: list[str]
    lead_log_path: Path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")
        if origin.strip()
    ]

    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    enable_gemini_env = os.getenv("ENABLE_GEMINI", "").strip().lower()
    enable_gemini = (
        enable_gemini_env == "true"
        or (enable_gemini_env == "" and _has_real_api_key(gemini_api_key))
    )

    return Settings(
        backend_url=os.getenv("BACKEND_URL", "http://localhost:8000"),
        enable_gemini=enable_gemini,
        gemini_api_key=gemini_api_key,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip(),
        gemini_timeout_seconds=max(5, int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))),
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
        notification_email=os.getenv("NOTIFICATION_EMAIL", "").strip(),
        cors_origins=cors_origins,
        lead_log_path=PROJECT_ROOT / "data" / "leads.csv",
    )


def _has_real_api_key(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    return normalized.lower() not in {
        "your_gemini_api_key",
        "changeme",
        "replace_me",
        "replace-with-your-key",
    }
