#!/usr/bin/env bash
# Starts the ToyBox backend (FastAPI/uvicorn) and frontend (Vite) as background
# processes on macOS/Linux. Run from anywhere:
#
#     ./scripts/start.sh
#
# Logs go to scripts/logs/, PIDs are tracked in scripts/.pids/ so stop.sh can
# find and kill the right processes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/logs"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

mkdir -p "$PID_DIR" "$LOG_DIR"

is_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

already_running() {
  local pid_file="$1"
  local label="$2"
  if [[ -f "$pid_file" ]]; then
    local existing_pid
    existing_pid="$(cat "$pid_file")"
    if is_running "$existing_pid"; then
      echo "$label is already running (PID $existing_pid). Run stop.sh first if you want to restart it."
      return 0
    fi
    rm -f "$pid_file"
  fi
  return 1
}

# --- Preflight checks --------------------------------------------------------

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "frontend/node_modules not found. Run 'npm install' inside frontend/ first, then re-run this script." >&2
  exit 1
fi

if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
  echo "Backend Python dependencies not found. Run 'pip install -r backend/requirements.txt' first, then re-run this script." >&2
  exit 1
fi

# --- Backend ------------------------------------------------------------------

if ! already_running "$BACKEND_PID_FILE" "Backend"; then
  echo "Starting backend (uvicorn) on http://localhost:8000 ..."
  (cd "$BACKEND_DIR" && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    > "$LOG_DIR/backend.log" 2> "$LOG_DIR/backend.err.log" &
    echo $! > "$BACKEND_PID_FILE")
fi

# --- Frontend -------------------------------------------------------------------

if ! already_running "$FRONTEND_PID_FILE" "Frontend"; then
  echo "Starting frontend (vite) on http://localhost:5173 ..."
  (cd "$FRONTEND_DIR" && nohup npm run dev \
    > "$LOG_DIR/frontend.log" 2> "$LOG_DIR/frontend.err.log" &
    echo $! > "$FRONTEND_PID_FILE")
fi

# --- Wait for backend health ----------------------------------------------------

echo "Waiting for backend to become healthy..."
healthy=false
for _ in $(seq 1 45); do
  if curl -fsS "http://localhost:8000/health" >/dev/null 2>&1; then
    healthy=true
    break
  fi
  sleep 1
done

if [[ "$healthy" == "true" ]]; then
  echo "Backend is healthy."
else
  echo "Backend did not report healthy within 45s. Check scripts/logs/backend.err.log" >&2
fi

echo ""
echo "ToyBox is starting up:"
echo "  Backend  : http://localhost:8000  (API docs at /docs)"
echo "  Frontend : http://localhost:5173"
echo ""
echo "Logs: scripts/logs/backend.log / frontend.log"
echo "To stop everything, run: ./scripts/stop.sh"
