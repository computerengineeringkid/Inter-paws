"""Serverless entrypoint for deploying the Flask app on Vercel."""
from __future__ import annotations
import os

from backend.app import create_app

app = create_app(os.getenv("FLASK_ENV"))
