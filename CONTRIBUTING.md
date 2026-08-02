# Contributing to L.O.T.U.S.

Thanks for helping. Lotus is a specialized [Hermes Agent](https://github.com/NousResearch/hermes-agent) profile + harness for mental/emotional companion support. Development patterns follow Hermes where they fit.

## Before you start

1. Search [issues](https://github.com/PabloTheThinker/lotus-agent/issues) and PRs for duplicates.
2. Read `GUARDRAILS.md` and `SECURITY.md` — safety is load-bearing.
3. For Hermes core changes, contribute upstream to [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent). This repo is the Lotus profile/harness layer, not a Hermes fork.

## Priorities

1. **Safety & crisis handling** — never weaken guardrails for convenience.
2. **Bug fixes** — speech gateway, context lock (no invented details), harness crashes.
3. **Natural companion voice** — gateway / patterns / tests with live transcripts (local only).
4. **Docs & install friction** — clearer setup for Hermes + Lotus.
5. **Skills** — only if broadly useful for mental/emotional companion work.

## Dev setup

Requires Hermes Agent (`hermes` on PATH). See [Hermes install](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart).

```bash
git clone https://github.com/PabloTheThinker/lotus-agent.git
cd lotus-agent
./scripts/install-profile.sh

# Harness
cd harness
python3 -m venv /tmp/lotus-harness-venv
source /tmp/lotus-harness-venv/bin/activate   # or Windows equivalent
pip install -e ".[dev]"
ruff check lotus tests
pyright lotus
pytest -q
```

Optional live voice check (writes local artifacts — **not committed**):

```bash
HERMES_HOME=/tmp/lotus-live ./scripts/live-transcript.py
```

Frontend:

```bash
cd frontend && npm install && npm test
```

## Architecture pointers

| Path | Role |
|------|------|
| `SOUL.md` / `MISSION.md` / `GUARDRAILS.md` | Identity, protocols, safety |
| `harness/lotus/speech/gateway.py` | Single speech pipe (character + move) |
| `harness/lotus/speech/patterns.py` | Pattern recognition + talk plan |
| `plugins/lotus-*/` | Thin Hermes hooks |
| `skills/lotus/` | Procedural skills |
| `AGENTS.md` | Operator notes for agents working in this repo |

Speech goes through the **gateway** — do not re-stack Voice OS / EI / Flow essays into the prompt.

## Pull requests

- Keep PRs focused; one concern per PR when possible.
- Include tests for harness behavior you change.
- Do not commit secrets, `memories/`, live transcripts, or API keys.
- Do not weaken crisis / self-harm refusals.
- Run `ruff`, `pyright`, and `pytest` under `harness/` before pushing.

## Code of conduct

Be respectful. This project touches mental health — no mockery of users in distress, no shipping “gotcha” advice, no contributions that treat crisis content as entertainment.

## License

By contributing, you agree your contributions are licensed under the MIT License (`LICENSE`).
