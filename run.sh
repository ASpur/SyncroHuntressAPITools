#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

VENV_DIR=".venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Creating virtual environment..."

  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$VENV_DIR"
  elif command -v python >/dev/null 2>&1; then
    python -m venv "$VENV_DIR"
  else
    echo "Python was not found. Install Python 3 and try again." >&2
    exit 1
  fi

  echo "Installing dependencies..."
  "$VENV_PYTHON" -m pip install -r requirements.txt
fi

echo "Starting Syncro Huntress Comparison Tool..."
exec "$VENV_PYTHON" gui.py "$@"
