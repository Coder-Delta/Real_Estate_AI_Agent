"""Timeline-to-follow-up message mapper for booking guidance."""

from __future__ import annotations


def build_booking_message(timeline: str) -> str:
    normalized_timeline = (timeline or "").lower()

    if "week" in normalized_timeline or "asap" in normalized_timeline:
        return "A priority call can be arranged within the next 24 hours."

    if "month" in normalized_timeline:
        return "A discovery call can be scheduled for tomorrow at 5:00 PM."

    return "A follow-up call will be scheduled after confirming the preferred time slot."
