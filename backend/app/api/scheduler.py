"""Endpoints for interacting with the scheduling engine."""
from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)

from backend.app.models import Appointment, FeedbackEvent, User
from backend.app.services.scheduler_service import find_candidate_slots_for_request
from backend.extensions import db

scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.post("/find-slots")
def find_slots() -> tuple[object, HTTPStatus]:
    """Return a ranked set of appointment slots for the supplied request."""

    payload = request.get_json(silent=True) or {}
    clinic_id = payload.get("clinic_id")

    if clinic_id is None:
        try:
            verify_jwt_in_request(optional=True)
        except Exception:  # pragma: no cover - optional JWT
            user = None
        else:
            identity = get_jwt_identity()
            try:
                user_id = int(identity) if identity is not None else None
            except (TypeError, ValueError):  # pragma: no cover - defensive
                user_id = None
            user = User.query.get(user_id) if user_id is not None else None
        if user is not None and user.clinic_id is not None:
            clinic_id = user.clinic_id

    if clinic_id is None:
        return (
            jsonify(message="A clinic_id must be provided for scheduling."),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        clinic_id_int = int(clinic_id)
    except (TypeError, ValueError):
        return (
            jsonify(message="clinic_id must be an integer."),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        ranked_slots = find_candidate_slots_for_request(clinic_id_int, payload)
    except ValueError as exc:
        return jsonify(message=str(exc)), HTTPStatus.BAD_REQUEST

    return jsonify(suggestions=ranked_slots), HTTPStatus.OK


def _parse_datetime(value: str | None, field: str) -> datetime:
    """Return a timezone-naive UTC datetime from an ISO 8601 string."""

    if not value:
        raise ValueError(f"{field} is required for booking an appointment.")

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{field} must be a valid ISO 8601 timestamp.") from exc

    if parsed.tzinfo is None:
        return parsed

    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


@scheduler_bp.post("/book")
@jwt_required()
def book_appointment() -> tuple[object, HTTPStatus]:
    """Confirm an appointment slot and log the associated feedback event."""

    payload: dict[str, Any] = request.get_json(silent=True) or {}
    clinic_id = payload.get("clinic_id")
    suggestion: dict[str, Any] = payload.get("suggestion") or {}

    if clinic_id is None:
        return jsonify(message="clinic_id is required."), HTTPStatus.BAD_REQUEST

    try:
        clinic_id_int = int(clinic_id)
    except (TypeError, ValueError):
        return jsonify(message="clinic_id must be an integer."), HTTPStatus.BAD_REQUEST

    start_time = suggestion.get("start_time")
    end_time = suggestion.get("end_time")

    try:
        start_dt = _parse_datetime(start_time, "start_time")
        end_dt = _parse_datetime(end_time, "end_time")
    except ValueError as exc:
        return jsonify(message=str(exc)), HTTPStatus.BAD_REQUEST

    if end_dt <= start_dt:
        return (
            jsonify(message="end_time must occur after start_time."),
            HTTPStatus.BAD_REQUEST,
        )

    identity = get_jwt_identity()
    try:
        user_id = int(identity) if identity is not None else None
    except (TypeError, ValueError):  # pragma: no cover - defensive
        user_id = None

    current_user = User.query.get(user_id) if user_id is not None else None

    if current_user is None:
        return jsonify(message="Authenticated user could not be resolved."), HTTPStatus.UNAUTHORIZED

    owner_id = payload.get("owner_id")
    try:
        owner_id_int = int(owner_id) if owner_id is not None else current_user.id
    except (TypeError, ValueError):
        return jsonify(message="owner_id must be an integer."), HTTPStatus.BAD_REQUEST

    doctor_id = suggestion.get("doctor_id")
    room_id = suggestion.get("room_id")
    constraint_id = payload.get("constraint_id")

    appointment = Appointment(
        clinic_id=clinic_id_int,
        pet_id=payload.get("pet_id"),
        owner_id=owner_id_int,
        doctor_id=doctor_id,
        room_id=room_id,
        constraint_id=constraint_id,
        start_time=start_dt,
        end_time=end_dt,
        status="scheduled",
        reason=payload.get("reason"),
        notes=payload.get("notes"),
    )

    db.session.add(appointment)
    db.session.flush()

    feedback_event = FeedbackEvent(
        appointment_id=appointment.id,
        user_id=current_user.id,
        suggestion_rank=suggestion.get("rank"),
        suggestion_score=suggestion.get("score"),
        suggestion_slot_id=suggestion.get("slot_id"),
        suggestion_start_time=start_dt,
        suggestion_end_time=end_dt,
        suggestion_doctor_id=doctor_id,
        suggestion_room_id=room_id,
    )

    db.session.add(feedback_event)
    db.session.commit()

    response_payload = {
        "appointment": {
            "id": appointment.id,
            "clinic_id": appointment.clinic_id,
            "start_time": appointment.start_time.isoformat(),
            "end_time": appointment.end_time.isoformat(),
            "doctor_id": appointment.doctor_id,
            "room_id": appointment.room_id,
        },
        "feedback_event_id": feedback_event.id,
        "message": "Appointment booked successfully.",
    }

    return jsonify(response_payload), HTTPStatus.CREATED
