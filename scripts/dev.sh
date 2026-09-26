#!/usr/bin/env bash
# One command to run the playground locally: checks tooling, installs what is missing, seeds the demo tenant on first run,
# starts the API on 8000 and the web app on 3000, and opens the browser.
#   scripts/dev.sh            start (seeds the demo tenant if the database is empty)
#   scripts/dev.sh --reseed   rebuild the demo tenant first
#   scripts/dev.sh --offline  run with the fake provider (no keys, no cost)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RESEED=0; OFFLINE=0
for arg in "$@"; do case "$arg" in --reseed) RESEED=1 ;; --offline) OFFLINE=1 ;; esac; done

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1 ($2)" >&2; exit 1; }; }
need node "https://nodejs.org, version 22 or later"
need uv "https://docs.astral.sh/uv/  (curl -LsSf https://astral.sh/uv/install.sh | sh)"

if [[ ! -f .env ]]; then cp .env.example .env; echo "created .env from .env.example; add provider keys there for live models"; fi
[[ -d node_modules ]] || npm install
[[ -d apps/api/.venv ]] || (cd apps/api && uv sync)
[[ -d apps/web/public/jupyterlite/lab ]] || npm run build:jupyterlite

if [[ $RESEED -eq 1 ]]; then
  (cd apps/api && ./.venv/bin/python scripts/seed_demo.py --reset)
else
  (cd apps/api && ./.venv/bin/python scripts/seed_demo.py) || true
fi

export PLAYGROUND_FAKE_LLM=$([[ $OFFLINE -eq 1 ]] && echo true || echo false)
export ALLOW_DEV_LOGIN=true
export PLAYGROUND_API_URL=http://localhost:8000

mkdir -p .run
(cd apps/api && exec ./.venv/bin/python -m uvicorn app.main:app --port 8000) > .run/api.log 2>&1 &
API_PID=$!
(cd apps/web && exec npx next dev --port 3000) > .run/web.log 2>&1 &
WEB_PID=$!
trap 'kill $API_PID $WEB_PID 2>/dev/null || true' EXIT INT TERM

for _ in $(seq 1 60); do curl -fsS http://localhost:8000/health >/dev/null 2>&1 && break; sleep 1; done
for _ in $(seq 1 90); do curl -fsS http://localhost:3000/api/health >/dev/null 2>&1 && break; sleep 1; done
echo
echo "Enterprise AI Playground is running"
echo "  web   http://localhost:3000   (sign in as Satya Bonda, password: playground)"
echo "  api   http://localhost:8000/docs"
echo "  logs  .run/api.log  .run/web.log"
echo "  mode  $([[ $OFFLINE -eq 1 ]] && echo 'offline fake provider' || echo 'live providers from .env')"
echo "Press Ctrl+C to stop both."
command -v open >/dev/null 2>&1 && open http://localhost:3000 || true
wait
