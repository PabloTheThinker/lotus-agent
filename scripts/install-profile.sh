#!/usr/bin/env bash
# Install L.O.T.U.S. as a Hermes profile from this repo (local clone).
# Prefer ./install.sh (same steps + Hermes-style entry). Kept for CONTRIBUTING / CI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT/install.sh" "$@"
