"""Configuration objects for the Interpaws backend."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Type

basedir = Path(__file__).resolve().parent


class Config:
    """Base configuration shared by all environments."""

    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
    BCRYPT_LOG_ROUNDS: int = int(os.getenv("BCRYPT_LOG_ROUNDS", "13"))
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    LLM_MAX_SUGGESTIONS: int = int(os.getenv("LLM_MAX_SUGGESTIONS", "5"))

    @classmethod
    def as_dict(cls) -> Dict[str, Any]:
        """Expose configuration values for debugging and introspection."""

        return {key: getattr(cls, key) for key in dir(cls) if key.isupper()}


class DevelopmentConfig(Config):
    """Configuration suitable for local development."""

    _db_path = basedir / "dev.db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DEV_DATABASE_URL", f"sqlite:///{_db_path}")
    DEBUG = True


class ProductionConfig(Config):
    """Configuration tailored for production deployments."""

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///inter_paws.db")
    DEBUG = False


CONFIG_MAP: Dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None) -> Type[Config]:
    """Retrieve the configuration class matching the supplied name."""

    if not name:
        return DevelopmentConfig
    return CONFIG_MAP.get(name.lower(), DevelopmentConfig)
