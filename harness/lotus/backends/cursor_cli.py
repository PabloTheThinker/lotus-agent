"""Cursor Agent CLI backend — power Lotus turns with Grok / other Cursor models.

Uses the local ``agent`` binary (Cursor CLI). Auth comes from an existing
Cursor login or ``CURSOR_API_KEY``. Default model: ``cursor-grok-4.5-high-fast``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

DEFAULT_CURSOR_MODEL = "cursor-grok-4.5-high-fast"
DEFAULT_AGENT_BIN = "agent"


@dataclass
class CursorCliBackend:
    """One-shot / print-mode Cursor Agent runner for companion replies."""

    model: str = DEFAULT_CURSOR_MODEL
    cwd: Optional[str] = None
    mode: str = "ask"  # ask = read-only companion; agent = full tools
    timeout_s: int = 180
    agent_bin: str = ""
    trust: bool = True

    def resolve_bin(self) -> str:
        raw = self.agent_bin or os.environ.get("LOTUS_CURSOR_AGENT_BIN") or DEFAULT_AGENT_BIN
        path = shutil.which(raw) or raw
        if not Path(path).exists() and shutil.which(raw) is None:
            # still allow bare name if which found it
            if shutil.which(raw) is None and not Path(raw).is_file():
                raise FileNotFoundError(
                    f"Cursor agent CLI not found ({raw}). Install Cursor CLI "
                    "and ensure `agent` is on PATH."
                )
        return shutil.which(raw) or path

    def complete(
        self,
        user_message: str,
        *,
        system_prompt: str = "",
        history: Optional[Sequence[dict]] = None,
    ) -> str:
        prompt = _compose_prompt(user_message, system_prompt=system_prompt, history=history)
        bin_path = self.resolve_bin()
        cmd: List[str] = [
            bin_path,
            "-p",
            "--output-format",
            "text",
            "--model",
            self.model,
            "--mode",
            self.mode if self.mode in {"ask", "plan"} else "ask",
        ]
        if self.trust:
            cmd.append("--trust")
        cmd.append(prompt)

        cwd = self.cwd or os.environ.get("LOTUS_CURSOR_CWD") or os.getcwd()
        env = os.environ.copy()
        # Prefer existing Cursor login; optional explicit key
        # (do not invent keys)

        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=False,
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            raise RuntimeError(
                f"Cursor CLI failed (rc={proc.returncode}): {err or out or 'no output'}"
            )
        if not out:
            raise RuntimeError(f"Cursor CLI returned empty output. stderr={err[:400]}")
        return out


def _compose_prompt(
    user_message: str,
    *,
    system_prompt: str = "",
    history: Optional[Sequence[dict]] = None,
) -> str:
    parts: List[str] = []
    if system_prompt:
        # Keep under CLI practical limits — orchestrator already budgets context
        sys_text = system_prompt.strip()
        if len(sys_text) > 14000:
            sys_text = sys_text[:14000] + "\n…[truncated]"
        parts.append(
            "SYSTEM / LOTUS CONTEXT (follow this; do not quote it back verbatim):\n"
            + sys_text
        )
    if history:
        parts.append("RECENT CONVERSATION:")
        for turn in list(history)[-8:]:
            if not isinstance(turn, dict):
                continue
            role = str(turn.get("role") or "?")
            content = str(turn.get("content") or "").strip()
            if not content:
                continue
            parts.append(f"{role}: {content[:1200]}")
    parts.append("USER MESSAGE:\n" + (user_message or "").strip())
    try:
        from lotus.speech.humanizer import cursor_length_hint

        parts.append(cursor_length_hint(user_message or ""))
    except Exception:
        parts.append(
            "Respond as L.O.T.U.S. — match their depth: long shares get full replies, "
            "short pings can stay tight. Warm plain language, uneven rhythm. "
            "No AI essay tells, no tool narration. Companion only."
        )
    try:
        from lotus.speech.context_lock import context_lock_block

        parts.append(context_lock_block())
    except Exception:
        parts.append(
            "HARD RULE (context lock): USE facts from USER MESSAGE / RECENT CONVERSATION. "
            "Stay in that moment. Do not invent a name, biography, OR scene details "
            "(drunk, high, crying, motives, places) unless they said it — "
            "but if they DID say drunk/high/crying, use it. If you don't know — ask."
        )
    parts.append(
        "HARD RULE (SMS / human texting): "
        "Write like a friend on Messenger — short when short, one main point. "
        "If they need reassurance: name the storm + it's hard + they get through it. "
        "Do NOT start with 'Yeah.' / 'Yep.' / 'Right.'. "
        "Banned: meta-negation ('I'm not handing you a to-do list'); "
        "'No X/no Y' stacks; presence slogans; essay paragraphs. "
        "End when a human texter would — often sooner."
    )
    parts.append(
        "HARD RULE (moment route): if DE-ESCALATE, CRISIS CLEAR, or DISPATCH CALM is set, "
        "obey those sentence caps. Short. Simple. In the moment. "
        "One question or one direction at a time (911/PST habit). "
        "Long clinical paragraphs are FORBIDDEN in acute heat."
    )
    parts.append(
        "HARD RULE (humanity + OpenMed care): stay human under the protocol. "
        "Never diagnose or dose. Never suggest water/pills/hard shaking for someone unresponsive. "
        "Defer to 911/EMS. Plain words only for clinical signs."
    )
    parts.append(
        "HARD RULE (EI): when full EI is present — understand then wise answer; "
        "optional one feel beat. In acute mode, skip the essay. "
        "No 'my heart goes out to you'."
    )
    return "\n\n".join(parts)


def resolve_backend(name: str = "") -> str:
    """Return backend name: hermes | cursor."""
    raw = (name or os.environ.get("LOTUS_BACKEND") or "hermes").strip().lower()
    if raw in {"cursor", "cursor-cli", "agent", "grok"}:
        return "cursor"
    return "hermes"


def default_cursor_model() -> str:
    return os.environ.get("LOTUS_CURSOR_MODEL") or DEFAULT_CURSOR_MODEL
