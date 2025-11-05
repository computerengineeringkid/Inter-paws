"""Endpoints for interacting with the scheduling engine."""
from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request

from backend.app.models import (
    Appointment,
    Clinic,
    Constraint,
    Doctor,
    FeedbackEvent,
    Pet,
    Room,
    User,
)
from backend.app.services.scheduler_service import find_candidate_slots_for_request
from backend.extensions import bcrypt, db

scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.post("/find-slots")
def find_slots() -> tuple[object, HTTPStatus]:
    """Return a ranked set of appointment slots for the supplied request."""

    payload = request.get_json(silent=True) or {}
    clinic_id = payload.get("clinic_id")

    authenticated_user: User | None = None

    try:
        verify_jwt_in_request(optional=True)
    except Exception:  # pragma: no cover - optional JWT
        authenticated_user = None
    else:
        identity = get_jwt_identity()
        try:
            user_id = int(identity) if identity is not None else None
        except (TypeError, ValueError):  # pragma: no cover - defensive
            user_id = None
        authenticated_user = User.query.get(user_id) if user_id is not None else None

    if clinic_id is None and authenticated_user is not None:
        clinic_id = authenticated_user.clinic_id

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

    if (
        authenticated_user is not None
        and authenticated_user.clinic_id is not None
        and authenticated_user.clinic_id != clinic_id_int
    ):
        return (
            jsonify(message="You are not authorized to access this clinic's schedule."),
            HTTPStatus.FORBIDDEN,
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

    clinic = Clinic.query.get(clinic_id_int)
    if clinic is None:
        return jsonify(message="Clinic not found."), HTTPStatus.NOT_FOUND

    owner_name = (payload.get("owner_name") or "").strip()
    owner_email = (payload.get("owner_email") or "").strip()
    pet_name = (payload.get("pet_name") or "").strip()

    if not owner_name or not owner_email or not pet_name:
        return (
            jsonify(message="owner_name, owner_email, and pet_name are required."),
            HTTPStatus.BAD_REQUEST,
        )

    user = User.query.filter_by(email=owner_email, clinic_id=clinic_id_int).first()

    if user is None:
        dummy_hash = bcrypt.generate_password_hash("password123").decode("utf-8")
        user = User(
            clinic_id=clinic_id_int,
            email=owner_email,
            full_name=owner_name,
            password_hash=dummy_hash,
            role="client",
        )
        db.session.add(user)
        db.session.flush()
    else:
        if owner_name and user.full_name != owner_name:
            user.full_name = owner_name

    pet = Pet.query.filter_by(
        name=pet_name,
        owner_id=user.id,
        clinic_id=clinic_id_int,
    ).first()

    if pet is None:
        pet = Pet(
            clinic_id=clinic_id_int,
            owner_id=user.id,
            name=pet_name,
            species="Unknown",
        )
        db.session.add(pet)
        db.session.flush()

    current_user = user

    doctor_id = suggestion.get("doctor_id")
    if doctor_id is not None:
        try:
            doctor_id_int = int(doctor_id)
        except (TypeError, ValueError):
            return jsonify(message="doctor_id must be an integer."), HTTPStatus.BAD_REQUEST
        doctor = Doctor.query.filter_by(id=doctor_id_int, clinic_id=clinic.id).first()
        if doctor is None:
            return (
                jsonify(message="doctor_id must reference a doctor in this clinic."),
                HTTPStatus.BAD_REQUEST,
            )
    else:
        doctor_id_int = None

    room_id = suggestion.get("room_id")
    if room_id is not None:
        try:
            room_id_int = int(room_id)
        except (TypeError, ValueError):
            return jsonify(message="room_id must be an integer."), HTTPStatus.BAD_REQUEST
        room = Room.query.filter_by(id=room_id_int, clinic_id=clinic.id).first()
        if room is None:
            return (
                jsonify(message="room_id must reference a room in this clinic."),
                HTTPStatus.BAD_REQUEST,
            )
    else:
        room_id_int = None

    constraint_id = payload.get("constraint_id")
    if constraint_id is not None:
        try:
            constraint_id_int = int(constraint_id)
        except (TypeError, ValueError):
            return jsonify(message="constraint_id must be an integer."), HTTPStatus.BAD_REQUEST
        constraint = Constraint.query.filter_by(
            id=constraint_id_int, clinic_id=clinic.id
        ).first()
        if constraint is None:
            return (
                jsonify(message="constraint_id must reference a constraint in this clinic."),
                HTTPStatus.BAD_REQUEST,
            )
    else:
        constraint_id_int = None

    appointment = Appointment(
        clinic_id=clinic_id_int,
        pet_id=pet.id,
        owner_id=user.id,
        doctor_id=doctor_id_int,
        room_id=room_id_int,
        constraint_id=constraint_id_int,
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
        suggestion_doctor_id=doctor_id_int,
        suggestion_room_id=room_id_int,
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


@scheduler_bp.get("/history")
@jwt_required()
def appointment_history() -> tuple[object, HTTPStatus]:
    """Return appointment history for the authenticated client."""

    identity = get_jwt_identity()
    try:
        user_id = int(identity) if identity is not None else None
    except (TypeError, ValueError):
        user_id = None

    if user_id is None:
        return jsonify(message="Invalid token."), HTTPStatus.UNAUTHORIZED

    user = User.query.get(user_id)
    if user is None:
        return jsonify(message="User not found."), HTTPStatus.NOT_FOUND

    appointments = (
        Appointment.query.filter_by(owner_id=user.id)
        .order_by(Appointment.start_time.desc())
        .limit(100)
        .all()
    )

    payload = [
        {
            "id": appointment.id,
            "start_time": appointment.start_time.isoformat(),
            "end_time": appointment.end_time.isoformat(),
            "status": appointment.status,
            "reason": appointment.reason,
            "doctor": {
                "id": appointment.doctor.id,
                "display_name": appointment.doctor.display_name,
            }
            if appointment.doctor
            else None,
            "room": {
                "id": appointment.room.id,
                "name": appointment.room.name,
            }
            if appointment.room
            else None,
            "pet": {
                "id": appointment.pet.id,
                "name": appointment.pet.name,
            }
            if appointment.pet
            else None,
        }
        for appointment in appointments
    ]

    return jsonify(appointments=payload), HTTPStatus.OK
