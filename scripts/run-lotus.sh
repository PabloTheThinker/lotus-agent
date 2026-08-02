#!/usr/bin/env bash
# Default: Lotus-branded CLI chat. Pass "gateway" | "ui" | "frontend" for other surfaces.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "${1:-chat}" in
  chat|"")
    shift || true
    exec "$ROOT/scripts/lotus-cli.sh" chat "$@"
    ;;
  setup)
    shift || true
    exec "$ROOT/scripts/lotus-setup.sh" "$@"
    ;;
  gateway)
    shift || true
    exec "$ROOT/scripts/lotus-gateway.sh" "${1:-start}" "${@:2}"
    ;;
  ui|frontend|web)
    shift || true
    exec "$ROOT/scripts/lotus-frontend.sh" "$@"
    ;;
  doctor)
    shift || true
    exec "$ROOT/scripts/lotus-doctor.sh" "$@"
    ;;
  cli)
    shift || true
    exec "$ROOT/scripts/lotus-cli.sh" "$@"
    ;;
  *)
    exec "$ROOT/scripts/lotus-cli.sh" "$@"
    ;;
esac
