"""Authentication endpoints."""
from __future__ import annotations

from datetime import datetime
from http import HTTPStatus

from flask import jsonify, request
from flask.typing import ResponseReturnValue
from flask_jwt_extended import create_access_token

from backend.app.models import User
from backend.extensions import bcrypt, db

from . import api_bp


@api_bp.post("/auth/register")
def register() -> ResponseReturnValue:
    """Register a new user account."""

    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password")
    name = (payload.get("name") or "").strip()
    role = (payload.get("role") or "staff").strip() or "staff"
    clinic_id = payload.get("clinic_id")

    if not email or not password or not name:
        return (
            jsonify(message="Email, password, and name are required."),
            HTTPStatus.BAD_REQUEST,
        )

    if User.query.filter_by(email=email).first():
        return (
            jsonify(message="An account with this email already exists."),
            HTTPStatus.CONFLICT,
        )

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(
        email=email,
        password_hash=password_hash,
        full_name=name,
        role=role,
        clinic_id=clinic_id,
    )

    db.session.add(user)
    db.session.commit()

    return jsonify(message="Registration successful."), HTTPStatus.CREATED


@api_bp.post("/auth/login")
def login() -> ResponseReturnValue:
    """Authenticate a user and return an access token."""

    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        return (
            jsonify(message="Email and password are required."),
            HTTPStatus.BAD_REQUEST,
        )

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return (
            jsonify(message="Invalid email or password."),
            HTTPStatus.UNAUTHORIZED,
        )

    user.last_login_at = datetime.utcnow()
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    return jsonify(access_token=access_token), HTTPStatus.OK
