#!/usr/bin/env bash
# Verify L.O.T.U.S. profile, harness, keys, and gateway readiness.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes/profiles/lotus}"
export LOTUS_REPO="${LOTUS_REPO:-$ROOT}"

if command -v lotus-harness >/dev/null 2>&1; then
  exec lotus-harness doctor
fi

# Prefer Hermes venv python if present
PY=python3
if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
  PY="$HOME/.hermes/hermes-agent/venv/bin/python"
elif [[ -x "$HOME/.hermes/hermes-agent/.venv/bin/python" ]]; then
  PY="$HOME/.hermes/hermes-agent/.venv/bin/python"
fi

export PYTHONPATH="${ROOT}/harness:${PYTHONPATH:-}"
exec "$PY" -m lotus.cli doctor
