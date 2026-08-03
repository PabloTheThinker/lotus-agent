# L.O.T.U.S.

**Light Over The Unseen Shadows**

[![CI](https://github.com/PabloTheThinker/lotus-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/PabloTheThinker/lotus-agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Open-source specialized [Hermes Agent](https://github.com/NousResearch/hermes-agent) profile + harness for mental and emotional support — present for depression, health stress, grief, and major life events. A steady companion in the dark: reconstructive, research-informed, and hard-guarded against chaos, violence, and self-harm.

Built **on** [Hermes Agent](https://hermes-agent.nousresearch.com/) by [Nous Research](https://nousresearch.com) — not a fork of Hermes core. See `NOTICE`.

> **Not a licensed clinician or emergency service.** If you or someone else is in immediate danger, contact local emergency services. In the US: **988** or **911**. International: https://www.iasp.info/suicidalthoughts/

## What you get

| Layer | Purpose |
|-------|---------|
| **Hermes profile distribution** | Installable agent: `SOUL.md`, skills, config, mission docs |
| **Lotus surfaces** | Skin, dashboard theme, CLI wrappers, gateway branding, hardened web UI |
| **Unified safety** | Single `lotus.guardrails` used by harness + thin Hermes plugin |
| **Doctor** | `lotus-harness doctor` / `./scripts/lotus-doctor.sh` readiness checks |
| **Realtime core** | Always-on understanding → learning → research + living user model |
| **Continuity** | Hermes-native session bridge — resume cards, open threads, USER.md sync candidates |
| **Moments graph** | Connects life events, threads, and conversation data across sessions (`moments.json`) |
| **Compound journey** | Long-term *user* mission + center checkpoint gate + meter (progress / longer path) |
| **Careful speech** | Moment-aware wording — prefer/avoid lists + brutal-truth only when needed |
| **Internal profile** | Full working chart + private Lotus notes as you talk (`profile.json`) |
| **Adaptive language** | Speaks more like *them* over time using phrases, metaphors, and memories |
| **Medical → plain language** | OpenMed-aware structuring + CDC everyday words |
| **Context orchestrator** | Single `pre_llm` inject (realtime) with budget + sticky safety |
| **Safety plugin** | Unsafe-output filter (`lotus.guardrails`; crisis inject via orchestrator) |
| **Honcho (optional)** | Hermes memory provider — `hermes -p lotus memory setup honcho` |
| **Specialized harness** | Python wrapper around Hermes `AIAgent` with protocol routing & research core |
| **Research pulse (cron)** | Background search (incl. @openmed_ai / plain-language topics) every 6h |

## Quick install

Same shape as Hermes: install once, then a single CLI. Requires [Hermes Agent](https://hermes-agent.nousresearch.com/) (`hermes` on PATH, ≥0.19).

**1. Hermes (if you don't have it yet)**

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

**2. L.O.T.U.S.**

```bash
curl -fsSL https://raw.githubusercontent.com/PabloTheThinker/lotus-agent/main/install.sh | bash
```

From a local clone: `./install.sh` (or `./scripts/install-profile.sh`).

**3. Connect a model → chat** (Hermes wizard, Lotus-scoped)

```bash
lotus setup                 # model + provider (required once)
lotus doctor                # verify profile / harness / gateway
lotus                       # chat (default)
lotus gateway start         # relays + OpenAI API for the web UI
lotus frontend              # Lotus web UI → http://127.0.0.1:8787
```

Pure Hermes equivalent:

```bash
hermes profile install github.com/PabloTheThinker/lotus-agent --alias --name lotus
# then re-run ./install.sh once to install the Lotus CLI verbs + harness,
# or: hermes -p lotus setup && hermes -p lotus chat
```

Update later: `lotus update` · keep Hermes current with `hermes update`

### Efficiency (local / weaker models)

Hermes’ core-toolset performance batch (fewer wasted tool turns, ~40% terminal schema diet, skill_view dedup — see [Teknium’s note](https://x.com/Teknium/status/2084065915004747888)) lands via `hermes update`. Lotus builds on that with **companion-lean defaults**:

- Heavy coding toolsets off by default (`browser`, `terminal`, `file`, `delegation`, `code_execution`) — re-enable with `lotus tools`
- Non-Lotus Hermes skill packs pruned on install/update (skills index stays lotus-focused)
- Short runtime `AGENTS.md`; operator notes live in `docs/OPERATORS.md` (not chat context)
- Tighter `tool_output` caps for smaller context windows

Measure anytime: `lotus prompt-size` · large session DBs: `lotus sessions optimize-storage`

### Surfaces (Hermes foundation · Lotus brand)

| Command | Surface |
|---------|---------|
| `lotus` / `lotus chat` | CLI / TUI with `skins/lotus.yaml` |
| `lotus gateway` | Messaging relays + OpenAI-compatible API (`:8642/v1`) |
| `lotus frontend` | Lotus web chat (proxies to gateway; keeps API key server-side) |
| `lotus dashboard` | Hermes dashboard with `dashboard.theme: lotus` |
| `lotus setup` / `lotus doctor` | Hermes setup wizard + Lotus readiness checks |

## Mission protocols

1. **Depression & numbness** — witness, shrink the frame, micro-agency  
2. **Health stress** — cope & organize; never replace medical care  
3. **Grief / loss** — hold space; no forced closure  
4. **Major life events** — regulate overwhelm (bad *or* good); secure next steps  

Rebuild ladder: **Safety → Body → Contact → Horizon → Meaning**

## Realtime core

Every turn, three subroutines run:

1. **Understanding** — affect, protocols, needs, preferences  
2. **Learning** — what helped / hurt; living model in `memories/lotus-core/`  
3. **Research** — queue gaps → find safer public-evidence approaches (plus cron pulse)

```bash
export HERMES_HOME=~/.hermes/profiles/lotus
lotus-harness core-tick "I feel numb and don't know how to start"
lotus-harness core-status
```

## Specialized harness

```bash
cd harness && python3 -m venv /tmp/lotus-harness-venv
/tmp/lotus-harness-venv/bin/pip install -e ".[dev]"
/tmp/lotus-harness-venv/bin/pytest
export HERMES_HOME=~/.hermes/profiles/lotus
lotus-harness classify "I feel numb and empty"
lotus-harness chat
```

## Repository map

```
install.sh              Hermes-style one-liner installer (curl | bash)
bin/lotus               Lotus CLI → hermes -p lotus (+ doctor/update/gateway/…)
SOUL.md                 Identity & voice
MISSION.md              Protocol playbooks
GUARDRAILS.md           Non-negotiable safety
AGENTS.md               Operator notes
config.yaml             Profile defaults + Lotus skin/theme
skins/lotus.yaml        CLI / TUI branding
dashboard-themes/       Hermes dashboard palette
frontend/               Lotus web chat UI + proxy server
skills/lotus/           Companion skills
plugins/lotus-*/        Hermes hooks
harness/                Specialized Python runtime
research/               Source posture + foundations
scripts/                Doctor / gateway / UI helpers + install lib
```

## Research ethics

L.O.T.U.S. integrates **public** science and open research (including publicly released Nous Research and published industry research). It does **not** claim access to reverse-engineered private neural datasets or proprietary personal brain data.

## Messaging & API

**Model connection always goes through Hermes setup** (`lotus setup` / `lotus setup model`). That wizard writes provider credentials and the default model into the lotus profile — do not bypass it with ad-hoc key hacks for day-to-day use.

For the Lotus web UI, keep `API_SERVER_ENABLED=true` and `API_SERVER_KEY` in the profile `.env` (install seeds these). Optional Telegram/Discord tokens also use Hermes setup / gateway (`lotus gateway start`) with `GATEWAY_RELAY_DISPLAY_NAME=L.O.T.U.S.`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

```bash
cd harness && pip install -e ".[dev]" && ruff check lotus tests && pyright lotus && pytest -q
```

Live model transcripts under `harness/tests/artifacts/` are **local-only** (gitignored), matching Hermes’s practice of not committing non-deterministic chat dumps.

## License

MIT — see [`LICENSE`](LICENSE). Hermes Agent attribution: [`NOTICE`](NOTICE).
