"""Ephemeral system prompt assembly for L.O.T.U.S."""

from __future__ import annotations

import os
from pathlib import Path

from .guardrails import assess_user_text, crisis_preamble
from .protocols import classify_protocol
from .research import research_context, should_encourage_live_lookup

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(name: str, max_chars: int = 12000) -> str:
    path = _REPO_ROOT / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()[:max_chars]


def _slim_cursor_backend() -> bool:
    return os.environ.get("LOTUS_BACKEND", "").strip().lower() in {
        "cursor",
        "cursor-cli",
        "agent",
        "grok",
    }


def build_ephemeral_system_prompt(
    user_message: str,
    *,
    include_mission: bool = True,
    include_guardrails: bool = True,
    realtime_context: str = "",
) -> str:
    """Compose a specialized ephemeral system prompt for one turn/session."""
    protocol = classify_protocol(user_message)
    safety = assess_user_text(user_message)
    slim = _slim_cursor_backend()

    sections = [
        "You are operating as L.O.T.U.S. (Light Over The Unseen Shadows).",
        "Companion only — not a licensed clinician. Never guide chaos, violence, or self-harm.",
        "Speak as L.O.T.U.S. through the Speech Gateway: your thoughts, your diction — not a reflective paraphrase. "
        "Match their depth (long shares get full replies). Uneven rhythm, no AI essay tells.",
        "REALTIME CORE is always on: understand → learn (living model + talk patterns) → "
        "adapt speech → promote durable prefs via Hermes memory when confirmed.",
    ]
    if realtime_context:
        # Orchestrator already carries the live blocks — keep full for Hermes,
        # slightly tighter cap for Cursor CLI prompt size / latency.
        ctx = realtime_context
        if slim and len(ctx) > 9000:
            ctx = ctx[:9000] + "\n…[truncated live context]"
        sections.append("## Realtime core (live)\n" + ctx)

    soul_cap = 3500 if slim else 12000
    soul = _read("SOUL.md", max_chars=soul_cap)
    if soul:
        sections.append("## Identity\n" + soul)

    if include_mission:
        mission = _read("MISSION.md", max_chars=3500 if slim else 8000)
        if mission:
            sections.append("## Mission Protocols\n" + mission)

    if include_guardrails:
        guards = _read("GUARDRAILS.md", max_chars=3500 if slim else 8000)
        if guards:
            sections.append("## Guardrails\n" + guards)

    sections.append(f"## Active protocol\n{protocol.value}")
    sections.append(
        "## Research\n"
        + research_context(protocol, include_foundations=not slim)
    )

    if safety.inject_crisis_override:
        sections.append("## CRISIS OVERRIDE\n" + crisis_preamble())

    if should_encourage_live_lookup(user_message) and not slim:
        sections.append(
            "## Live research\n"
            "Use Hermes web research tools for current crisis resources or evidence; "
            "cite reputable sources; do not invent citations."
        )

    return "\n\n".join(sections)
