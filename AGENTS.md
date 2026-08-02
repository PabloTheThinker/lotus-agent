# L.O.T.U.S. Agent Operating Notes

Project context for the L.O.T.U.S. Hermes profile and specialized harness.

## What this repo is

1. **Hermes profile distribution** — `SOUL.md`, `config.yaml`, skills, and safety plugin installable via `hermes profile install`.
2. **Specialized harness** — `harness/` Python package that wraps Hermes `AIAgent` with protocol routing, crisis scanning, and research-informed context injection.

## Read order for the agent

1. `SOUL.md` — identity & voice (loaded by Hermes automatically)
2. `MISSION.md` — protocol playbooks (P1–P4 + rebuild ladder)
3. `GUARDRAILS.md` — non-negotiable safety
4. `skills/lotus/*/SKILL.md` — procedural skills (incl. `lotus-humanizer` voice)
5. `research/SOURCES.md` — research posture and source tiers

Speech: **Moment route** (topic × severity) → Voice OS → EI (when not acute) → Flow.
Acute heat uses AAEP BETA / PFA style: short sentences, simple words (see `moment_route`).
Full EI (appraisal + wisdom) only when severity allows. Humanizer anti-tells always.
Do **not** write clinical essays into a flooded moment.

## Install (profile)

```bash
hermes profile install /path/to/lotus-agent --alias
lotus setup          # Hermes wizard — connect AI model / provider (required)
lotus chat           # talk to L.O.T.U.S.
```

Or from this repo:

```bash
./scripts/install-profile.sh
./scripts/lotus-setup.sh            # → lotus setup (Hermes model wizard)
./scripts/lotus-doctor.sh
./scripts/run-lotus.sh              # Lotus CLI chat
./scripts/lotus-gateway.sh start    # Hermes gateway + API
./scripts/lotus-frontend.sh         # Lotus web UI (port 8787)
```

Model/provider configuration is **Hermes CLI setup only** (`lotus setup` / `lotus setup model`) for the default Hermes backend. Lotus wrappers must not replace that flow.

**Alternate backend — Cursor CLI (Grok):** for harness testing without Hermes model setup:

```bash
LOTUS_BACKEND=cursor lotus-harness ask "I feel numb today"
# or:
lotus-harness ask --backend cursor --model cursor-grok-4.5-high-fast "I feel numb today"
```

Uses the local `agent` binary (`--mode ask --trust`). Auth: existing Cursor login or `CURSOR_API_KEY`.

## Lotus surfaces (keep Hermes foundation)

| Path | Role |
|------|------|
| `skins/lotus.yaml` | CLI/TUI colors + branding (`display.skin: lotus`) |
| `dashboard-themes/lotus.yaml` | Dashboard palette (`dashboard.theme: lotus`) |
| `frontend/` | Web chat; session token + rate limit + SSE proxy → Hermes `/v1` |
| `scripts/lotus-*.sh` | CLI / gateway / frontend / doctor launchers |
| `harness/lotus/guardrails.py` | Single safety source for plugin + harness |
| `harness/lotus/doctor.py` | Install / env / gateway readiness |

Do not fork Hermes core for branding — skin YAML + wrappers + frontend only.
Safety patterns live only in `lotus.guardrails`; `plugins/lotus-safety` must stay thin.

## Harness (library mode)

```bash
cd harness && pip install -e .
lotus-harness chat
```

## Safety plugin

`plugins/lotus-safety/` hooks into Hermes:
- `transform_llm_output` — blocks clearly unsafe outgoing patterns when possible
- Crisis / protocol **context inject** is owned by the orchestrator (via `lotus-realtime`), not this plugin

## Hermes plugin pattern (this repo)

Thin plugins under `plugins/lotus-*/` register hooks only. Business logic lives in `harness/lotus/`. Shared import bootstrap: `lotus.plugin_bootstrap`.

