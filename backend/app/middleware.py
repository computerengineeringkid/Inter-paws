"""Application middleware utilities such as audit logging."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from flask import Flask, current_app, g, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy.exc import SQLAlchemyError

from backend.app.models import AuditLog, User
from backend.extensions import db


@dataclass(slots=True)
class _AuditConfig:
    action: str
    entity_type: str


SIGNIFICANT_ACTIONS: dict[tuple[str, str], _AuditConfig] = {
    ("POST", "/api/auth/login"): _AuditConfig(
        action="auth.login",
        entity_type="user",
    ),
    ("POST", "/api/schedule/book"): _AuditConfig(
        action="appointment.booked",
        entity_type="appointment",
    ),
    ("POST", "/api/clinic/onboarding"): _AuditConfig(
        action="clinic.onboarded",
        entity_type="clinic",
    ),
}


def register_audit_middleware(app: Flask) -> None:
    """Attach middleware that records audit logs for significant actions."""

    @app.before_request
    def _capture_audit_context() -> None:  # pragma: no cover - integration tested
        method = request.method.upper()
        normalized_path = _normalize_path(request.path)
        config = SIGNIFICANT_ACTIONS.get((method, normalized_path))
        if not config:
            g.audit_context = None
            return

        request_bytes = request.get_data(cache=True) or b""
        g.audit_context = {
            "config": config,
            "method": method,
            "path": normalized_path,
            "request_bytes": request_bytes,
            "description": None,
        }

    @app.after_request
    def _persist_audit_log(response):  # pragma: no cover - integration tested
        context: dict[str, Any] | None = getattr(g, "audit_context", None)
        if not context:
            return response

        if response.status_code >= 400:
            return response

        config: _AuditConfig = context["config"]
        user = _resolve_user(config.action, context["request_bytes"])
        clinic_id = user.clinic_id if user else None

        entity_id = _determine_entity_id(config.action, response, user)
        description = context.get("description") or _default_description(
            config.action, user, entity_id
        )

        audit_log = AuditLog(
            clinic_id=clinic_id,
            user_id=user.id if user else None,
            entity_type=config.entity_type,
            entity_id=entity_id,
            action=config.action,
            description=description,
            changes=None,
            method=context["method"],
            path=context["path"],
            request_hash=_hash_request(
                context["method"], context["path"], context["request_bytes"]
            ),
            response_hash=_hash_response(response),
        )

        db.session.add(audit_log)
        try:
            db.session.commit()
        except SQLAlchemyError:  # pragma: no cover - defensive
            db.session.rollback()
            current_app.logger.exception("Failed to persist audit log entry")

        return response


def _normalize_path(path: str) -> str:
    if path != "/" and path.endswith("/"):
        return path[:-1]
    return path


def _resolve_user(action: str, request_bytes: bytes) -> User | None:
    user = _current_user()
    if user:
        return user

    if action == "auth.login":
        try:
            payload = json.loads(request_bytes.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return None
        email = (payload.get("email") or "").strip().lower()
        if not email:
            return None
        return User.query.filter_by(email=email).first()

    return None


def _current_user() -> User | None:
    try:
        verify_jwt_in_request(optional=True)
    except Exception:  # pragma: no cover - defensive
        return None

    identity = get_jwt_identity()
    if identity is None:
        return None

    try:
        user_id = int(identity)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None

    return User.query.get(user_id)


def _determine_entity_id(action: str, response, user: User | None) -> int | None:
    if action == "auth.login":
        return user.id if user else None

    if not getattr(response, "is_json", False):
        return None

    data = response.get_json(silent=True) or {}

    if action == "appointment.booked":
        appointment_payload = data.get("appointment") or {}
        return appointment_payload.get("id")

    if action == "clinic.onboarded":
        return data.get("clinic_id")

    return None


def _default_description(action: str, user: User | None, entity_id: int | None) -> str | None:
    if action == "auth.login" and user:
        return f"User {user.email} authenticated successfully."
    if action == "appointment.booked" and entity_id:
        return f"Appointment {entity_id} booked via AI recommendation."
    if action == "clinic.onboarded" and entity_id:
        return f"Clinic {entity_id} onboarding completed."
    return None


def _hash_request(method: str, path: str, body: bytes) -> str:
    payload = f"{method}\n{path}\n".encode("utf-8") + body
    return hashlib.sha256(payload).hexdigest()


def _hash_response(response) -> str:
    body = response.get_data() or b""
    payload = f"{response.status_code}\n".encode("utf-8") + body
    return hashlib.sha256(payload).hexdigest()

