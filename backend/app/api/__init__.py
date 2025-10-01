"""API blueprint registration."""
from flask import Blueprint

api_bp = Blueprint("api", __name__)

# Import endpoints to ensure they are registered with the blueprint.
from . import auth  # noqa: E402,F401
