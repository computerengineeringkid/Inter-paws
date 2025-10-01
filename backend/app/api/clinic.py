"""Clinic onboarding endpoints."""
from __future__ import annotations

import json
from datetime import date, datetime, time
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.app.models import Clinic, Constraint, Doctor, Room, User
from backend.extensions import db

clinic_bp = Blueprint("clinic", __name__)

_RRULE_DAY_MAP = {
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}


def _current_admin() -> User | None:
    """Return the authenticated administrator or ``None`` if not authorized."""

    user_id = get_jwt_identity()
    if not user_id:
        return None
    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None
    user = User.query.get(user_pk)
    if not user or (user.role or "").lower() != "admin":
        return None
    return user


def _parse_operating_hours(rules: list[dict[str, Any]], clinic_id: int) -> list[Constraint]:
    """Create constraint objects representing operating hours."""

    constraints: list[Constraint] = []
    reference_date = date.today()

    for rule in rules:
        day_label = (rule.get("day") or "").strip()
        start_value = (rule.get("start") or "").strip()
        end_value = (rule.get("end") or "").strip()
        notes = (rule.get("notes") or "").strip() or None

        if not day_label or not start_value or not end_value:
            raise ValueError("Each operating hour requires a day, start time, and end time.")

        try:
            start_time_obj = time.fromisoformat(start_value)
            end_time_obj = time.fromisoformat(end_value)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise ValueError("Operating hours must use HH:MM format.") from exc

        if end_time_obj <= start_time_obj:
            raise ValueError("Operating hour end time must be after the start time.")

        start_dt = datetime.combine(reference_date, start_time_obj)
        end_dt = datetime.combine(reference_date, end_time_obj)
        recurrence = _RRULE_DAY_MAP.get(day_label.lower())
        recurrence_value = f"RRULE:FREQ=WEEKLY;BYDAY={recurrence}" if recurrence else None

        constraints.append(
            Constraint(
                clinic_id=clinic_id,
                title=f"Operating hours - {day_label}",
                description=notes,
                start_time=start_dt,
                end_time=end_dt,
                recurrence=recurrence_value,
                is_all_day=False,
            )
        )

    return constraints


