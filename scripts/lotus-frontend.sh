#!/usr/bin/env bash
# Serve the L.O.T.U.S. web UI and proxy chat to the Hermes gateway API.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_HOME="${HERMES_HOME:-$HOME/.hermes/profiles/lotus}"
PROFILE_ENV="$PROFILE_HOME/.env"

if [[ -f "$PROFILE_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$PROFILE_ENV"
  set +a
fi

export LOTUS_API_BASE="${LOTUS_API_BASE:-http://127.0.0.1:${API_SERVER_PORT:-8642}/v1}"
export LOTUS_UI_HOST="${LOTUS_UI_HOST:-127.0.0.1}"
export LOTUS_UI_PORT="${LOTUS_UI_PORT:-8787}"
export API_SERVER_KEY="${API_SERVER_KEY:-${LOTUS_API_KEY:-}}"

echo "L.O.T.U.S. frontend"
echo "  UI:      http://${LOTUS_UI_HOST}:${LOTUS_UI_PORT}"
echo "  Gateway: ${LOTUS_API_BASE}"
echo "  Tip:     lotus gateway start   # if API is down"
echo

exec python3 "$ROOT/frontend/server.py"
