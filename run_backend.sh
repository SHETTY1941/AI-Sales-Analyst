#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
if [[ -x "$ROOT_DIR/venv/bin/python" ]]; then PYTHON="$ROOT_DIR/venv/bin/python";
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then PYTHON="$ROOT_DIR/.venv/bin/python";
else echo "Run ./start.sh once to create the virtual environment and install dependencies."; exit 1; fi
exec "$PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
