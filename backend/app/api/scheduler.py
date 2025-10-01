"""Endpoints for interacting with the scheduling engine."""
from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from backend.app.models import User
from backend.app.services.scheduler_service import find_candidate_slots_for_request

scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.post("/find-slots")
def find_slots() -> tuple[object, HTTPStatus]:
    """Return a ranked set of appointment slots for the supplied request."""

    payload = request.get_json(silent=True) or {}
    clinic_id = payload.get("clinic_id")

    if clinic_id is None:
        try:
            verify_jwt_in_request(optional=True)
        except Exception:  # pragma: no cover - optional JWT
            user = None
        else:
            identity = get_jwt_identity()
            try:
                user_id = int(identity) if identity is not None else None
            except (TypeError, ValueError):  # pragma: no cover - defensive
                user_id = None
            user = User.query.get(user_id) if user_id is not None else None
        if user is not None and user.clinic_id is not None:
            clinic_id = user.clinic_id

    if clinic_id is None:
        return (
            jsonify(message="A clinic_id must be provided for scheduling."),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        clinic_id_int = int(clinic_id)
    except (TypeError, ValueError):
        return (
            jsonify(message="clinic_id must be an integer."),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        ranked_slots = find_candidate_slots_for_request(clinic_id_int, payload)
    except ValueError as exc:
        return jsonify(message=str(exc)), HTTPStatus.BAD_REQUEST

    return jsonify(suggestions=ranked_slots), HTTPStatus.OK
