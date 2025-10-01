"""End-to-end tests for the clinic onboarding workflow."""
from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any
import unittest

from backend.app import create_app
from backend.app.models import Clinic, Constraint, Doctor, Room, User
from backend.extensions import bcrypt, db


class ClinicOnboardingTestCase(unittest.TestCase):
    """Exercise the onboarding API using the full Flask stack."""

    def setUp(self) -> None:  # noqa: D401 - inherited documentation
        """Configure a fresh application and database for each test."""

        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite://",
            JWT_SECRET_KEY="test-secret-key",
        )

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        admin_password = "super-secret"
        admin = User(
            email="admin@example.com",
            password_hash=bcrypt.generate_password_hash(admin_password).decode("utf-8"),
            full_name="Clinic Admin",
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
        self.admin = admin
        self.admin_password = admin_password

        staff_password = "staff-pass"
        staff = User(
            email="staff@example.com",
            password_hash=bcrypt.generate_password_hash(staff_password).decode("utf-8"),
            full_name="Clinic Staff",
            role="staff",
        )
        db.session.add(staff)
        db.session.commit()
        self.staff = staff
        self.staff_password = staff_password

        self.client = self.app.test_client()

    def tearDown(self) -> None:  # noqa: D401 - inherited documentation
        """Tear down the database and application context."""

        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _login(self, email: str, password: str) -> str:
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.get_data(as_text=True))
        data = response.get_json()
        assert data is not None
        token = data.get("access_token")
        self.assertTrue(token)
        return token

    def _submit_onboarding(self, token: str, payload: dict[str, Any]) -> Any:
        response = self.client.post(
            "/api/clinic/onboarding",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        return response

    # ------------------------------------------------------------------
    # Test cases
    # ------------------------------------------------------------------
    def test_onboarding_creates_clinic_and_related_records(self) -> None:
        token = self._login(self.admin.email, self.admin_password)

        payload = {
            "clinic": {
                "name": "Sunrise Animal Hospital",
                "email": "hello@sunrise.test",
                "phone_number": "555-0100",
                "address": "100 Market Street",
            },
            "doctors": [
                {
                    "display_name": "Dr. Jane Smith",
                    "specialty": "Surgery",
                    "license_number": "LIC123",
                    "biography": "10 years of surgical experience.",
                },
                {
                    "display_name": "Dr. Carlos Ruiz",
                    "specialty": "Dentistry",
                    "license_number": "LIC456",
                },
            ],
            "rooms": [
                {
                    "name": "Exam Room 1",
                    "room_type": "Exam",
                    "capacity": 1,
                    "notes": "Bright and spacious.",
                },
                {
                    "name": "Surgery Suite",
                    "room_type": "Surgery",
                    "capacity": 1,
                },
            ],
            "equipment": [
                {
                    "name": "Digital X-Ray",
                    "room": "Exam Room 1",
                    "notes": "Calibrate quarterly",
                },
                {
                    "name": "Anesthesia Machine",
                    "room": "Surgery Suite",
                },
            ],
            "schedule_rules": {
                "operating_hours": [
                    {"day": "Monday", "start": "08:00", "end": "17:00", "notes": "Open for walk-ins."},
                    {"day": "Tuesday", "start": "09:00", "end": "18:00"},
                ]
            },
        }

        response = self._submit_onboarding(token, payload)
        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.get_data(as_text=True))
        data = response.get_json()
        assert data is not None
        self.assertIn("clinic_id", data)

        clinic = Clinic.query.get(data["clinic_id"])
        assert clinic is not None
        self.assertEqual(clinic.name, payload["clinic"]["name"])
        self.assertEqual(clinic.email, payload["clinic"]["email"])
        self.assertEqual(clinic.phone_number, payload["clinic"]["phone_number"])
        self.assertEqual(clinic.address, payload["clinic"]["address"])

        self.assertEqual(self.admin.clinic_id, clinic.id)

        doctors = Doctor.query.filter_by(clinic_id=clinic.id).order_by(Doctor.display_name).all()
        self.assertEqual(len(doctors), 2)
        self.assertEqual(doctors[0].display_name, "Dr. Carlos Ruiz")
        self.assertEqual(doctors[1].display_name, "Dr. Jane Smith")

        rooms = Room.query.filter_by(clinic_id=clinic.id).order_by(Room.name).all()
        self.assertEqual(len(rooms), 2)
        room_payload = json.loads(rooms[0].notes)
        self.assertIn("equipment", room_payload)
        self.assertEqual(room_payload["equipment"][0]["name"], "Digital X-Ray")

        constraints = (
            Constraint.query.filter_by(clinic_id=clinic.id)
            .order_by(Constraint.start_time)
            .all()
        )
        self.assertEqual(len(constraints), 2)
        self.assertTrue(all(constraint.title.startswith("Operating hours") for constraint in constraints))
        self.assertEqual(
            constraints[0].start_time.time().isoformat(timespec="minutes"),
            payload["schedule_rules"]["operating_hours"][0]["start"],
        )

        # Fetch the onboarding payload to ensure serialization works end-to-end.
        response = self.client.get(
            "/api/clinic/onboarding",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.get_data(as_text=True))
        returned = response.get_json()
        assert returned is not None
        self.assertEqual(returned["clinic"]["name"], payload["clinic"]["name"])
        self.assertEqual(len(returned["doctors"]), 2)
        self.assertEqual(len(returned["rooms"]), 2)
        self.assertEqual(len(returned["equipment"]), 2)
        self.assertEqual(len(returned["schedule_rules"]["operating_hours"]), 2)

    def test_requires_admin_role(self) -> None:
        token = self._login(self.staff.email, self.staff_password)
        response = self._submit_onboarding(token, {"clinic": {"name": "Test"}})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_requires_authentication(self) -> None:
        response = self.client.post("/api/clinic/onboarding", json={"clinic": {"name": "Test"}})
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_validates_room_capacity(self) -> None:
        token = self._login(self.admin.email, self.admin_password)
        payload = {
            "clinic": {"name": "Capacity Clinic"},
            "rooms": [{"name": "Exam Room", "capacity": "many"}],
        }
        response = self._submit_onboarding(token, payload)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(Clinic.query.count(), 0)

    def test_validates_operating_hours(self) -> None:
        token = self._login(self.admin.email, self.admin_password)
        payload = {
            "clinic": {"name": "Hours Clinic"},
            "schedule_rules": {
                "operating_hours": [{"day": "Monday", "start": "10:00", "end": "09:00"}]
            },
        }
        response = self._submit_onboarding(token, payload)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(Constraint.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
