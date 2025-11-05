"""Endpoints for interacting with the scheduling engine."""
from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

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
from backend.extensions import db

scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.post("/find-slots")
@jwt_required()
def find_slots() -> tuple[object, HTTPStatus]:
    """Return a ranked set of appointment slots for the supplied request."""

    payload = request.get_json(silent=True) or {}
    identity = get_jwt_identity()
    try:
        user_id = int(identity) if identity is not None else None
    except (TypeError, ValueError):
        user_id = None

    if user_id is None:
        return jsonify(message="Invalid token."), HTTPStatus.UNAUTHORIZED

    authenticated_user = User.query.get(user_id)
    if authenticated_user is None:
        return jsonify(message="User not found."), HTTPStatus.NOT_FOUND

    if authenticated_user.clinic_id is None:
        return (
            jsonify(message="User is not associated with a clinic."),
            HTTPStatus.BAD_REQUEST,
        )

    request_clinic_id = payload.pop("clinic_id", None)
    if request_clinic_id is not None:
        try:
            requested_id_int = int(request_clinic_id)
        except (TypeError, ValueError):
            return (
                jsonify(message="clinic_id must be an integer."),
                HTTPStatus.BAD_REQUEST,
            )
        if requested_id_int != authenticated_user.clinic_id:
            return (
                jsonify(
                    message="You are not authorized to access this clinic's schedule."
                ),
                HTTPStatus.FORBIDDEN,
            )

    clinic_id_int = int(authenticated_user.clinic_id)

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
    suggestion: dict[str, Any] = payload.get("suggestion") or {}

    identity = get_jwt_identity()
    try:
        user_id = int(identity) if identity is not None else None
    except (TypeError, ValueError):
        user_id = None

    if user_id is None:
        return jsonify(message="Invalid token."), HTTPStatus.UNAUTHORIZED

    booking_user = User.query.get(user_id)
    if booking_user is None:
        return jsonify(message="User not found."), HTTPStatus.NOT_FOUND

    if booking_user.clinic_id is None:
        return (
            jsonify(message="User is not associated with a clinic."),
            HTTPStatus.BAD_REQUEST,
        )

    request_clinic_id = payload.pop("clinic_id", None)
    if request_clinic_id is not None:
        try:
            requested_id_int = int(request_clinic_id)
        except (TypeError, ValueError):
            return jsonify(message="clinic_id must be an integer."), HTTPStatus.BAD_REQUEST
        if requested_id_int != booking_user.clinic_id:
            return (
                jsonify(message="You are not authorized to book for this clinic."),
                HTTPStatus.FORBIDDEN,
            )

    clinic_id_int = int(booking_user.clinic_id)

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

    owner_name = (payload.get("owner_name") or booking_user.full_name or "").strip()
    owner_email = (booking_user.email or "").strip()
    pet_name = (payload.get("pet_name") or "").strip()

    if not owner_name or not owner_email:
        return (
            jsonify(message="owner_name and owner_email are required."),
            HTTPStatus.BAD_REQUEST,
        )

    owner = booking_user
    if owner_name and owner.full_name != owner_name:
        owner.full_name = owner_name

    pet: Pet | None = None
    if pet_name:
        pet = Pet.query.filter_by(
            name=pet_name,
            owner_id=owner.id,
            clinic_id=clinic_id_int,
        ).first()

        if pet is None:
            species = (payload.get("pet_species") or "Unknown").strip() or "Unknown"
            pet = Pet(
                clinic_id=clinic_id_int,
                owner_id=owner.id,
                name=pet_name,
                species=species,
            )
            db.session.add(pet)
            db.session.flush()
    else:
        pet = (
            Pet.query.filter_by(owner_id=owner.id, clinic_id=clinic_id_int)
            .order_by(Pet.id)
            .first()
        )
        if pet is None:
            fallback_name = owner.full_name or "Client"
            generated_name = f"{fallback_name}'s Pet".strip()
            if not generated_name:
                generated_name = "Pet"
            pet = Pet(
                clinic_id=clinic_id_int,
                owner_id=owner.id,
                name=generated_name,
                species="Unknown",
            )
            db.session.add(pet)
            db.session.flush()

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
        owner_id=owner.id,
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
        user_id=owner.id,
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
