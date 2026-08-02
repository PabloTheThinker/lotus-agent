# L.O.T.U.S.

**Light Over The Unseen Shadows**

A specialized [Hermes Agent](https://hermes-agent.nousresearch.com/) for mental and emotional support — present for depression, health stress, grief, and major life events. Built to be a steady light in darkness: reconstructive, research-informed, and hard-guarded against chaos, violence, and self-harm.

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

Requires Hermes Agent (`hermes` on PATH).

```bash
./scripts/install-profile.sh             # profile + harness pip + skin/theme

# Connect the AI model the Hermes way (required — powers chat / gateway / UI)
lotus setup                              # full Hermes wizard
# lotus setup model                      # model/provider only
# ./scripts/lotus-setup.sh               # same as lotus setup

./scripts/lotus-doctor.sh                # verify model / gateway / harness
./scripts/lotus-cli.sh                   # Lotus-skinned CLI
./scripts/lotus-gateway.sh start         # Hermes gateway + /v1 API
./scripts/lotus-frontend.sh              # Lotus web UI → http://127.0.0.1:8787
```

Or:

```bash
hermes profile install /path/to/lotus-agent --alias --name lotus
```

### Surfaces (Hermes foundation · Lotus brand)

| Command | Surface |
|---------|---------|
| `./scripts/lotus-cli.sh` | CLI / TUI with `skins/lotus.yaml` |
| `./scripts/lotus-gateway.sh` | Messaging relays + OpenAI-compatible API (`:8642/v1`) |
| `./scripts/lotus-frontend.sh` | Lotus web chat (proxies to gateway; keeps API key server-side) |
| `lotus dashboard` | Hermes dashboard with `dashboard.theme: lotus` |

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
scripts/                Install / CLI / gateway / UI helpers
```

## Research ethics

L.O.T.U.S. integrates **public** science and open research (including publicly released Nous Research and published industry research). It does **not** claim access to reverse-engineered private neural datasets or proprietary personal brain data.

## Messaging & API

**Model connection always goes through Hermes setup** (`lotus setup` / `lotus setup model`). That wizard writes provider credentials and the default model into the lotus profile — do not bypass it with ad-hoc key hacks for day-to-day use.

For the Lotus web UI, keep `API_SERVER_ENABLED=true` and `API_SERVER_KEY` in the profile `.env` (install seeds these). Optional Telegram/Discord tokens also use Hermes setup / gateway (`./scripts/lotus-gateway.sh`) with `GATEWAY_RELAY_DISPLAY_NAME=L.O.T.U.S.`

## License

MIT — see `LICENSE`.
