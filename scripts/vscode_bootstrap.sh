#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] $PYTHON_BIN not found. Install Python 3.10+ first."
  exit 1
fi

echo "[1/4] Creating virtual environment at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[2/4] Upgrading pip tooling"
python -m pip install --upgrade pip setuptools wheel

echo "[3/4] Installing project dependencies"
pip install -r backend/requirements.txt

echo "[4/4] Starting Offline Proctored Exam app on http://localhost:${PORT}"
exec uvicorn backend.app.main:app --host "$HOST" --port "$PORT" --reload
