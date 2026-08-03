#!/usr/bin/env bash
# Shared post-install steps for L.O.T.U.S. (sourced by install.sh / install-profile.sh)
# Expects: PROFILE_HOME, ROOT (optional — repo or staged tree), HERMES binary on PATH

lotus_install_cli() {
  local src=""
  if [[ -n "${ROOT:-}" && -f "$ROOT/bin/lotus" ]]; then
    src="$ROOT/bin/lotus"
  elif [[ -f "$PROFILE_HOME/bin/lotus" ]]; then
    src="$PROFILE_HOME/bin/lotus"
  else
    echo "  (lotus CLI source missing — hermes --alias wrapper left in place)" >&2
    return 0
  fi
  # Keep a copy inside the profile for updates
  mkdir -p "$PROFILE_HOME/bin"
  cp -f "$src" "$PROFILE_HOME/bin/lotus"
  chmod +x "$PROFILE_HOME/bin/lotus"

  local dest="${LOTUS_BIN_DIR:-$HOME/.local/bin}/lotus"
  mkdir -p "$(dirname "$dest")"
  cp -f "$PROFILE_HOME/bin/lotus" "$dest"
  chmod +x "$dest"
  echo "CLI:          $dest → hermes -p lotus (+ Lotus verbs)"

  case ":$PATH:" in
    *":$(dirname "$dest"):"*) ;;
    *)
      echo
      echo "Add to PATH if needed:"
      echo "  export PATH=\"$(dirname "$dest"):\$PATH\""
      ;;
  esac
}

lotus_install_skin_theme() {
  local src_root="${ROOT:-$PROFILE_HOME}"
  mkdir -p "$PROFILE_HOME/skins" "$PROFILE_HOME/dashboard-themes"
  if [[ -f "$src_root/skins/lotus.yaml" ]]; then
    cp -f "$src_root/skins/lotus.yaml" "$PROFILE_HOME/skins/lotus.yaml"
  fi
  if [[ -f "$src_root/dashboard-themes/lotus.yaml" ]]; then
    cp -f "$src_root/dashboard-themes/lotus.yaml" "$PROFILE_HOME/dashboard-themes/lotus.yaml"
  fi
  hermes -p lotus skin use lotus >/dev/null 2>&1 || true
}

lotus_install_harness() {
  local src_root="${ROOT:-$PROFILE_HOME}"
  local py
  py="$(command -v python3)"
  if [[ -x "$HOME/.hermes/hermes-agent/venv/bin/python" ]]; then
    py="$HOME/.hermes/hermes-agent/venv/bin/python"
  elif [[ -x "$HOME/.hermes/hermes-agent/.venv/bin/python" ]]; then
    py="$HOME/.hermes/hermes-agent/.venv/bin/python"
  fi
  echo "Installing lotus-harness into: $py"
  if [[ -d "$PROFILE_HOME/harness" ]]; then
    "$py" -m pip install -e "$PROFILE_HOME/harness" --quiet \
      || "$py" -m pip install -e "$src_root/harness" --quiet \
      || echo "  (pip install harness skipped — plugins will use path bootstrap)"
  elif [[ -d "$src_root/harness" ]]; then
    "$py" -m pip install -e "$src_root/harness" --quiet \
      || echo "  (pip install harness skipped — plugins will use path bootstrap)"
  fi
}

