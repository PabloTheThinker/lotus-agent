#!/usr/bin/env bash
# Start / manage the Hermes gateway under the L.O.T.U.S. profile.
# Relays (Telegram/Discord) + OpenAI-compatible API for the Lotus frontend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_ENV="${HERMES_HOME:-$HOME/.hermes/profiles/lotus}/.env"

lotus_cmd() {
  if command -v lotus >/dev/null 2>&1; then
    lotus "$@"
  elif command -v hermes >/dev/null 2>&1; then
    hermes -p lotus "$@"
  else
    echo "Hermes / lotus not found. Run ./install.sh first." >&2
    exit 1
  fi
}

# Soft-load profile .env so API_SERVER_* is available for the UI proxy
if [[ -f "$PROFILE_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$PROFILE_ENV"
  set +a
fi

export GATEWAY_RELAY_DISPLAY_NAME="${GATEWAY_RELAY_DISPLAY_NAME:-L.O.T.U.S.}"

# Ensure Lotus skin is active for CLI/TUI surfaces that share this profile
lotus_cmd skin use lotus >/dev/null 2>&1 || true

ACTION="${1:-start}"
shift || true

case "$ACTION" in
  start|run)
    echo "Starting L.O.T.U.S. gateway (Hermes foundation)…"
    echo "  Display name: $GATEWAY_RELAY_DISPLAY_NAME"
    echo "  API (if enabled): http://127.0.0.1:${API_SERVER_PORT:-8642}/v1"
    echo "  Frontend:     ./scripts/lotus-frontend.sh"
    lotus_cmd gateway start "$@"
    ;;
  stop|status|restart|logs)
    lotus_cmd gateway "$ACTION" "$@"
    ;;
  *)
    lotus_cmd gateway "$ACTION" "$@"
    ;;
esac
