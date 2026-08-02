#!/usr/bin/env bash
# Lotus-branded CLI entry: skin + chat (or passthrough hermes/lotus subcommands).
set -euo pipefail

lotus_cmd() {
  if command -v lotus >/dev/null 2>&1; then
    lotus "$@"
  elif command -v hermes >/dev/null 2>&1; then
    hermes -p lotus "$@"
  else
    echo "L.O.T.U.S. profile not installed. Run ./scripts/install-profile.sh first." >&2
    exit 1
  fi
}

PROFILE_ENV="${HERMES_HOME:-$HOME/.hermes/profiles/lotus}/.env"
if [[ -f "$PROFILE_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$PROFILE_ENV"
  set +a
fi

export GATEWAY_RELAY_DISPLAY_NAME="${GATEWAY_RELAY_DISPLAY_NAME:-L.O.T.U.S.}"

lotus_cmd skin use lotus >/dev/null 2>&1 || true

if [[ $# -eq 0 ]]; then
  lotus_cmd chat
  exit $?
fi

# Preserve Hermes setup as the model-connection path
if [[ "$1" == "setup" ]]; then
  shift
  lotus_cmd setup "$@"
  exit $?
fi

lotus_cmd "$@"
