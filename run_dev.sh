#!/usr/bin/env bash
set -euo pipefail

# Check for virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# Activate virtual environment
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

export FLASK_APP="backend.app.serverless:app"
export FLASK_ENV="development"

echo "Running database migrations..."
flask db upgrade

echo "Starting server on http://localhost:5000/booking"
flask run --port 5000
