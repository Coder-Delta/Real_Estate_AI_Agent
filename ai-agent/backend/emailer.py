"""SMTP email helper for sending lead notifications to a configured recipient."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import get_settings


def send_email(subject: str, message: str) -> bool:
    settings = get_settings()
    if not all(
        [
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_username,
            settings.smtp_password,
            settings.notification_email,
        ]
    ):
        return False

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = settings.smtp_username
    email["To"] = settings.notification_email
    email.set_content(message)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(email)

    return True
