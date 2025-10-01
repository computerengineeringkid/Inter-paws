"""API blueprint registration."""
from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Import endpoints to ensure they are registered with the blueprint.
from . import auth  # noqa: E402,F401
from .clinic import clinic_bp  # noqa: E402,F401
from .scheduler import scheduler_bp  # noqa: E402,F401

api_bp.register_blueprint(clinic_bp, url_prefix="/clinic")
api_bp.register_blueprint(scheduler_bp, url_prefix="/schedule")
