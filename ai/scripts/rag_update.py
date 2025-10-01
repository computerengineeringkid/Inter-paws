"""Generate retrieval-ready insights from recent feedback events."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable

from backend.app import create_app
from backend.app.models import FeedbackEvent

INSIGHTS_PATH = Path(__file__).resolve().parent / "insights.json"


def _time_bucket(value: datetime | None) -> str | None:
    if value is None:
        return None
    hour = value.hour
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def _format_insights(events: Iterable[FeedbackEvent]) -> list[str]:
    doctor_preferences: Counter[str] = Counter()
    time_preferences: Counter[str] = Counter()
    rank_preferences: Counter[int] = Counter()

    for event in events:
        if event.appointment and event.appointment.doctor:
            doctor_preferences[event.appointment.doctor.display_name] += 1

        bucket = _time_bucket(event.suggestion_start_time)
        if bucket:
            time_preferences[bucket] += 1

        if event.suggestion_rank is not None:
            rank_preferences[event.suggestion_rank] += 1

    insights: list[str] = []

    if doctor_preferences:
        doctor, count = doctor_preferences.most_common(1)[0]
        insights.append(
            f"Clients most frequently choose recommendations featuring {doctor} "
            f"({count} recent selections)."
        )

    if time_preferences:
        bucket, count = time_preferences.most_common(1)[0]
        insights.append(
            f"Preferred appointment window skews toward the {bucket} "
            f"based on {count} bookings."
        )

    if rank_preferences:
        rank, count = rank_preferences.most_common(1)[0]
        ordinal = _ordinal(rank)
        insights.append(
            f"The {ordinal} ranked suggestion was accepted {count} times in the latest run."
        )

    if not insights:
        insights.append("Insufficient feedback data to derive new scheduling insights.")

    return insights


def _ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def generate_insights() -> dict[str, object]:
    app = create_app()
    with app.app_context():
        events = FeedbackEvent.query.order_by(FeedbackEvent.id.asc()).all()
        insights = _format_insights(events)
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_events": len(events),
            "insights": insights,
        }

        INSIGHTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload


def main() -> None:
    result = generate_insights()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":  # pragma: no cover - manual execution path
    main()
