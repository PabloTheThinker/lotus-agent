#!/usr/bin/env bash
# One-shot L.O.T.U.S. ask via Cursor CLI (default: Grok 4.5).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HERMES_HOME="${HERMES_HOME:-$HOME/.hermes/profiles/lotus}"
export LOTUS_BACKEND=cursor
export LOTUS_CURSOR_MODEL="${LOTUS_CURSOR_MODEL:-cursor-grok-4.5-high-fast}"
export PYTHONPATH="${ROOT}/harness:${PYTHONPATH:-}"

MSG="${*:-I feel a little heavy today. Be with me briefly.}"
if command -v lotus-harness >/dev/null 2>&1; then
  exec lotus-harness ask --backend cursor --model "$LOTUS_CURSOR_MODEL" "$MSG"
fi
exec python3 -m lotus.cli ask --backend cursor --model "$LOTUS_CURSOR_MODEL" "$MSG"
