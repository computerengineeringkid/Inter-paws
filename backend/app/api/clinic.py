"""Clinic onboarding endpoints."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_jwt_extended import get_jwt_identity, jwt_required
from uuid import uuid4

from backend.app.models import Appointment, Clinic, Constraint, Doctor, Pet, Room, User
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


def _current_clinic_user(*, require_admin: bool = False) -> User | None:
    """Return the authenticated clinic member or ``None`` if unauthorized."""

    user_id = get_jwt_identity()
    if not user_id:
        return None
    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None
    user = User.query.get(user_pk)
    if not user:
        return None
    role = (user.role or "").lower()
    if require_admin and role != "admin":
        return None
    if role not in {"admin", "staff"}:
        return None
    if user.clinic_id is None:
        return None
    return user


def _deserialize_room_payload(room: Room) -> tuple[str | None, list[dict[str, Any]]]:
    """Return room notes and equipment entries from the stored payload."""

    notes_value: str | None = None
    equipment_entries: list[dict[str, Any]] = []
    if room.notes:
        try:
            parsed = json.loads(room.notes)
        except json.JSONDecodeError:
            notes_value = room.notes
        else:
            if isinstance(parsed, dict):
                raw_notes = parsed.get("notes")
                notes_value = raw_notes if isinstance(raw_notes, str) else None
                raw_equipment = parsed.get("equipment", [])
                if isinstance(raw_equipment, list):
                    for index, item in enumerate(raw_equipment):
                        if not isinstance(item, dict):
                            continue
                        identifier = str(item.get("id") or f"{room.id}-{index}")
                        name_value = (item.get("name") or "").strip()
                        if not name_value:
                            continue
                        equipment_entries.append(
                            {
                                "id": identifier,
                                "name": name_value,
                                "notes": item.get("notes"),
                            }
                        )
            elif isinstance(parsed, str):
                notes_value = parsed
    return notes_value, equipment_entries


def _serialize_room(room: Room) -> dict[str, Any]:
    """Return API payload for a room including embedded equipment."""

    notes_value, equipment_entries = _deserialize_room_payload(room)
    return {
        "id": room.id,
        "name": room.name,
        "room_type": room.room_type,
        "capacity": room.capacity,
        "notes": notes_value,
        "is_active": room.is_active,
        "equipment": equipment_entries,
    }


def _persist_room_notes(room: Room, *, notes: str | None, equipment: list[dict[str, Any]] | None) -> None:
    """Persist normalized notes/equipment payload for the supplied room."""

    payload: dict[str, Any] = {}
    if notes:
        payload["notes"] = notes
    if equipment:
        payload["equipment"] = equipment
    room.notes = json.dumps(payload) if payload else None


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
        identifier = (entry.get("id") or "").strip() or uuid4().hex
        equipment_payload: dict[str, Any] = {"name": name, "id": identifier}
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
        room_notes, room_equipment = _deserialize_room_payload(room)
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
                    "id": item.get("id"),
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


@clinic_bp.get("/resources")
@jwt_required()
def list_resources() -> ResponseReturnValue:
    """Return doctors and rooms for the authenticated clinic."""

    member = _current_clinic_user()
    if not member:
        return (
            jsonify(message="Clinic membership is required."),
            HTTPStatus.FORBIDDEN,
        )

    clinic = Clinic.query.get(member.clinic_id)
    if not clinic:
        return jsonify(doctors=[], rooms=[]), HTTPStatus.OK

    doctors_payload = [
        {
            "id": doctor.id,
            "display_name": doctor.display_name,
            "specialty": doctor.specialty,
            "license_number": doctor.license_number,
            "biography": doctor.biography,
            "is_active": doctor.is_active,
        }
        for doctor in clinic.doctors
    ]

    rooms_payload = [_serialize_room(room) for room in clinic.rooms]

    return jsonify(doctors=doctors_payload, rooms=rooms_payload), HTTPStatus.OK


@clinic_bp.post("/doctors")
@jwt_required()
def create_doctor() -> ResponseReturnValue:
    """Create a doctor record for the clinic."""

    admin = _current_clinic_user(require_admin=True)
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    payload = request.get_json(silent=True) or {}
    display_name = (payload.get("display_name") or "").strip()
    if not display_name:
        return jsonify(message="display_name is required."), HTTPStatus.BAD_REQUEST

    doctor = Doctor(
        clinic_id=admin.clinic_id,
        display_name=display_name,
        specialty=(payload.get("specialty") or "").strip() or None,
        license_number=(payload.get("license_number") or "").strip() or None,
        biography=(payload.get("biography") or "").strip() or None,
        is_active=True,
    )

    db.session.add(doctor)
    db.session.commit()

    return jsonify(id=doctor.id, message="Doctor created."), HTTPStatus.CREATED


@clinic_bp.put("/doctors/<int:doctor_id>")
@jwt_required()
def update_doctor(doctor_id: int) -> ResponseReturnValue:
    """Update an existing doctor record."""

    admin = _current_clinic_user(require_admin=True)
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    doctor = Doctor.query.filter_by(id=doctor_id, clinic_id=admin.clinic_id).first()
    if not doctor:
        return jsonify(message="Doctor not found."), HTTPStatus.NOT_FOUND

    payload = request.get_json(silent=True) or {}
    if "display_name" in payload:
        name_value = (payload.get("display_name") or "").strip()
        if not name_value:
            return jsonify(message="display_name cannot be blank."), HTTPStatus.BAD_REQUEST
        doctor.display_name = name_value
    if "specialty" in payload:
        doctor.specialty = (payload.get("specialty") or "").strip() or None
    if "license_number" in payload:
        doctor.license_number = (payload.get("license_number") or "").strip() or None
    if "biography" in payload:
        doctor.biography = (payload.get("biography") or "").strip() or None
    if "is_active" in payload:
        doctor.is_active = bool(payload.get("is_active", True))

    db.session.add(doctor)
    db.session.commit()

    return jsonify(message="Doctor updated."), HTTPStatus.OK


@clinic_bp.delete("/doctors/<int:doctor_id>")
@jwt_required()
def delete_doctor(doctor_id: int) -> ResponseReturnValue:
    """Delete a doctor from the clinic."""

    admin = _current_clinic_user(require_admin=True)
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    doctor = Doctor.query.filter_by(id=doctor_id, clinic_id=admin.clinic_id).first()
    if not doctor:
        return jsonify(message="Doctor not found."), HTTPStatus.NOT_FOUND

    db.session.delete(doctor)
    db.session.commit()

    return jsonify(message="Doctor removed."), HTTPStatus.OK


@clinic_bp.post("/rooms")
@jwt_required()
def create_room() -> ResponseReturnValue:
    """Create a room for the current clinic."""

    admin = _current_clinic_user(require_admin=True)
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify(message="name is required."), HTTPStatus.BAD_REQUEST

    capacity_value = payload.get("capacity")
    capacity_int = None
    if capacity_value not in (None, ""):
        try:
            capacity_int = int(capacity_value)
        except (TypeError, ValueError):
            return jsonify(message="capacity must be a number."), HTTPStatus.BAD_REQUEST

    notes_value = (payload.get("notes") or "").strip() or None

    room = Room(
        clinic_id=admin.clinic_id,
        name=name,
        room_type=(payload.get("room_type") or "").strip() or None,
        capacity=capacity_int,
        is_active=True,
    )

    db.session.add(room)
    db.session.flush()
    _persist_room_notes(room, notes=notes_value, equipment=[])
    db.session.add(room)
    db.session.commit()

    return jsonify(id=room.id, message="Room created."), HTTPStatus.CREATED


@clinic_bp.put("/rooms/<int:room_id>")
@jwt_required()
def update_room(room_id: int) -> ResponseReturnValue:
    """Update room metadata for the clinic."""

    admin = _current_clinic_user(require_admin=True)
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    room = Room.query.filter_by(id=room_id, clinic_id=admin.clinic_id).first()
    if not room:
        return jsonify(message="Room not found."), HTTPStatus.NOT_FOUND

    payload = request.get_json(silent=True) or {}
    notes_value, equipment_entries = _deserialize_room_payload(room)

    if "name" in payload:
        name_value = (payload.get("name") or "").strip()
        if not name_value:
            return jsonify(message="name cannot be blank."), HTTPStatus.BAD_REQUEST
        room.name = name_value
    if "room_type" in payload:
        room.room_type = (payload.get("room_type") or "").strip() or None
    if "capacity" in payload:
        capacity_value = payload.get("capacity")
        if capacity_value in (None, ""):
            room.capacity = None
        else:
            try:
                room.capacity = int(capacity_value)
            except (TypeError, ValueError):
                return jsonify(message="capacity must be numeric."), HTTPStatus.BAD_REQUEST
    if "notes" in payload:
        notes_value = (payload.get("notes") or "").strip() or None
    if "is_active" in payload:
        room.is_active = bool(payload.get("is_active", True))

    _persist_room_notes(room, notes=notes_value, equipment=equipment_entries)
    db.session.add(room)
    db.session.commit()

    return jsonify(message="Room updated."), HTTPStatus.OK


@clinic_bp.delete("/rooms/<int:room_id>")
@jwt_required()
def delete_room(room_id: int) -> ResponseReturnValue:
    """Remove a room and its equipment."""

    admin = _current_clinic_user(require_admin=True)
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    room = Room.query.filter_by(id=room_id, clinic_id=admin.clinic_id).first()
    if not room:
        return jsonify(message="Room not found."), HTTPStatus.NOT_FOUND

    db.session.delete(room)
    db.session.commit()

    return jsonify(message="Room removed."), HTTPStatus.OK


@clinic_bp.post("/rooms/<int:room_id>/equipment")
@jwt_required()
def add_equipment(room_id: int) -> ResponseReturnValue:
    """Attach a piece of equipment to a room."""

    admin = _current_clinic_user(require_admin=True)
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    room = Room.query.filter_by(id=room_id, clinic_id=admin.clinic_id).first()
    if not room:
        return jsonify(message="Room not found."), HTTPStatus.NOT_FOUND

    payload = request.get_json(silent=True) or {}
    name_value = (payload.get("name") or "").strip()
    if not name_value:
        return jsonify(message="Equipment name is required."), HTTPStatus.BAD_REQUEST

    notes_value, equipment_entries = _deserialize_room_payload(room)
    new_entry = {"id": uuid4().hex, "name": name_value}
    entry_notes = (payload.get("notes") or "").strip()
    if entry_notes:
        new_entry["notes"] = entry_notes
    equipment_entries.append(new_entry)

    _persist_room_notes(room, notes=notes_value, equipment=equipment_entries)
    db.session.add(room)
    db.session.commit()

    return jsonify(message="Equipment added.", id=new_entry["id"]), HTTPStatus.CREATED


@clinic_bp.delete("/rooms/<int:room_id>/equipment/<string:equipment_id>")
@jwt_required()
def remove_equipment(room_id: int, equipment_id: str) -> ResponseReturnValue:
    """Remove an equipment entry from a room."""

    admin = _current_clinic_user(require_admin=True)
    if not admin:
        return (
            jsonify(message="Administrator privileges are required."),
            HTTPStatus.FORBIDDEN,
        )

    room = Room.query.filter_by(id=room_id, clinic_id=admin.clinic_id).first()
    if not room:
        return jsonify(message="Room not found."), HTTPStatus.NOT_FOUND

    notes_value, equipment_entries = _deserialize_room_payload(room)
    filtered = [entry for entry in equipment_entries if entry.get("id") != equipment_id]
    if len(filtered) == len(equipment_entries):
        return jsonify(message="Equipment not found."), HTTPStatus.NOT_FOUND

    _persist_room_notes(room, notes=notes_value, equipment=filtered)
    db.session.add(room)
    db.session.commit()

    return jsonify(message="Equipment removed."), HTTPStatus.OK


@clinic_bp.get("/schedule")
@jwt_required()
def clinic_schedule() -> ResponseReturnValue:
    """Return appointments for the clinic in the requested window."""

    member = _current_clinic_user()
    if not member:
        return (
            jsonify(message="Clinic membership is required."),
            HTTPStatus.FORBIDDEN,
        )

    clinic = Clinic.query.get(member.clinic_id)
    if not clinic:
        return jsonify(appointments=[]), HTTPStatus.OK

    start_param = (request.args.get("start") or "").strip()
    view = (request.args.get("view") or "week").strip().lower()

    try:
        if start_param:
            start_dt = datetime.fromisoformat(start_param)
        else:
            start_dt = datetime.utcnow()
    except ValueError:
        return jsonify(message="start must be an ISO formatted date."), HTTPStatus.BAD_REQUEST

    if start_dt.tzinfo is not None:
        start_dt = start_dt.astimezone(tz=None).replace(tzinfo=None)

    start_floor = datetime.combine(start_dt.date(), time.min)
    if view == "day":
        end_dt = start_floor + timedelta(days=1)
    else:
        end_dt = start_floor + timedelta(days=7)

    appointments = (
        Appointment.query.filter_by(clinic_id=clinic.id)
        .filter(Appointment.start_time >= start_floor)
        .filter(Appointment.start_time < end_dt)
        .order_by(Appointment.start_time.asc())
        .all()
    )

    payload = [
        {
            "id": appt.id,
            "start_time": appt.start_time.isoformat(),
            "end_time": appt.end_time.isoformat(),
            "status": appt.status,
            "doctor_name": appt.doctor.display_name if appt.doctor else None,
            "room_name": appt.room.name if appt.room else None,
            "pet_name": appt.pet.name if appt.pet else None,
            "owner_name": appt.owner.full_name if appt.owner else None,
            "reason": appt.reason,
        }
        for appt in appointments
    ]

    return jsonify(appointments=payload), HTTPStatus.OK


@clinic_bp.get("/patients")
@jwt_required()
def list_patients() -> ResponseReturnValue:
    """Return pets and owners for the authenticated clinic."""

    member = _current_clinic_user()
    if not member:
        return (
            jsonify(message="Clinic membership is required."),
            HTTPStatus.FORBIDDEN,
        )

    pets = Pet.query.filter_by(clinic_id=member.clinic_id).all()
    owners = User.query.filter_by(clinic_id=member.clinic_id, role="client").all()

    pets_payload = [
        {
            "id": pet.id,
            "name": pet.name,
            "species": pet.species,
            "breed": pet.breed,
            "owner_name": pet.owner.full_name if pet.owner else None,
        }
        for pet in pets
    ]

    owners_payload = [
        {
            "id": owner.id,
            "name": owner.full_name,
            "email": owner.email,
        }
        for owner in owners
    ]

    return jsonify(pets=pets_payload, owners=owners_payload), HTTPStatus.OK
