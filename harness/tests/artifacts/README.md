# Test artifacts (local only)

This directory holds **regenerated** outputs from live / stress scripts.
They are gitignored — like Hermes’s policy for non-deterministic model transcripts.

## Generate locally

```bash
# Multi-turn companion transcript (Cursor/Grok or Hermes)
HERMES_HOME=/tmp/lotus-live ./scripts/live-transcript.py

# Optional deeper path tests
./scripts/human-path-test.py
./scripts/human-path-deep.py
```

Outputs such as `live-transcript-latest.md` help iterate on voice; they are not
part of the open-source release surface. Unit tests under `harness/tests/test_*.py`
are what CI runs.