| Plugin | Hooks | Harness |
|--------|-------|---------|
| `lotus-safety` | `transform_llm_output` | `lotus.guardrails` |
| `lotus-continuity` | `on_session_start/end`, `post_llm_call` | `lotus.continuity` |
| `lotus-realtime` | `on_session_start`, `pre/post_llm_call` (**sole context inject**) | `lotus.context` + `lotus.realtime` |
| `lotus-moments` | `on_session_start/end`, `post_llm_call` | `lotus.moments` |
| `lotus-compound` | `on_session_start`, `post_llm_call` | `lotus.compound` |
| `lotus-profile` | `on_session_start` | `lotus.profile` (updated via realtime) |

**Context orchestrator** (`lotus.context.build_turn_context`): merges safety, living model, profile, speech, adaptive language, continuity, compound, moments, research, and optional plain-language / LLM-extract / LLM-understand blocks under `LOTUS_CONTEXT_BUDGET_CHARS` (default 12000). Only `lotus-realtime` returns context from `pre_llm_call`. Over-budget drops are logged (`LOTUS_CONTEXT_DEBUG=1` for always-on).

Moments graph (`moments.json` + `MOMENTS.md`) links events across conversations.
Compound journey (`compound.json` + `COMPOUND.md`) grows *their* long-term mission; center checkpoint gates deeper guidance; stalls extend the journey horizon. Opt-in UI meter: `LOTUS_JOURNEY_UI` + frontend toggle.
Careful speech (`harness/lotus/speech/`, skill `lotus-careful-speech`) maps moments/protocols to prefer/avoid wording and gates brutal truth (`off` / `invited` / `required`).
Internal profile (`profile.json` + `PROFILE.md` + `LOTUS_NOTES.md`) is a professional companion chart built while talking — not a clinical record.
Prefs (`prefs.json`): `preferred_lang` + `crisis_regions` + `lang_locked` (also `LOTUS_PREFERRED_LANG` / `LOTUS_CRISIS_REGIONS`). Soft autodetect from message cues when unlocked.
State JSON uses `_schema_version` with soft migrations (`lotus.schema`).

Privacy agency over `memories/lotus-core/`:

```bash
lotus-harness privacy status
lotus-harness privacy export [--out PATH]
lotus-harness privacy wipe --yes [--keep-prefs] [--keep-approaches]
```

`pre_llm_call` (realtime only) returns `{"context": "..."}`. Durable facts → Hermes `memory` tool → USER.md / MEMORY.md.

## Realtime + continuity

| System | When | Output |
|--------|------|--------|
| Understanding | every `pre_llm_call` (cached for post) | affect, needs, protocols |
| Learning | every `post_llm_call` | living model + voice profile |
| Adaptive language | every turn | phrases/metaphors/memories → relatability |
| Continuity | session bridge | RESUME.md, open threads, MEMORY_SYNC.md |
| Research | every turn + cron | APPROACHES.md |

State: `$HERMES_HOME/memories/lotus-core/`.

Disable (any of these → orchestrator skips that block / plugin skips hooks):
`LOTUS_SAFETY_DISABLE`, `LOTUS_REALTIME_DISABLE`, `LOTUS_CONTINUITY_DISABLE`,
`LOTUS_MOMENTS_DISABLE`, `LOTUS_COMPOUND_DISABLE`, `LOTUS_PROFILE_DISABLE`,
`LOTUS_SPEECH_DISABLE`.

Opt-in enrichers: `LOTUS_LLM_EXTRACT=1`, `LOTUS_LLM_UNDERSTAND=1` (never downgrades regex crisis).

## Design principles

- Edges over core: skills + plugin + SOUL, not a bloated fork of Hermes internals.
- Safety beats cleverness.
- Always-on understanding > one-shot prompts.
- Research is first-class but public and ethical — no proprietary reverse-engineering claims.
- Deep user understanding grows via living model + Hermes memory + optional Honcho + lotus skills.

## Honcho (optional Hermes memory provider)

Honcho is **not** reimplemented in Lotus. It is Hermes' memory-provider plugin.

```bash
hermes -p lotus memory setup honcho   # configure for this profile
lotus-harness doctor                  # shows honcho status
```

When `memory.provider: honcho` and credentials exist, the orchestrator injects a short
reminder to use Honcho tools alongside lotus-core files. Continuity stays file+hook based.
Disable the reminder with `LOTUS_HONCHO_DISABLE=1`.
