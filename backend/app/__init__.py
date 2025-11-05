"""Application factory for the Inter-Paws backend."""
from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from backend.config import get_config
from backend.app.middleware import register_audit_middleware
from backend.app.models import User
from backend.extensions import bcrypt, db, jwt, migrate


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    config_cls = get_config(config_name or app.config.get("ENV"))
    app.config.from_object(config_cls)

    register_extensions(app)
    register_blueprints(app)

    if app.config.get("DEBUG"):
        _seed_dev_admin(app)

    register_audit_middleware(app)

    CORS(app)
    return app


def register_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)


def register_blueprints(app: Flask) -> None:
    """Register application blueprints."""

    from backend.app.api import api_bp
    from backend.app.frontend import frontend_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(frontend_bp)


def _seed_dev_admin(app: Flask) -> None:
    """Seed a default admin user for development."""
    with app.app_context():
        existing_admin = User.query.filter_by(email="admin@example.com").first()
        if not existing_admin:
            password_hash = bcrypt.generate_password_hash("admin").decode("utf-8")
            dev_admin = User(
                email="admin@example.com",
                password_hash=password_hash,
                role="admin",
                full_name="Dev Admin",
            )
            db.session.add(dev_admin)
            db.session.commit()
