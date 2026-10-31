#!/usr/bin/env bash
# One-command launcher for Linux/macOS. Safe to run from any working directory.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

info() { printf '\n\033[1;36m[AI Sales Analyst]\033[0m %s\n' "$*"; }
warn() { printf '\n\033[1;33m[Action needed]\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31m[Startup failed]\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "Python 3 is required. Install Python 3.10 or newer."
command -v node >/dev/null 2>&1 || fail "Node.js is required. Install Node.js 18 or newer."
command -v npm >/dev/null 2>&1 || fail "npm is required. Install Node.js with npm."

# Reuse an existing project virtual environment when present.
if [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/venv/bin/python"
elif [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
else
  info "Creating Python virtual environment..."
  python3 -m venv "$ROOT_DIR/.venv" || fail "Could not create .venv. On Ubuntu/Debian install python3-venv first."
  PYTHON="$ROOT_DIR/.venv/bin/python"
fi

info "Installing/checking Python dependencies..."
"$PYTHON" -m pip install -q -r "$ROOT_DIR/requirements.txt" || fail "Python dependency installation failed. Check your internet connection and requirements.txt."

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  warn "Created project-root .env from .env.example. Add your Gemini and/or Groq key to .env, then run ./start.sh again."
fi

# Frontend only needs the backend URL; provider secrets must never be copied into Vite.
if [[ ! -f "$ROOT_DIR/frontend-react/.env" ]]; then
  cp "$ROOT_DIR/frontend-react/.env.example" "$ROOT_DIR/frontend-react/.env"
fi

KEY_STATE=$("$PYTHON" - <<'PY'
from pathlib import Path
from dotenv import dotenv_values
root = Path(__file__).resolve().parent
values = dotenv_values(root / ".env")
def valid(name):
    value = (values.get(name) or "").strip().strip('"').strip("'")
    return bool(value) and not value.lower().startswith(("your_", "replace_", "paste_")) and not value.startswith("<")
print("yes" if valid("GEMINI_API_KEY") or valid("GROQ_API_KEY") else "no")
PY
)
if [[ "$KEY_STATE" != "yes" ]]; then
  warn "No real AI key found in $ROOT_DIR/.env. Add GEMINI_API_KEY and/or GROQ_API_KEY. Dashboard works, but AI questions will not run until a key is added."
fi

if [[ ! -x "$ROOT_DIR/frontend-react/node_modules/.bin/vite" ]] || ! (cd "$ROOT_DIR/frontend-react" && npm ls --depth=0 >/dev/null 2>&1); then
  info "Installing/checking React dependencies..."
  (cd "$ROOT_DIR/frontend-react" && npm install) || fail "npm install failed. Check your internet connection and Node.js version."
fi

BACKEND_PID=""
STARTED_BACKEND="no"
if "$PYTHON" - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1).read()
PY
then
  info "Backend already responds at http://127.0.0.1:8000; reusing it."
else
  info "Starting FastAPI backend from the correct project root..."
  (cd "$ROOT_DIR" && exec "$PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000) > "$ROOT_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
  STARTED_BACKEND="yes"
  for attempt in $(seq 1 40); do
    if "$PYTHON" - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1).read()
PY
    then break; fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      cat "$ROOT_DIR/backend.log" >&2
      fail "Backend exited during startup. See backend.log above."
    fi
    sleep 1
  done
  "$PYTHON" - <<'PY' >/dev/null 2>&1 || { cat "$ROOT_DIR/backend.log" >&2; fail "Backend did not become healthy within 40 seconds. See backend.log."; }
import urllib.request
urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2).read()
PY
fi

cleanup() {
  if [[ "$STARTED_BACKEND" == "yes" && -n "$BACKEND_PID" ]]; then
    info "Stopping backend process..."
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

info "Backend:  http://127.0.0.1:8000"
info "API docs: http://127.0.0.1:8000/docs"
info "AI status: http://127.0.0.1:8000/ai-status"
info "Frontend: http://localhost:5173"
info "Press Ctrl+C to stop the application."
(cd "$ROOT_DIR/frontend-react" && npm run dev -- --host 127.0.0.1)
