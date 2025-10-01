"""Routes for client-facing booking experience."""
from __future__ import annotations

from flask import Blueprint, render_template

frontend_bp = Blueprint("frontend", __name__)


@frontend_bp.get("/booking")
def booking_form() -> str:
    """Render the client booking interface."""

    return render_template("client/booking.html")
