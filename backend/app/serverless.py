"""Serverless entrypoint for deploying the Flask app on Vercel."""
from __future__ import annotations

from backend.app import create_app

app = create_app("production")
