#!/usr/bin/env bash
# ============================================================================
# L.O.T.U.S. Installer
# ============================================================================
# Hermes-style one-liner for the Lotus profile distribution.
# Requires Hermes Agent on PATH (same prerequisite as any Hermes profile).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/PabloTheThinker/lotus-agent/main/install.sh | bash
#
# From a local clone:
#   ./install.sh
#   ./install.sh --force
#
# Options:
#   --force          Overwrite existing lotus profile (user data preserved by Hermes)
#   --skip-setup     Don't hint / offer setup (always non-interactive for curl)
#   --from-github    Force install from GitHub even when run inside a clone
#   --source URL     Override distribution source (git URL or local dir)
# ============================================================================

set -euo pipefail

if [[ -n "${PYTHONPATH:-}" ]]; then
  echo "⚠ Ignoring inherited PYTHONPATH during install"
  unset PYTHONPATH
fi

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
NC=$'\033[0m'

LOTUS_GITHUB_SLUG="${LOTUS_GITHUB_SLUG:-github.com/PabloTheThinker/lotus-agent}"
LOTUS_GITHUB_HTTPS="${LOTUS_GITHUB_HTTPS:-https://github.com/PabloTheThinker/lotus-agent.git}"
PROFILE_NAME="${LOTUS_PROFILE:-lotus}"
PROFILE_HOME="${HOME}/.hermes/profiles/${PROFILE_NAME}"

FORCE=false
FROM_GITHUB=false
SOURCE_OVERRIDE=""
SKIP_SETUP_HINT=false

if [[ -t 0 ]]; then
  IS_INTERACTIVE=true
else
  IS_INTERACTIVE=false
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force|-f)
      FORCE=true
      shift
      ;;
    --from-github)
      FROM_GITHUB=true
      shift
      ;;
    --source)
      SOURCE_OVERRIDE="$2"
      shift 2
      ;;
    --skip-setup)
      SKIP_SETUP_HINT=true
      shift
      ;;
    -h|--help)
      sed -n '2,20p' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

echo
echo "${BOLD}${CYAN}L.O.T.U.S.${NC} — Light Over The Unseen Shadows"
echo "Hermes Agent profile installer"
echo

# Resolve script location when not piped through curl
INSTALLER_PATH="${BASH_SOURCE[0]:-}"
LOCAL_ROOT=""
if [[ -n "$INSTALLER_PATH" && -f "$INSTALLER_PATH" ]]; then
  _dir="$(cd "$(dirname "$INSTALLER_PATH")" && pwd)"
  if [[ -f "$_dir/distribution.yaml" && -f "$_dir/SOUL.md" ]]; then
    LOCAL_ROOT="$_dir"
  fi
fi

die() { echo "${RED}✗${NC} $*" >&2; exit 1; }
ok()  { echo "${GREEN}✓${NC} $*"; }

# ── prerequisites ─────────────────────────────────────────────────────────
if ! command -v hermes >/dev/null 2>&1; then
  echo "${RED}Hermes Agent not found on PATH.${NC}"
  echo
  echo "Install Hermes first (required — Lotus runs on Hermes):"
  echo "  ${CYAN}curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash${NC}"
  echo
  echo "Then re-run this installer."
  exit 1
fi
ok "Hermes found: $(command -v hermes)"

if ! command -v git >/dev/null 2>&1; then
  die "git is required (Hermes profile install uses git)"
fi
ok "git found"

if ! command -v rsync >/dev/null 2>&1 && [[ -n "$LOCAL_ROOT" && "$FROM_GITHUB" != true && -z "$SOURCE_OVERRIDE" ]]; then
  echo "${YELLOW}⚠${NC} rsync not found — local staging uses cp fallback"
fi

# Soft version check (Hermes ≥0.19)
if hermes --version >/dev/null 2>&1; then
  ver_line="$(hermes --version 2>/dev/null | head -1 || true)"
  echo "  $ver_line"
fi

# ── choose source ─────────────────────────────────────────────────────────
SOURCE=""
USE_LOCAL_STAGE=false

if [[ -n "$SOURCE_OVERRIDE" ]]; then
  SOURCE="$SOURCE_OVERRIDE"
elif [[ "$FROM_GITHUB" == true ]]; then
  SOURCE="$LOTUS_GITHUB_SLUG"
