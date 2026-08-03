#!/usr/bin/env bash
# Connect an AI model / provider via the Hermes setup wizard (canonical path).
# Usage:
#   ./scripts/lotus-setup.sh           # full Hermes setup
#   ./scripts/lotus-setup.sh model     # model/provider section only
#   ./scripts/lotus-setup.sh --portal  # Nous Portal one-shot
set -euo pipefail

if command -v lotus >/dev/null 2>&1; then
  exec lotus setup "$@"
elif command -v hermes >/dev/null 2>&1; then
  exec hermes -p lotus setup "$@"
else
  echo "Hermes / lotus not found. Run ./install.sh first." >&2
  exit 1
fi
