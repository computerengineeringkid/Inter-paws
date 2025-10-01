from __future__ import annotations

from datetime import datetime, timedelta
from http import HTTPStatus
import unittest

from backend.app import create_app
from backend.app.models import (
    Appointment,
    AuditLog,
    Clinic,
    Doctor,
    FeedbackEvent,
    Room,
    User,
)
from backend.extensions import bcrypt, db


class FeedbackAuditTestCase(unittest.TestCase):
    """Validate appointment booking feedback capture and audit logging."""

    def setUp(self) -> None:  # noqa: D401 - documented in base class
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite://",
            JWT_SECRET_KEY="test-secret",
        )

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        clinic = Clinic(name="Evergreen Veterinary")
        db.session.add(clinic)
        db.session.flush()

        doctor = Doctor(
            clinic_id=clinic.id,
            display_name="Dr. Nia Patel",
            specialty="General Practice",
        )
        room = Room(clinic_id=clinic.id, name="Exam 1", room_type="Exam")

        password = bcrypt.generate_password_hash("owner-pass").decode("utf-8")
        user = User(
            email="owner@example.com",
            password_hash=password,
            full_name="Pet Owner",
            role="staff",
            clinic_id=clinic.id,
        )

        db.session.add_all([doctor, room, user])
        db.session.commit()

        self.client = self.app.test_client()
        self.clinic = clinic
        self.doctor = doctor
        self.room = room
        self.user = user

    def tearDown(self) -> None:  # noqa: D401 - documented in base class
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _login(self) -> str:
        response = self.client.post(
            "/api/auth/login",
            json={"email": self.user.email, "password": "owner-pass"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.get_data(as_text=True))
        payload = response.get_json()
        assert payload is not None
        token = payload.get("access_token")
        self.assertTrue(token)
        return token

    def test_booking_creates_feedback_and_audit_entries(self) -> None:
        token = self._login()

        login_logs = AuditLog.query.order_by(AuditLog.id).all()
        self.assertEqual(len(login_logs), 1)
        self.assertEqual(login_logs[0].action, "auth.login")
        self.assertEqual(login_logs[0].user_id, self.user.id)
        self.assertEqual(login_logs[0].clinic_id, self.clinic.id)
        self.assertEqual(len(login_logs[0].request_hash), 64)
        self.assertEqual(len(login_logs[0].response_hash), 64)

        start_time = datetime(2024, 3, 1, 9, 0, 0)
        end_time = start_time + timedelta(minutes=30)

        response = self.client.post(
            "/api/schedule/book",
            json={
                "clinic_id": self.clinic.id,
                "suggestion": {
                    "rank": 1,
                    "score": 0.92,
                    "doctor_id": self.doctor.id,
                    "room_id": self.room.id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
                "reason": "Wellness exam",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.get_data(as_text=True))
        data = response.get_json()
        assert data is not None
        appointment_payload = data.get("appointment") or {}
        appointment_id = appointment_payload.get("id")
        self.assertIsNotNone(appointment_id)

        appointment = Appointment.query.get(appointment_id)
        assert appointment is not None
        self.assertEqual(appointment.clinic_id, self.clinic.id)
        self.assertEqual(appointment.doctor_id, self.doctor.id)
        self.assertEqual(appointment.room_id, self.room.id)
        self.assertEqual(appointment.start_time, start_time)
        self.assertEqual(appointment.end_time, end_time)

        feedback_events = FeedbackEvent.query.filter_by(appointment_id=appointment.id).all()
        self.assertEqual(len(feedback_events), 1)
        feedback_event = feedback_events[0]
        self.assertEqual(feedback_event.user_id, self.user.id)
        self.assertEqual(feedback_event.suggestion_rank, 1)
        self.assertAlmostEqual(feedback_event.suggestion_score or 0, 0.92, places=2)
        self.assertEqual(feedback_event.suggestion_doctor_id, self.doctor.id)
        self.assertEqual(feedback_event.suggestion_room_id, self.room.id)
        self.assertEqual(feedback_event.suggestion_start_time, start_time)
        self.assertEqual(feedback_event.suggestion_end_time, end_time)

        logs = AuditLog.query.order_by(AuditLog.id).all()
        self.assertEqual(len(logs), 2)
        booking_log = logs[-1]
        self.assertEqual(booking_log.action, "appointment.booked")
        self.assertEqual(booking_log.entity_type, "appointment")
        self.assertEqual(booking_log.entity_id, appointment.id)
        self.assertEqual(booking_log.user_id, self.user.id)
        self.assertEqual(booking_log.clinic_id, self.clinic.id)
        self.assertEqual(booking_log.method, "POST")
        self.assertEqual(booking_log.path, "/api/schedule/book")
        self.assertEqual(len(booking_log.request_hash), 64)
        self.assertEqual(len(booking_log.response_hash), 64)
