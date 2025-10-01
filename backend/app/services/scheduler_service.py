"""Service for orchestrating the constraint solver to find appointment slots."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable

from ai.models.constraint_model import (
    AppointmentRequest,
    ClinicSchedule,
    DoctorAvailability,
    RoomAvailability,
    TimeWindow,
    find_feasible_slots,
)
from backend.app.models import Clinic, Constraint, Doctor, Room


def find_candidate_slots_for_request(
    clinic_id: int, payload: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return serialized appointment slots for the provided clinic and request."""

    clinic = Clinic.query.get(clinic_id)
    if clinic is None:
        raise ValueError(f"Clinic {clinic_id} does not exist.")

    doctors = [doctor for doctor in clinic.doctors if doctor.is_active]
    rooms = [room for room in clinic.rooms if room.is_active]
    constraints = Constraint.query.filter_by(clinic_id=clinic_id).all()

    appointment_request = _build_request(payload)
    clinic_schedule = _build_clinic_schedule(payload, constraints)
    doctor_availability = _build_doctor_availability(doctors, constraints)
    room_availability = _build_room_availability(rooms, constraints)

    slots = find_feasible_slots(
        doctor_availability, room_availability, appointment_request, clinic_schedule
    )

    return [
        {
            "doctor_id": doctor_id,
            "room_id": room_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        for doctor_id, room_id, start_time, end_time in slots
    ]


def _build_request(payload: dict[str, Any]) -> AppointmentRequest:
    """Translate JSON payload into an AppointmentRequest."""

    try:
        start = _parse_datetime(payload["start"])
        end = _parse_datetime(payload["end"])
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError("'start' and 'end' are required fields.") from exc

    duration = int(payload.get("duration_minutes", 0))
    granularity = int(payload.get("granularity_minutes", 15))

    doctor_ids = _parse_int_set(payload.get("doctor_ids"))
    room_ids = _parse_int_set(payload.get("room_ids"))

    required_specialties = _parse_str_set(payload.get("required_specialties"))
    required_equipment = _parse_str_set(payload.get("required_equipment"))
    required_room_type = payload.get("required_room_type")

    return AppointmentRequest(
        start=start,
        end=end,
        duration_minutes=duration,
        granularity_minutes=granularity,
        allowed_doctor_ids=doctor_ids,
        allowed_room_ids=room_ids,
        required_specialties=required_specialties,
        required_room_type=required_room_type,
        required_equipment=required_equipment,
    )


def _build_clinic_schedule(
    payload: dict[str, Any], constraints: Iterable[Constraint]
) -> ClinicSchedule:
    """Create clinic-wide scheduling windows from payload and database records."""

    operating_windows: list[TimeWindow] = []
    for window in payload.get("operating_hours", []) or []:
        try:
            start = _parse_datetime(window["start"])
            end = _parse_datetime(window["end"])
        except (KeyError, ValueError) as exc:  # pragma: no cover - validation
            raise ValueError(
                "Operating hours must include valid 'start' and 'end' timestamps."
            ) from exc
        operating_windows.append(TimeWindow(start=start, end=end))

    clinic_blocks = [
        TimeWindow(start=constraint.start_time, end=constraint.end_time)
        for constraint in constraints
        if constraint.doctor_id is None and constraint.room_id is None
    ]

    return ClinicSchedule(
        operating_windows=operating_windows,
        blocked_windows=clinic_blocks,
    )


def _build_doctor_availability(
    doctors: Iterable[Doctor], constraints: Iterable[Constraint]
) -> list[DoctorAvailability]:
    """Aggregate availability information for doctors."""

    blocks: dict[int, list[TimeWindow]] = defaultdict(list)
    for constraint in constraints:
        if constraint.doctor_id is None:
            continue
        blocks[constraint.doctor_id].append(
            TimeWindow(start=constraint.start_time, end=constraint.end_time)
        )

    availabilities: list[DoctorAvailability] = []
    for doctor in doctors:
        specialties = {doctor.specialty} if doctor.specialty else set()
        availabilities.append(
            DoctorAvailability(
                id=doctor.id,
                specialties=specialties,
                unavailable_windows=blocks.get(doctor.id, ()),
            )
        )
    return availabilities


def _build_room_availability(
    rooms: Iterable[Room], constraints: Iterable[Constraint]
) -> list[RoomAvailability]:
    """Aggregate availability information for rooms."""

    blocks: dict[int, list[TimeWindow]] = defaultdict(list)
    for constraint in constraints:
        if constraint.room_id is None:
            continue
        blocks[constraint.room_id].append(
            TimeWindow(start=constraint.start_time, end=constraint.end_time)
        )

    availabilities: list[RoomAvailability] = []
    for room in rooms:
        availabilities.append(
            RoomAvailability(
                id=room.id,
                room_type=room.room_type,
                unavailable_windows=blocks.get(room.id, ()),
            )
        )
    return availabilities


def _parse_datetime(value: Any) -> datetime:
    """Parse ISO formatted timestamps into datetime objects."""

    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):  # pragma: no cover - defensive
        raise ValueError("Timestamp values must be ISO formatted strings.")
    text = value.strip()
    if not text:
        raise ValueError("Timestamp values cannot be blank.")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _parse_int_set(values: Any) -> set[int] | None:
    """Convert a collection of values into a set of ints."""

    if values in (None, ""):
        return None
    result: set[int] = set()
    for item in values:
        if item in (None, ""):
            continue
        result.add(int(item))
    return result or None


def _parse_str_set(values: Any) -> set[str] | None:
    """Convert a collection of values into a normalized set of strings."""

    if values in (None, ""):
        return None
    result: set[str] = set()
    for item in values:
        if not item:
            continue
        result.add(str(item))
    return result or None
