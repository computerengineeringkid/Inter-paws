"""Constraint satisfaction model for generating feasible appointment slots."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Sequence

from ortools.sat.python import cp_model


@dataclass
class TimeWindow:
    """Represents an inclusive-exclusive window of time."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("TimeWindow end must be after start.")

    def contains(self, start: datetime, end: datetime) -> bool:
        """Return whether the window fully contains the provided interval."""

        return self.start <= start and end <= self.end

    def overlaps(self, start: datetime, end: datetime) -> bool:
        """Return whether the provided interval overlaps the window."""

        return start < self.end and end > self.start


@dataclass
class DoctorAvailability:
    """Structured availability information for a doctor."""

    id: int
    specialties: Iterable[str] = field(default_factory=set)
    available_windows: Sequence[TimeWindow] = field(default_factory=tuple)
    unavailable_windows: Sequence[TimeWindow] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.specialties = {value for value in self.specialties if value}
        self.available_windows = tuple(self.available_windows)
        self.unavailable_windows = tuple(self.unavailable_windows)


@dataclass
class RoomAvailability:
    """Structured availability information for a room."""

    id: int
    room_type: str | None = None
    equipment: Iterable[str] = field(default_factory=set)
    available_windows: Sequence[TimeWindow] = field(default_factory=tuple)
    unavailable_windows: Sequence[TimeWindow] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.equipment = {value for value in self.equipment if value}
        self.available_windows = tuple(self.available_windows)
        self.unavailable_windows = tuple(self.unavailable_windows)


@dataclass
class ClinicSchedule:
    """Operating and blocked windows that apply to the entire clinic."""

    operating_windows: Sequence[TimeWindow] = field(default_factory=tuple)
    blocked_windows: Sequence[TimeWindow] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.operating_windows = tuple(self.operating_windows)
        self.blocked_windows = tuple(self.blocked_windows)


@dataclass
class AppointmentRequest:
    """Parameters describing the requested appointment."""

    start: datetime
    end: datetime
    duration_minutes: int
    granularity_minutes: int = 15
    allowed_doctor_ids: set[int] | None = None
    allowed_room_ids: set[int] | None = None
    required_specialties: set[str] | None = None
    required_room_type: str | None = None
    required_equipment: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("AppointmentRequest end must be after start.")
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive.")
        if self.granularity_minutes <= 0:
            raise ValueError("granularity_minutes must be positive.")
        if self.required_specialties:
            self.required_specialties = {value for value in self.required_specialties if value}
        self.required_equipment = {value for value in self.required_equipment if value}


Slot = tuple[int, int, datetime, datetime]
"""Return type alias for feasible appointment slots."""


def find_feasible_slots(
    doctors: Sequence[DoctorAvailability],
    rooms: Sequence[RoomAvailability],
    request: AppointmentRequest,
    clinic_schedule: ClinicSchedule | None = None,
) -> list[Slot]:
    """Return all feasible appointment slots that satisfy the provided constraints."""

    clinic_schedule = clinic_schedule or ClinicSchedule()
    candidate_starts = _generate_candidate_starts(request, clinic_schedule)
    if not candidate_starts:
        return []

    eligible_doctors = _filter_doctors(doctors, request)
    if not eligible_doctors:
        return []

    eligible_rooms = _filter_rooms(rooms, request)
    if not eligible_rooms:
        return []

    duration = timedelta(minutes=request.duration_minutes)

    doctor_domain = sorted({doctor.id for doctor in eligible_doctors})
    room_domain = sorted({room.id for room in eligible_rooms})
    slot_domain = list(range(len(candidate_starts)))

    model = cp_model.CpModel()
    doctor_var = model.NewIntVarFromDomain(
        cp_model.Domain.FromValues(doctor_domain), "doctor"
    )
    room_var = model.NewIntVarFromDomain(cp_model.Domain.FromValues(room_domain), "room")
    start_var = model.NewIntVarFromDomain(
        cp_model.Domain.FromValues(slot_domain), "start_index"
    )

    doctor_allowed_pairs = _build_allowed_pairs(
        eligible_doctors, candidate_starts, duration, start_var_index=True
    )
    if not doctor_allowed_pairs:
        return []
    model.AddAllowedAssignments([doctor_var, start_var], doctor_allowed_pairs)

    room_allowed_pairs = _build_allowed_pairs(
        eligible_rooms, candidate_starts, duration, start_var_index=True
    )
    if not room_allowed_pairs:
        return []
    model.AddAllowedAssignments([room_var, start_var], room_allowed_pairs)

    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True

    collector = _SlotCollector(doctor_var, room_var, start_var)
    status = solver.SearchForAllSolutions(model, collector)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return []

    slots: list[Slot] = []
    for doctor_id, room_id, start_index in collector.solutions:
        start_time = candidate_starts[start_index]
        end_time = start_time + duration
        slots.append((doctor_id, room_id, start_time, end_time))

    slots.sort(key=lambda value: (value[2], value[0], value[1]))
    return slots


