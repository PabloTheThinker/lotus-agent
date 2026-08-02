#!/usr/bin/env bash
# Install L.O.T.U.S. as a Hermes profile distribution from this repo.
# Stages a clean copy so local venvs / egg-info / symlinks never break install.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v hermes >/dev/null 2>&1; then
  echo "Hermes Agent not found on PATH. Install from https://hermes-agent.nousresearch.com/"
  exit 1
fi

STAGE="$(mktemp -d /tmp/lotus-dist.XXXXXX)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

echo "Staging clean distribution from: $ROOT"
rsync -a \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'harness/.venv/' \
  --exclude '**/__pycache__/' \
  --exclude '**/*.egg-info/' \
  --exclude '.pytest_cache/' \
  --exclude 'node_modules/' \
  "$ROOT/" "$STAGE/"

echo "Installing L.O.T.U.S. profile..."
hermes profile install "$STAGE" --alias --name lotus -y --force

PROFILE_HOME="$HOME/.hermes/profiles/lotus"

# Hermes loads skins/themes from HERMES_HOME (profile dir) — keep copies current
mkdir -p "$PROFILE_HOME/skins" "$PROFILE_HOME/dashboard-themes"
cp -f "$ROOT/skins/lotus.yaml" "$PROFILE_HOME/skins/lotus.yaml"
cp -f "$ROOT/dashboard-themes/lotus.yaml" "$PROFILE_HOME/dashboard-themes/lotus.yaml"

# Install harness into the active Python so plugins import reliably
PYTHON_BIN="$(command -v python3)"
if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
  PYTHON_BIN="$HOME/.hermes/hermes-agent/venv/bin/python"
elif [[ -x "$HOME/.hermes/hermes-agent/.venv/bin/python" ]]; then
  PYTHON_BIN="$HOME/.hermes/hermes-agent/.venv/bin/python"
fi
echo "Installing lotus-harness into: $PYTHON_BIN"
"$PYTHON_BIN" -m pip install -e "$PROFILE_HOME/harness" --quiet \
  || "$PYTHON_BIN" -m pip install -e "$ROOT/harness" --quiet \
  || echo "  (pip install harness skipped — plugins will use path bootstrap)"

# Apply Lotus skin for CLI/TUI (config.yaml already sets display.skin)
hermes -p lotus skin use lotus >/dev/null 2>&1 || true

# Seed .env from template if missing (never overwrite secrets)
if [[ ! -f "$PROFILE_HOME/.env" && -f "$ROOT/.env.template" ]]; then
  cp "$ROOT/.env.template" "$PROFILE_HOME/.env"
  echo "Created $PROFILE_HOME/.env from template (Lotus UI / gateway helpers)."
  echo "Connect your AI model with Hermes:  lotus setup"
fi

# Ensure API_SERVER_KEY exists when blank (do not rotate existing secrets)
if [[ -f "$PROFILE_HOME/.env" ]] && grep -qE '^API_SERVER_KEY=\s*$' "$PROFILE_HOME/.env"; then
  KEY="$(openssl rand -hex 24 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(24))')"
  if [[ "$(uname)" == Darwin ]]; then
    sed -i '' "s/^API_SERVER_KEY=\s*$/API_SERVER_KEY=$KEY/" "$PROFILE_HOME/.env"
  else
    sed -i "s/^API_SERVER_KEY=\s*$/API_SERVER_KEY=$KEY/" "$PROFILE_HOME/.env"
  fi
  echo "Generated API_SERVER_KEY in profile .env"
fi

# Stable UI session secret across restarts (do not rotate if already set)
if [[ -f "$PROFILE_HOME/.env" ]]; then
  if ! grep -qE '^LOTUS_UI_SESSION_SECRET=' "$PROFILE_HOME/.env"; then
    SECRET="$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "LOTUS_UI_SESSION_SECRET=$SECRET" >> "$PROFILE_HOME/.env"
    echo "Generated LOTUS_UI_SESSION_SECRET in profile .env"
  elif grep -qE '^LOTUS_UI_SESSION_SECRET=\s*$' "$PROFILE_HOME/.env"; then
    SECRET="$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
    if [[ "$(uname)" == Darwin ]]; then
      sed -i '' "s/^LOTUS_UI_SESSION_SECRET=\s*$/LOTUS_UI_SESSION_SECRET=$SECRET/" "$PROFILE_HOME/.env"
    else
      sed -i "s/^LOTUS_UI_SESSION_SECRET=\s*$/LOTUS_UI_SESSION_SECRET=$SECRET/" "$PROFILE_HOME/.env"
    fi
    echo "Generated LOTUS_UI_SESSION_SECRET in profile .env"
  fi
fi

echo
echo "Installed at: $PROFILE_HOME"
echo "Alias:        lotus → hermes -p lotus"
echo
# Ensure research pulse is scheduled once (skip if any job named lotus-research-pulse exists)
if ! hermes -p lotus cron list 2>/dev/null | grep -qi 'Name:[[:space:]]*lotus-research-pulse'; then
  echo "Scheduling lotus-research-pulse (every 6h)..."
  PROMPT="$(python3 -c "import json; print(json.load(open('$ROOT/cron/lotus-research-pulse.json'))['prompt'])")"
  hermes -p lotus cron create "every 6h" "$PROMPT" \
    --name "lotus-research-pulse" \
    --deliver local \
    --skill lotus-realtime-core \
    --skill lotus-research-core \
    --skill lotus-medical-plain-language \
    --skill lotus-adaptive-language \
    --skill lotus-continuity \
    >/dev/null || echo "  (cron create skipped — run manually after setup)"
else
  echo "lotus-research-pulse already scheduled — leaving existing cron job in place"
fi
echo
echo "Next (Hermes setup is how you connect the AI model):"
echo "  lotus setup                         # Hermes wizard — model + provider (required)"
echo "  # or:  ./scripts/lotus-setup.sh"
echo "  # or:  lotus setup model            # model section only"
echo "  ./scripts/lotus-doctor.sh           # verify model / gateway / harness"
echo "  ./scripts/lotus-cli.sh              # Lotus-skinned CLI chat"
echo "  ./scripts/lotus-gateway.sh start    # gateway + OpenAI API for frontend"
echo "  ./scripts/lotus-frontend.sh         # Lotus web UI → http://127.0.0.1:8787"