elif [[ -n "$LOCAL_ROOT" ]]; then
  USE_LOCAL_STAGE=true
  SOURCE="$LOCAL_ROOT"
else
  SOURCE="$LOTUS_GITHUB_SLUG"
fi

echo
echo "Source:  ${CYAN}${SOURCE}${NC}"
echo "Profile: ${CYAN}${PROFILE_HOME}${NC}"
echo

# ── install distribution ──────────────────────────────────────────────────
STAGE=""
cleanup() {
  if [[ -n "$STAGE" && -d "$STAGE" ]]; then
    rm -rf "$STAGE"
  fi
}
trap cleanup EXIT

INSTALL_ARGS=(--alias --name "$PROFILE_NAME" -y)
if [[ "$FORCE" == true ]]; then
  INSTALL_ARGS+=(--force)
elif [[ -d "$PROFILE_HOME" ]]; then
  echo "${YELLOW}Profile already exists.${NC} Re-installing with --force (memories/sessions kept)."
  INSTALL_ARGS+=(--force)
fi

if [[ "$USE_LOCAL_STAGE" == true ]]; then
  STAGE="$(mktemp -d /tmp/lotus-dist.XXXXXX)"
  echo "Staging clean distribution from local clone…"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.git/' \
      --exclude '.venv/' \
      --exclude 'harness/.venv/' \
      --exclude '**/__pycache__/' \
      --exclude '**/*.egg-info/' \
      --exclude '.pytest_cache/' \
      --exclude 'node_modules/' \
      --exclude 'LIVE_TRANSCRIPT.md' \
      --exclude 'harness/tests/artifacts/' \
      "$LOCAL_ROOT/" "$STAGE/"
  else
    cp -a "$LOCAL_ROOT/." "$STAGE/"
    rm -rf "$STAGE/.git" "$STAGE/.venv" "$STAGE/harness/.venv" \
      "$STAGE/node_modules" "$STAGE/harness/tests/artifacts" 2>/dev/null || true
  fi
  ROOT="$LOCAL_ROOT"
  hermes profile install "$STAGE" "${INSTALL_ARGS[@]}"
else
  ROOT="$PROFILE_HOME"
  hermes profile install "$SOURCE" "${INSTALL_ARGS[@]}" \
    || hermes profile install "$LOTUS_GITHUB_HTTPS" "${INSTALL_ARGS[@]}"
fi

ok "Profile installed"

# ── post-install (CLI, harness, skin, env, cron) ───────────────────────────
LIB=""
if [[ -n "${LOCAL_ROOT:-}" && -f "$LOCAL_ROOT/scripts/lib/lotus-post-install.sh" ]]; then
  LIB="$LOCAL_ROOT/scripts/lib/lotus-post-install.sh"
elif [[ -f "$PROFILE_HOME/scripts/lib/lotus-post-install.sh" ]]; then
  LIB="$PROFILE_HOME/scripts/lib/lotus-post-install.sh"
fi

if [[ -n "$LIB" ]]; then
  # shellcheck disable=SC1090
  source "$LIB"
  # For GitHub installs, ROOT should be the profile (files already there)
  if [[ "$USE_LOCAL_STAGE" != true ]]; then
    ROOT="$PROFILE_HOME"
  fi
  lotus_run_post_install
else
  # Minimal fallback if lib missing from an old tarball
  hermes profile alias "$PROFILE_NAME" >/dev/null 2>&1 || true
  echo
  echo "Installed at: $PROFILE_HOME"
  echo "Alias:        lotus → hermes -p lotus"
  echo
  echo "Next:  lotus setup && lotus"
fi

# Ensure ~/.local/bin is preferred
if [[ -x "$HOME/.local/bin/lotus" ]]; then
  ok "lotus CLI ready"
fi

if [[ "$SKIP_SETUP_HINT" != true ]]; then
  echo "${BOLD}Connect your model (Hermes setup):${NC}"
  echo "  ${CYAN}lotus setup${NC}"
  echo
  if [[ "$IS_INTERACTIVE" == true ]]; then
    echo "Then: ${CYAN}lotus${NC}"
  fi
fi

echo "${GREEN}${BOLD}Done.${NC} Welcome to L.O.T.U.S."
echo
