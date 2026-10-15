#!/usr/bin/env bash
# One-command demo (macOS / Linux / Git Bash): venv -> dependencies -> pipeline -> API + dashboard.
#   ./run_demo.sh                  full run (about 3 minutes for the pipeline)
#   ./run_demo.sh --skip-pipeline  reuse existing data/ outputs
#   PORT=8001 ./run_demo.sh        serve on another port
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"

if [ ! -d .venv ]; then
  echo "Creating virtual environment in .venv"
  python3 -m venv .venv 2>/dev/null || python -m venv .venv
fi
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=.venv/Scripts/python; fi

echo "Installing dependencies"
"$PY" -m pip install -q -r requirements.txt

if [ "${1:-}" != "--skip-pipeline" ]; then
  for step in generate_data build_features train_model detect cross_seed validate; do
    echo; echo "== $step =="
    "$PY" "backend/pipeline/$step.py"
  done
fi

URL="http://127.0.0.1:$PORT"
echo; echo "Starting API on $URL (Ctrl+C to stop)"
"$PY" -m uvicorn backend.app.main:app --port "$PORT" &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT INT TERM

for _ in $(seq 1 90); do
  if curl -fs "$URL/health" >/dev/null 2>&1; then break; fi
  kill -0 "$SERVER" 2>/dev/null || { echo "The API exited during startup."; exit 1; }
  sleep 1
done
curl -fs "$URL/health" >/dev/null || { echo "The API did not become ready within 90 seconds."; exit 1; }

echo "Dashboard: $URL/app/    API docs: $URL/docs"
(command -v open >/dev/null && open "$URL/app/") || (command -v xdg-open >/dev/null && xdg-open "$URL/app/") || true
wait "$SERVER"
