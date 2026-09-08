#!/usr/bin/env bash
# Stops the ToyBox backend and frontend started by start.sh on macOS/Linux.
# Run from anywhere:
#
#     ./scripts/stop.sh
#
# Kills by tracked PID first, then falls back to whatever is listening on
# ports 8000/5173 in case the PID file is stale, missing, or npm left an
# orphaned child (vite) behind when its parent was killed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

stop_by_pid_file() {
  local pid_file="$1"
  local label="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "Stopping $label (PID $pid)..."
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi
}

stop_by_port() {
  local port="$1"
  local label="$2"
  local pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Stopping $label on port $port (PID(s) $pids)..."
    kill -9 $pids 2>/dev/null || true
  fi
}

stop_by_pid_file "$BACKEND_PID_FILE" "backend"
stop_by_pid_file "$FRONTEND_PID_FILE" "frontend"

# Fallback in case a process was started outside these scripts, or an
# orphaned child survived the PID-based kill.
stop_by_port 8000 "backend"
stop_by_port 5173 "frontend"

echo "ToyBox stopped."