def _generate_candidate_starts(
    request: AppointmentRequest, clinic_schedule: ClinicSchedule
) -> list[datetime]:
    """Create candidate start times within the request window and clinic rules."""

    duration = timedelta(minutes=request.duration_minutes)
    step = timedelta(minutes=request.granularity_minutes)

    starts: list[datetime] = []
    current = request.start
    while current + duration <= request.end:
        end_time = current + duration
        if _slot_allowed_by_clinic(current, end_time, clinic_schedule):
            starts.append(current)
        current += step
    return starts


def _slot_allowed_by_clinic(
    start: datetime, end: datetime, clinic_schedule: ClinicSchedule
) -> bool:
    """Return whether the slot is allowed by clinic-wide windows."""

    if clinic_schedule.operating_windows:
        if not any(window.contains(start, end) for window in clinic_schedule.operating_windows):
            return False
    if clinic_schedule.blocked_windows:
        if any(window.overlaps(start, end) for window in clinic_schedule.blocked_windows):
            return False
    return True


def _filter_doctors(
    doctors: Sequence[DoctorAvailability], request: AppointmentRequest
) -> list[DoctorAvailability]:
    """Filter doctors based on request-specific requirements."""

    required_specialties = request.required_specialties or set()
    allowed_ids = request.allowed_doctor_ids

    eligible: list[DoctorAvailability] = []
    for doctor in doctors:
        if allowed_ids is not None and doctor.id not in allowed_ids:
            continue
        if required_specialties and not required_specialties.issubset(doctor.specialties):
            continue
        eligible.append(doctor)
    return eligible


def _filter_rooms(
    rooms: Sequence[RoomAvailability], request: AppointmentRequest
) -> list[RoomAvailability]:
    """Filter rooms based on request-specific requirements."""

    allowed_ids = request.allowed_room_ids
    required_equipment = request.required_equipment
    required_room_type = request.required_room_type

    eligible: list[RoomAvailability] = []
    for room in rooms:
        if allowed_ids is not None and room.id not in allowed_ids:
            continue
        if required_room_type and room.room_type != required_room_type:
            continue
        if required_equipment and not required_equipment.issubset(room.equipment):
            continue
        eligible.append(room)
    return eligible


def _build_allowed_pairs(
    resources: Sequence[DoctorAvailability | RoomAvailability],
    candidate_starts: Sequence[datetime],
    duration: timedelta,
    *,
    start_var_index: bool,
) -> list[tuple[int, int]]:
    """Return allowed (resource, start) pairs for AddAllowedAssignments."""

    pairs: list[tuple[int, int]] = []
    for index, start_time in enumerate(candidate_starts):
        end_time = start_time + duration
        for resource in resources:
            if _resource_allows(resource, start_time, end_time):
                start_value = index if start_var_index else start_time
                pairs.append((resource.id, start_value))
    return pairs


def _resource_allows(
    resource: DoctorAvailability | RoomAvailability,
    start: datetime,
    end: datetime,
) -> bool:
    """Return whether the resource is available for the slot."""

    available_windows = getattr(resource, "available_windows", ())
    unavailable_windows = getattr(resource, "unavailable_windows", ())

    if available_windows:
        if not any(window.contains(start, end) for window in available_windows):
            return False
    if unavailable_windows:
        if any(window.overlaps(start, end) for window in unavailable_windows):
            return False
    return True


class _SlotCollector(cp_model.CpSolverSolutionCallback):
    """Collect all solutions discovered by the CP-SAT solver."""

    def __init__(
        self,
        doctor_var: cp_model.IntVar,
        room_var: cp_model.IntVar,
        start_var: cp_model.IntVar,
    ) -> None:
        super().__init__()
        self._doctor_var = doctor_var
        self._room_var = room_var
        self._start_var = start_var
        self.solutions: list[tuple[int, int, int]] = []

    def OnSolutionCallback(self) -> None:  # noqa: D401 - callback API
        self.solutions.append(
            (
                self.Value(self._doctor_var),
                self.Value(self._room_var),
                self.Value(self._start_var),
            )
        )
