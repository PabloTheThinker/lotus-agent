#!/usr/bin/env bash
# Compatibility shim — prefer the installed `lotus` CLI (bin/lotus).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$HOME/.local/bin/lotus" ]]; then
  exec "$HOME/.local/bin/lotus" "$@"
fi
if [[ -x "$ROOT/bin/lotus" ]]; then
  exec "$ROOT/bin/lotus" "$@"
fi
if command -v lotus >/dev/null 2>&1; then
  exec lotus "$@"
fi

echo "L.O.T.U.S. CLI not found. Install with:" >&2
echo "  ./install.sh" >&2
echo "Or:" >&2
echo "  curl -fsSL https://raw.githubusercontent.com/PabloTheThinker/lotus-agent/main/install.sh | bash" >&2
exit 1