def _prepare_equipment_lookup(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group equipment by their associated room."""

    lookup: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        name = (entry.get("name") or "").strip()
        if not name:
            continue
        room_name = (entry.get("room") or "").strip()
        equipment_payload: dict[str, Any] = {"name": name}
        notes = (entry.get("notes") or "").strip()
        if notes:
            equipment_payload["notes"] = notes
        target_room = room_name or "__unassigned__"
        lookup.setdefault(target_room, []).append(equipment_payload)
    return lookup


@clinic_bp.post("/onboarding")
@jwt_required()
def submit_onboarding() -> ResponseReturnValue:
    """Persist onboarding data for the current administrator's clinic."""

    admin = _current_admin()
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    payload = request.get_json(silent=True) or {}
    clinic_data: dict[str, Any] = payload.get("clinic") or {}
    doctor_entries: list[dict[str, Any]] = payload.get("doctors") or []
    room_entries: list[dict[str, Any]] = payload.get("rooms") or []
    equipment_entries: list[dict[str, Any]] = payload.get("equipment") or []
    schedule_rules: dict[str, Any] = payload.get("schedule_rules") or {}
    operating_hours = schedule_rules.get("operating_hours") or []

    clinic_name = (clinic_data.get("name") or "").strip()
    if not clinic_name:
        return jsonify(message="Clinic name is required."), HTTPStatus.BAD_REQUEST

    clinic = Clinic.query.get(admin.clinic_id) if admin.clinic_id else None

    if not clinic:
        clinic = Clinic(name=clinic_name)
        db.session.add(clinic)
        db.session.flush()
        admin.clinic_id = clinic.id
        db.session.add(admin)
    else:
        clinic.name = clinic_name

    clinic.address = (clinic_data.get("address") or "").strip() or None
    clinic.phone_number = (clinic_data.get("phone_number") or "").strip() or None
    clinic.email = (clinic_data.get("email") or "").strip() or None

    # Refresh related entities to avoid duplicates on repeated onboarding submissions.
    if clinic.id:
        Doctor.query.filter_by(clinic_id=clinic.id).delete(synchronize_session=False)
        Room.query.filter_by(clinic_id=clinic.id).delete(synchronize_session=False)
        Constraint.query.filter_by(clinic_id=clinic.id, doctor_id=None, room_id=None).delete(
            synchronize_session=False
        )

    equipment_lookup = _prepare_equipment_lookup(equipment_entries)
    unassigned_equipment = equipment_lookup.pop("__unassigned__", [])

    try:
        operating_constraints = _parse_operating_hours(operating_hours, clinic.id)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(message=str(exc)), HTTPStatus.BAD_REQUEST

    for doctor in doctor_entries:
        display_name = (doctor.get("display_name") or "").strip()
        if not display_name:
            continue
        specialty = (doctor.get("specialty") or "").strip() or None
        license_number = (doctor.get("license_number") or "").strip() or None
        biography = (doctor.get("biography") or "").strip() or None
        db.session.add(
            Doctor(
                clinic_id=clinic.id,
                display_name=display_name,
                specialty=specialty,
                license_number=license_number,
                biography=biography,
            )
        )

    for room in room_entries:
        name = (room.get("name") or "").strip()
        if not name:
            continue
        room_type = (room.get("room_type") or "").strip() or None
        notes_value = (room.get("notes") or "").strip() or None
        capacity_value = room.get("capacity")
        capacity_int = None
        if capacity_value not in (None, ""):
            try:
                capacity_int = int(capacity_value)
            except (TypeError, ValueError):
                db.session.rollback()
                return (
                    jsonify(message=f"Room capacity for '{name}' must be a number."),
                    HTTPStatus.BAD_REQUEST,
                )

        aggregated_equipment = equipment_lookup.get(name, [])
        notes_payload = {"notes": notes_value, "equipment": aggregated_equipment}
        db.session.add(
            Room(
                clinic_id=clinic.id,
                name=name,
                room_type=room_type,
                capacity=capacity_int,
                notes=json.dumps(notes_payload) if notes_payload else None,
            )
        )

    if unassigned_equipment:
        db.session.add(
            Room(
                clinic_id=clinic.id,
                name="General Equipment Storage",
                room_type="storage",
                capacity=None,
                notes=json.dumps(
                    {
                        "notes": "Automatically generated for unassigned equipment.",
                        "equipment": unassigned_equipment,
                    }
                ),
            )
        )

    for constraint in operating_constraints:
        db.session.add(constraint)

    db.session.commit()

    return jsonify(message="Onboarding completed successfully.", clinic_id=clinic.id), HTTPStatus.CREATED


@clinic_bp.get("/onboarding")
@jwt_required()
def retrieve_onboarding() -> ResponseReturnValue:
    """Return onboarding data for the authenticated administrator."""

    admin = _current_admin()
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    clinic = Clinic.query.get(admin.clinic_id) if admin.clinic_id else None
    if not clinic:
        return (
            jsonify(
                clinic=None,
                doctors=[],
                rooms=[],
                equipment=[],
                schedule_rules={"operating_hours": []},
            ),
            HTTPStatus.OK,
        )

    doctors_payload = [
        {
            "id": doctor.id,
            "display_name": doctor.display_name,
            "specialty": doctor.specialty,
            "license_number": doctor.license_number,
            "biography": doctor.biography,
        }
        for doctor in clinic.doctors
    ]

    rooms_payload: list[dict[str, Any]] = []
    equipment_payload: list[dict[str, Any]] = []

    for room in clinic.rooms:
        room_notes: str | None = None
        room_equipment: list[dict[str, Any]] = []
        if room.notes:
            try:
                parsed_notes = json.loads(room.notes)
            except json.JSONDecodeError:
                room_notes = room.notes
            else:
                room_notes = parsed_notes.get("notes") if isinstance(parsed_notes, dict) else None
                if isinstance(parsed_notes, dict):
                    room_equipment = [
                        item
                        for item in parsed_notes.get("equipment", [])
                        if isinstance(item, dict) and item.get("name")
                    ]
        rooms_payload.append(
            {
                "id": room.id,
                "name": room.name,
                "room_type": room.room_type,
                "capacity": room.capacity,
                "notes": room_notes,
                "equipment": room_equipment,
            }
        )
        for item in room_equipment:
            equipment_payload.append(
                {
                    "name": item.get("name"),
                    "room": room.name,
                    "notes": item.get("notes"),
                }
            )

    operating_payload = []
    for constraint in clinic.constraints:
        if constraint.doctor_id or constraint.room_id:
            continue
        if not constraint.title or not constraint.title.startswith("Operating hours"):
            continue
        operating_payload.append(
            {
                "id": constraint.id,
                "day": constraint.title.split("-", 1)[-1].strip(),
                "start": constraint.start_time.time().isoformat(timespec="minutes"),
                "end": constraint.end_time.time().isoformat(timespec="minutes"),
                "notes": constraint.description,
            }
        )

    response_payload = {
        "clinic": {
            "id": clinic.id,
            "name": clinic.name,
            "email": clinic.email,
            "phone_number": clinic.phone_number,
            "address": clinic.address,
        },
        "doctors": doctors_payload,
        "rooms": rooms_payload,
        "equipment": equipment_payload,
        "schedule_rules": {"operating_hours": operating_payload},
    }

    return jsonify(response_payload), HTTPStatus.OK
