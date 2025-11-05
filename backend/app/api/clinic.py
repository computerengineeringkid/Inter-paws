"""Clinic onboarding endpoints."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.app.models import (
    Clinic,
    Constraint,
    Doctor,
    DoctorSchedule,
    Room,
    RoomSchedule,
    User,
)
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

_DAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_SCHEDULE_KIND_MAP = {
    "availability": "availability",
    "available": "availability",
    "shift": "availability",
    "break": "blackout",
    "blackout": "blackout",
    "unavailable": "blackout",
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
        DoctorSchedule.query.filter_by(clinic_id=clinic.id).delete(
            synchronize_session=False
        )
        RoomSchedule.query.filter_by(clinic_id=clinic.id).delete(
            synchronize_session=False
        )
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

    created_doctors: list[Doctor] = []
    for doctor in doctor_entries:
        display_name = (doctor.get("display_name") or "").strip()
        if not display_name:
            continue
        specialty = (doctor.get("specialty") or "").strip() or None
        license_number = (doctor.get("license_number") or "").strip() or None
        biography = (doctor.get("biography") or "").strip() or None
        doctor_model = Doctor(
            clinic_id=clinic.id,
            display_name=display_name,
            specialty=specialty,
            license_number=license_number,
            biography=biography,
        )
        db.session.add(doctor_model)
        created_doctors.append(doctor_model)

    created_rooms: list[Room] = []
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
        room_model = Room(
            clinic_id=clinic.id,
            name=name,
            room_type=room_type,
            capacity=capacity_int,
            notes=json.dumps(notes_payload) if notes_payload else None,
        )
        db.session.add(room_model)
        created_rooms.append(room_model)

    if unassigned_equipment:
        storage_room = Room(
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
        db.session.add(storage_room)
        created_rooms.append(storage_room)

    for constraint in operating_constraints:
        db.session.add(constraint)

    db.session.flush()

    response_doctors = [
        {"id": doctor.id, "display_name": doctor.display_name}
        for doctor in sorted(created_doctors, key=lambda value: value.display_name or "")
    ]
    response_rooms = [
        {"id": room.id, "name": room.name}
        for room in sorted(created_rooms, key=lambda value: value.name or "")
    ]

    db.session.commit()

    return (
        jsonify(
            message="Onboarding completed successfully.",
            clinic_id=clinic.id,
            doctors=response_doctors,
            rooms=response_rooms,
        ),
        HTTPStatus.CREATED,
    )


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


def _resolve_kind(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in _SCHEDULE_KIND_MAP:
        return _SCHEDULE_KIND_MAP[normalized]
    if not normalized:
        return "availability"
    raise ValueError(
        "Schedule entries must specify a kind of 'availability' or 'break'."
    )


def _resolve_weekday(value: str | None) -> int:
    if value is None:
        raise ValueError("Each schedule entry requires a day of the week.")
    key = value.strip().lower()
    if key not in _DAY_INDEX:
        raise ValueError("Day must be one of Monday through Sunday.")
    return _DAY_INDEX[key]


def _parse_time(value: str | None, label: str) -> time:
    if not value:
        raise ValueError(f"{label} is required for schedule entries.")
    try:
        return time.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{label} must use HH:MM format.") from exc


def _next_reference_date(weekday: int) -> date:
    today = date.today()
    delta = (weekday - today.weekday()) % 7
    return today + timedelta(days=delta)


def _parse_schedule_dates(entry: dict[str, Any], weekday: int) -> tuple[date, date | None]:
    start_date_raw = entry.get("start_date")
    end_date_raw = entry.get("end_date")

    start_date_value: date
    if start_date_raw:
        start_date_value = date.fromisoformat(str(start_date_raw))
    else:
        start_date_value = _next_reference_date(weekday)

    end_date_value: date | None
    if end_date_raw:
        end_date_value = date.fromisoformat(str(end_date_raw))
        if end_date_value < start_date_value:
            raise ValueError("end_date cannot precede start_date for schedule entries.")
    else:
        end_date_value = None

    return start_date_value, end_date_value


def _resolve_doctor_id(clinic: Clinic, entry: dict[str, Any]) -> int:
    doctor_lookup = {doctor.id: doctor for doctor in clinic.doctors}
    identifier = entry.get("doctor_id")
    if identifier not in (None, ""):
        try:
            doctor_id = int(identifier)
        except (TypeError, ValueError) as exc:
            raise ValueError("doctor_id must be an integer.") from exc
        if doctor_id not in doctor_lookup:
            raise ValueError("doctor_id must reference an existing doctor in the clinic.")
        return doctor_id

    doctor_name = (entry.get("doctor_name") or "").strip()
    if doctor_name:
        for doctor in clinic.doctors:
            if (doctor.display_name or "").strip().lower() == doctor_name.lower():
                return doctor.id
        raise ValueError(f"Doctor '{doctor_name}' does not exist in the clinic.")

    raise ValueError("Each doctor schedule requires a doctor_id or doctor_name.")


def _resolve_room_id(clinic: Clinic, entry: dict[str, Any]) -> int:
    room_lookup = {room.id: room for room in clinic.rooms}
    identifier = entry.get("room_id")
    if identifier not in (None, ""):
        try:
            room_id = int(identifier)
        except (TypeError, ValueError) as exc:
            raise ValueError("room_id must be an integer.") from exc
        if room_id not in room_lookup:
            raise ValueError("room_id must reference an existing room in the clinic.")
        return room_id

    room_name = (entry.get("room_name") or "").strip()
    if room_name:
        for room in clinic.rooms:
            if (room.name or "").strip().lower() == room_name.lower():
                return room.id
        raise ValueError(f"Room '{room_name}' does not exist in the clinic.")

    raise ValueError("Each room schedule requires a room_id or room_name.")


def _create_doctor_schedule_models(
    clinic: Clinic, entries: list[dict[str, Any]]
) -> list[DoctorSchedule]:
    schedules: list[DoctorSchedule] = []
    for entry in entries:
        weekday = _resolve_weekday(entry.get("day"))
        start_value = _parse_time(entry.get("start"), "start")
        end_value = _parse_time(entry.get("end"), "end")
        if end_value <= start_value:
            raise ValueError("Schedule end time must be after the start time.")
        start_date_value, end_date_value = _parse_schedule_dates(entry, weekday)
        label = (entry.get("label") or "").strip() or None
        notes = (entry.get("notes") or "").strip() or None
        kind = _resolve_kind(entry.get("kind"))
        doctor_id = _resolve_doctor_id(clinic, entry)
        schedules.append(
            DoctorSchedule(
                clinic_id=clinic.id,
                doctor_id=doctor_id,
                label=label,
                kind=kind,
                weekday=weekday,
                start_time=start_value,
                end_time=end_value,
                start_date=start_date_value,
                end_date=end_date_value,
                notes=notes,
            )
        )
    return schedules


def _create_room_schedule_models(
    clinic: Clinic, entries: list[dict[str, Any]]
) -> list[RoomSchedule]:
    schedules: list[RoomSchedule] = []
    for entry in entries:
        weekday = _resolve_weekday(entry.get("day"))
        start_value = _parse_time(entry.get("start"), "start")
        end_value = _parse_time(entry.get("end"), "end")
        if end_value <= start_value:
            raise ValueError("Schedule end time must be after the start time.")
        start_date_value, end_date_value = _parse_schedule_dates(entry, weekday)
        label = (entry.get("label") or "").strip() or None
        notes = (entry.get("notes") or "").strip() or None
        kind = _resolve_kind(entry.get("kind"))
        room_id = _resolve_room_id(clinic, entry)
        schedules.append(
            RoomSchedule(
                clinic_id=clinic.id,
                room_id=room_id,
                label=label,
                kind=kind,
                weekday=weekday,
                start_time=start_value,
                end_time=end_value,
                start_date=start_date_value,
                end_date=end_date_value,
                notes=notes,
            )
        )
    return schedules


@clinic_bp.post("/availability")
@jwt_required()
def update_clinic_availability() -> ResponseReturnValue:
    """Persist doctor and room schedules for the administrator's clinic."""

    admin = _current_admin()
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    clinic = Clinic.query.get(admin.clinic_id) if admin.clinic_id else None
    if not clinic:
        return jsonify(message="Clinic has not completed onboarding."), HTTPStatus.BAD_REQUEST

    payload = request.get_json(silent=True) or {}
    doctor_entries: list[dict[str, Any]] = payload.get("doctor_schedules") or []
    room_entries: list[dict[str, Any]] = payload.get("room_schedules") or []

    try:
        doctor_models = _create_doctor_schedule_models(clinic, doctor_entries)
        room_models = _create_room_schedule_models(clinic, room_entries)
    except ValueError as exc:
        db.session.rollback()
        return jsonify(message=str(exc)), HTTPStatus.BAD_REQUEST

    DoctorSchedule.query.filter_by(clinic_id=clinic.id).delete(synchronize_session=False)
    RoomSchedule.query.filter_by(clinic_id=clinic.id).delete(synchronize_session=False)

    for model in doctor_models + room_models:
        db.session.add(model)

    db.session.commit()

    return jsonify(message="Availability updated successfully."), HTTPStatus.CREATED
