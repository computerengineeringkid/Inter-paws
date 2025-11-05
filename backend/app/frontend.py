"""Routes for client-facing booking experience."""
from __future__ import annotations

from flask import Blueprint, render_template

frontend_bp = Blueprint("frontend", __name__)


@frontend_bp.get("/booking")
@frontend_bp.get("/client/<path:path>")
def booking_form(path: str | None = None) -> str:
    """Render the client booking interface."""

    return render_template("client/booking.html")


@frontend_bp.get("/onboarding")
@frontend_bp.get("/clinic/<path:path>")
def clinic_onboarding_form(path: str | None = None) -> str:
    """Render the clinic onboarding wizard."""

    return render_template("clinic/onboarding.html")