lotus_seed_env() {
  local src_root="${ROOT:-$PROFILE_HOME}"
  if [[ ! -f "$PROFILE_HOME/.env" ]]; then
    if [[ -f "$src_root/.env.template" ]]; then
      cp "$src_root/.env.template" "$PROFILE_HOME/.env"
      echo "Created $PROFILE_HOME/.env from template"
    elif [[ -f "$PROFILE_HOME/.env.EXAMPLE" ]]; then
      cp "$PROFILE_HOME/.env.EXAMPLE" "$PROFILE_HOME/.env"
      echo "Created $PROFILE_HOME/.env from .env.EXAMPLE"
    fi
  fi

  if [[ -f "$PROFILE_HOME/.env" ]] && grep -qE '^API_SERVER_KEY=\s*$' "$PROFILE_HOME/.env"; then
    local key
    key="$(openssl rand -hex 24 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(24))')"
    if [[ "$(uname)" == Darwin ]]; then
      sed -i '' "s/^API_SERVER_KEY=\s*$/API_SERVER_KEY=$key/" "$PROFILE_HOME/.env"
    else
      sed -i "s/^API_SERVER_KEY=\s*$/API_SERVER_KEY=$key/" "$PROFILE_HOME/.env"
    fi
    echo "Generated API_SERVER_KEY in profile .env"
  fi

  if [[ -f "$PROFILE_HOME/.env" ]]; then
    if ! grep -qE '^LOTUS_UI_SESSION_SECRET=' "$PROFILE_HOME/.env"; then
      local secret
      secret="$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
      echo "LOTUS_UI_SESSION_SECRET=$secret" >> "$PROFILE_HOME/.env"
      echo "Generated LOTUS_UI_SESSION_SECRET in profile .env"
    elif grep -qE '^LOTUS_UI_SESSION_SECRET=\s*$' "$PROFILE_HOME/.env"; then
      local secret
      secret="$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
      if [[ "$(uname)" == Darwin ]]; then
        sed -i '' "s/^LOTUS_UI_SESSION_SECRET=\s*$/LOTUS_UI_SESSION_SECRET=$secret/" "$PROFILE_HOME/.env"
      else
        sed -i "s/^LOTUS_UI_SESSION_SECRET=\s*$/LOTUS_UI_SESSION_SECRET=$secret/" "$PROFILE_HOME/.env"
      fi
      echo "Generated LOTUS_UI_SESSION_SECRET in profile .env"
    fi
  fi
}

lotus_schedule_research_pulse() {
  local src_root="${ROOT:-$PROFILE_HOME}"
  local cron_json="$src_root/cron/lotus-research-pulse.json"
  [[ -f "$cron_json" ]] || cron_json="$PROFILE_HOME/cron/lotus-research-pulse.json"
  [[ -f "$cron_json" ]] || return 0

  if hermes -p lotus cron list 2>/dev/null | grep -qi 'Name:[[:space:]]*lotus-research-pulse'; then
    echo "lotus-research-pulse already scheduled — leaving existing cron job in place"
    return 0
  fi

  echo "Scheduling lotus-research-pulse (every 6h)..."
  local prompt
  prompt="$(python3 -c "import json; print(json.load(open('$cron_json'))['prompt'])")"
  hermes -p lotus cron create "every 6h" "$prompt" \
    --name "lotus-research-pulse" \
    --deliver local \
    --skill lotus-realtime-core \
    --skill lotus-research-core \
    --skill lotus-medical-plain-language \
    --skill lotus-adaptive-language \
    --skill lotus-continuity \
    >/dev/null || echo "  (cron create skipped — run manually after setup)"
}

lotus_print_next_steps() {
  cat <<EOF

Installed at: $PROFILE_HOME

Next (same flow as Hermes — connect a model, then chat):
  lotus setup                 # Hermes wizard — model + provider (required)
  lotus doctor                # verify model / gateway / harness
  lotus                       # chat
  lotus gateway start         # relays + OpenAI API for the web UI
  lotus frontend              # Lotus web UI → http://127.0.0.1:8787

EOF
}

lotus_prune_foreign_skills() {
  # Hermes `hermes update` syncs bundled coding/creative skills into every profile.
  # That bloats the skills index and invites huge skill_view reads — bad for the
  # companion use-case and for weaker/local models (Teknium core-toolset batch).
  # Deleting respects Hermes' "user deletions" sync policy; lotus skills stay.
  local skills_root="${PROFILE_HOME}/skills"
  [[ -d "$skills_root" ]] || return 0

  local removed=0
  local dir
  for dir in apple autonomous-ai-agents creative email github media mlops \
    note-taking productivity research smart-home social-media software-development
  do
    if [[ -d "$skills_root/$dir" ]]; then
      rm -rf "$skills_root/$dir"
      removed=$((removed + 1))
    fi
  done

  # Keep only lotus/ (and any future first-party packs). Touch a marker so doctor can see intent.
  mkdir -p "$skills_root/lotus"
  date -u +"%Y-%m-%dT%H:%M:%SZ" >"$PROFILE_HOME/.lotus-skills-pruned" 2>/dev/null || true

  if [[ "$removed" -gt 0 ]]; then
    echo "Pruned $removed non-Lotus skill pack(s) from profile (companion-lean)."
  else
    echo "Skills:        lotus-only (no foreign packs to prune)"
  fi
}

lotus_run_post_install() {
  : "${PROFILE_HOME:?PROFILE_HOME required}"
  lotus_install_skin_theme
  lotus_install_harness
  lotus_seed_env
  lotus_install_cli
  lotus_prune_foreign_skills
  lotus_schedule_research_pulse
  lotus_print_next_steps
}
