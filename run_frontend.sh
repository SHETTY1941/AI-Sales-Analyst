#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR/frontend-react"
[[ -f .env ]] || cp .env.example .env
[[ -x node_modules/.bin/vite ]] || npm install
exec npm run dev -- --host 127.0.0.1
