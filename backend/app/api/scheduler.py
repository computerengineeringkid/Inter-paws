"""Endpoints for interacting with the scheduling engine."""
from __future__ import annotations

from http import HTTPStatus

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from backend.app.models import User
from backend.app.services.scheduler_service import find_candidate_slots_for_request

scheduler_bp = Blueprint("scheduler", __name__)


@scheduler_bp.post("/find-slots")
@jwt_required()
def find_slots() -> tuple[object, HTTPStatus]:
    """Return all feasible appointment slots for the supplied request."""

    payload = request.get_json(silent=True) or {}
    clinic_id = payload.get("clinic_id")

    if clinic_id is None:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if user is None or user.clinic_id is None:
            return (
                jsonify(message="A clinic_id must be provided for scheduling."),
                HTTPStatus.BAD_REQUEST,
            )
        clinic_id = user.clinic_id

    try:
        clinic_id_int = int(clinic_id)
    except (TypeError, ValueError):
        return (
            jsonify(message="clinic_id must be an integer."),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        slots = find_candidate_slots_for_request(clinic_id_int, payload)
    except ValueError as exc:
        return jsonify(message=str(exc)), HTTPStatus.BAD_REQUEST

    return jsonify(slots=slots), HTTPStatus.OK
