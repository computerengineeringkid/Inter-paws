"""Tests for the LLM ranking layer and scheduling fallbacks."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.app.services import scheduler_service
from backend.app.services.llm_client import LLMRankingError, RankedSlot, parse_llm_response


class FakeClinic:
    """Simple stand-in for the Clinic model."""

    def __init__(self, name: str = "Interpaws Central") -> None:
        self.name = name


class LLMIntegrationTests(unittest.TestCase):
    """Validate ranking behaviour with and without LLM support."""

    def setUp(self) -> None:
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        self.app_context.pop()

    def test_parse_llm_response_extracts_rankings(self) -> None:
        """The JSON payload embedded in text is parsed successfully."""

        response = "Here you go! {\"recommendations\":[{\"slot_id\":1,\"score\":0.9,\"rationale\":\"Early slot\"}]}"
        result = parse_llm_response(response)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].slot_id, 1)
        self.assertAlmostEqual(result[0].score or 0.0, 0.9)
        self.assertEqual(result[0].rationale, "Early slot")

    def test_rank_slots_uses_llm_output(self) -> None:
        """Slots are returned in the order suggested by the LLM."""

        clinic = FakeClinic()
        payload = {
            "reason_for_visit": "Annual check-up",
            "urgency": "Routine",
            "preferred_start": "2024-05-01T09:00:00",
            "preferred_end": "2024-05-01T17:00:00",
        }
        slots = [
            {
                "slot_id": 1,
                "doctor_id": 7,
                "room_id": 3,
                "start_time": "2024-05-01T09:00:00",
                "end_time": "2024-05-01T09:30:00",
            },
            {
                "slot_id": 2,
                "doctor_id": 8,
                "room_id": 4,
                "start_time": "2024-05-01T10:00:00",
                "end_time": "2024-05-01T10:30:00",
            },
        ]

        with patch.object(
            scheduler_service,
            "rank_slots_with_llm",
            return_value=[RankedSlot(slot_id=2, score=0.92, rationale="Aligns with lunch break"),
                          RankedSlot(slot_id=1, score=0.75, rationale="Backup choice")],
        ):
            ranked = scheduler_service._rank_slots(
                clinic=clinic,
                payload=payload,
                serialized_slots=slots,
                duration_minutes=30,
            )

        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["doctor_id"], 8)
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertEqual(ranked[0]["score"], 0.92)
        self.assertIn("Aligns", ranked[0]["rationale"])

    def test_rank_slots_falls_back_when_llm_fails(self) -> None:
        """Heuristic fallback is used when the LLM cannot provide rankings."""

        clinic = FakeClinic()
        payload = {
            "reason_for_visit": "Vaccination",
            "urgency": "Routine",
            "preferred_start": "2024-05-01T09:00:00",
            "preferred_end": "2024-05-01T12:00:00",
        }
        slots = [
            {
                "slot_id": 1,
                "doctor_id": 2,
                "room_id": 1,
                "start_time": "2024-05-01T11:00:00",
                "end_time": "2024-05-01T11:30:00",
            },
            {
                "slot_id": 2,
                "doctor_id": 3,
                "room_id": 2,
                "start_time": "2024-05-01T09:30:00",
                "end_time": "2024-05-01T10:00:00",
            },
        ]

        with patch.object(
            scheduler_service,
            "rank_slots_with_llm",
            side_effect=LLMRankingError("model offline"),
        ):
            ranked = scheduler_service._rank_slots(
                clinic=clinic,
                payload=payload,
                serialized_slots=slots,
                duration_minutes=30,
            )

        self.assertEqual(len(ranked), 2)
        # Earliest slot should come first in fallback order
        self.assertEqual(ranked[0]["start_time"], "2024-05-01T09:30:00")
        self.assertIn("earliest", ranked[0]["rationale"].lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
