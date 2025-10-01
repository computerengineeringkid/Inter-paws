"""Unit tests for the OR-Tools constraint model."""
from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from ai.models.constraint_model import (
    AppointmentRequest,
    ClinicSchedule,
    DoctorAvailability,
    RoomAvailability,
    TimeWindow,
    find_feasible_slots,
)


class ConstraintModelTestCase(unittest.TestCase):
    """Validate the mathematical feasibility solver."""

    def test_simple_slot_generation(self) -> None:
        """Slots are produced when doctor and room are available."""

        doctor = DoctorAvailability(
            id=1,
            available_windows=[
                TimeWindow(start=datetime(2024, 1, 1, 9, 0), end=datetime(2024, 1, 1, 12, 0))
            ],
        )
        room = RoomAvailability(
            id=1,
            room_type="Exam",
            available_windows=[
                TimeWindow(start=datetime(2024, 1, 1, 9, 0), end=datetime(2024, 1, 1, 12, 0))
            ],
        )
        request = AppointmentRequest(
            start=datetime(2024, 1, 1, 9, 0),
            end=datetime(2024, 1, 1, 12, 0),
            duration_minutes=30,
            granularity_minutes=30,
        )
        clinic_schedule = ClinicSchedule(
            operating_windows=[
                TimeWindow(start=datetime(2024, 1, 1, 8, 0), end=datetime(2024, 1, 1, 18, 0))
            ]
        )

        slots = find_feasible_slots([doctor], [room], request, clinic_schedule)

        expected_starts = [
            datetime(2024, 1, 1, 9, 0),
            datetime(2024, 1, 1, 9, 30),
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 1, 10, 30),
            datetime(2024, 1, 1, 11, 0),
            datetime(2024, 1, 1, 11, 30),
        ]
        self.assertEqual(len(slots), len(expected_starts))
        self.assertListEqual(
            [(slot[2], slot[3]) for slot in slots],
            [
                (start, start + timedelta(minutes=request.duration_minutes))
                for start in expected_starts
            ],
        )

    def test_no_doctor_matches_specialty(self) -> None:
        """No slots are returned when specialty requirement cannot be met."""

        doctor = DoctorAvailability(id=1, specialties={"Dentistry"})
        room = RoomAvailability(id=1)
        request = AppointmentRequest(
            start=datetime(2024, 1, 2, 9, 0),
            end=datetime(2024, 1, 2, 10, 0),
            duration_minutes=30,
            required_specialties={"Surgery"},
        )

        slots = find_feasible_slots([doctor], [room], request)
        self.assertEqual(slots, [])

    def test_equipment_requirement_filters_rooms(self) -> None:
        """Required equipment narrows results to matching rooms and slots."""

        doctor = DoctorAvailability(
            id=5,
            specialties={"Surgery"},
            available_windows=[
                TimeWindow(start=datetime(2024, 1, 3, 9, 0), end=datetime(2024, 1, 3, 13, 0))
            ],
            unavailable_windows=[
                TimeWindow(start=datetime(2024, 1, 3, 10, 0), end=datetime(2024, 1, 3, 11, 0))
            ],
        )
        room_with_equipment = RoomAvailability(
            id=3,
            room_type="Surgery",
            equipment={"Anesthesia"},
            available_windows=[
                TimeWindow(start=datetime(2024, 1, 3, 9, 0), end=datetime(2024, 1, 3, 13, 0))
            ],
        )
        room_without_equipment = RoomAvailability(
            id=4,
            room_type="Surgery",
        )

        request = AppointmentRequest(
            start=datetime(2024, 1, 3, 9, 0),
            end=datetime(2024, 1, 3, 13, 0),
            duration_minutes=60,
            granularity_minutes=30,
            required_equipment={"Anesthesia"},
            required_specialties={"Surgery"},
        )

        slots = find_feasible_slots(
            [doctor],
            [room_with_equipment, room_without_equipment],
            request,
        )

        expected_starts = [
            datetime(2024, 1, 3, 9, 0),
            datetime(2024, 1, 3, 11, 0),
            datetime(2024, 1, 3, 11, 30),
            datetime(2024, 1, 3, 12, 0),
        ]
        self.assertTrue(all(slot[1] == room_with_equipment.id for slot in slots))
        self.assertEqual([slot[2] for slot in slots], expected_starts)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
