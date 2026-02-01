#!/usr/bin/env bash
# Setup: create venv (if missing), install deps, then run the app with uvicorn.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> Creating virtual environment in $VENV_DIR"
  "$PYTHON" -m venv "$VENV_DIR"
else
  echo "==> Using existing virtual environment $VENV_DIR"
fi

echo "==> Installing dependencies"
"$VENV_DIR/bin/pip" install -q -r requirements.txt

echo "==> Starting uvicorn"
exec "$VENV_DIR/bin/uvicorn" app.main:app --reload --reload-exclude ".venv" --host 0.0.0.0 --port 8000
