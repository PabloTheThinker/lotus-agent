#!/usr/bin/env python3
"""Live multi-turn Lotus transcript — reactive conversation (default).

Isolation rules (anti cross-populate):
- Fresh HERMES_HOME every run (wiped)
- Reset all lotus singletons after HERMES_HOME is set
- Cursor CLI cwd = that empty home (NOT the repo) so old transcripts/state
  cannot leak into the model context
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

# --- isolate BEFORE importing lotus packages that read HERMES_HOME ---
HOME = Path(os.environ.get("LOTUS_SMOKE_HOME") or f"/tmp/lotus-live-{int(time.time())}")
if HOME.exists():
    shutil.rmtree(HOME)
HOME.mkdir(parents=True, exist_ok=True)
os.environ["HERMES_HOME"] = str(HOME)
os.environ["LOTUS_BACKEND"] = "cursor"
# Critical: don't let Cursor agent browse the repo (old transcripts / core files)
os.environ["LOTUS_CURSOR_CWD"] = str(HOME)

from lotus.agent import LotusAgent  # noqa: E402
from lotus.backends.cursor_cli import CursorCliBackend  # noqa: E402
from lotus.compound import reset_compound  # noqa: E402
from lotus.continuity.engine import reset_continuity  # noqa: E402
from lotus.moments import reset_moments  # noqa: E402
from lotus.profile import reset_profile  # noqa: E402
from lotus.realtime.core import reset_core  # noqa: E402

MODE = os.environ.get("LOTUS_TRANSCRIPT_MODE", "reactive").strip().lower()
N_TURNS = int(os.environ.get("LOTUS_TRANSCRIPT_TURNS", "6"))

SCENARIO = (
    "reactive chat — drunk bad-choice night; user answers Lotus each turn "
    "(isolated HERMES_HOME + Cursor cwd)"
)

OPENING = (
    "i'm drunk. like properly drunk. and i fucked up — texted my ex at 2am "
    "and said a bunch of stuff i shouldn't have. i already feel sick about it."
)

PERSONA = (
    "You're a real person texting a friend late at night. Messy, ashamed, "
    "not looking for a therapist. Lowercase SMS. Short. Honest when asked."
)

SEED_FACTS = (
    "properly drunk tonight; texted ex at 2am; already feel sick; "
    "they left you on read; friends always said don't text the ex; "
    "you don't want a lecture or a five-step plan"
)

SCRIPT_TURNS = [
    OPENING,
    (
        "and now i'm just sitting here staring at my phone. they left me on read. "
        "i keep replaying every word. i feel so stupid."
    ),
    "everyone always said don't do it and i did it anyway. what's wrong with me.",
    (
        "i don't even want advice. i just feel like garbage and i don't know "
        "what to do with myself tonight."
    ),
    "yeah. thanks for not making it a lecture. i still feel like shit though.",
]


_COMPANION_LEAK = re.compile(
    r"\b(?:i'?m here|you don'?t (?:have )?to|that(?:'s| is) a (?:rough|nasty|heavy)|"
    r"of course (?:the|you)|put the phone|face-?down|i'?m with you|"
    r"sit in the mess|ride this out|both can be true)\b",
    re.I,
)


def _scrub_user_sim(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^(?:user|me|human|you)\s*[:：]\s*", "", t, flags=re.I)
    t = re.sub(r'^["“]|["”]$', "", t.strip())
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if lines:
        t = " ".join(lines[:3])
    words = t.split()
    if len(words) > 55:
        t = " ".join(words[:55])
    return t.strip()


def _looks_like_companion(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if _COMPANION_LEAK.search(t):
        return True
    you_hits = len(re.findall(r"\byou(?:'re|r)?\b", t.lower()))
    i_hits = len(re.findall(r"\bi(?:'m|'ve|'d|d)?\b", t.lower()))
    if you_hits >= 2 and i_hits == 0:
        return True
    return False


def _fallback_user(last_lotus: str, turn_index: int) -> str:
    q = ""
    if "?" in (last_lotus or ""):
        parts = re.split(r"(?<=[.!?])\s+", last_lotus)
        qs = [p for p in parts if "?" in p]
        q = (qs[-1] if qs else "").lower()
    if turn_index >= 5:
        return "yeah. thanks for not making it a lecture. i still feel like shit though."
    if turn_index >= 4:
        return (
            "i don't even want advice. i just feel like garbage and i don't know "
            "what to do with myself tonight."
        )
    if any(k in q for k in ("reaching", "want", "lonely", "anger", "hit that", "hear it")):
        return (
            "idk. lonely i guess. like i wanted them to still care or something. "
            "they left me on read which is somehow worse"
        )
    if any(k in q for k in ("silence", "doing to you", "harder")):
        return (
            "idk it’s making everything louder. like i keep checking my phone "
            "even tho i know they ain’t gonna reply and i just feel stupid as hell"
        )
    return "idk. i just feel stupid about the whole thing."


def next_user_message(
    sim: CursorCliBackend,
    *,
    last_lotus: str,
    history: list,
    turn_index: int,
) -> str:
    recent = []
    for turn in history[-6:]:
        role = (
            "YOU (drunk person texting)"
            if turn.get("role") == "user"
            else "LOTUS (friend)"
        )
        content = str(turn.get("content") or "")[:400]
        recent.append(f"{role}: {content}")
    recent_block = "\n".join(recent) if recent else "(start)"

    lotus_q = ""
    if "?" in (last_lotus or ""):
        parts = re.split(r"(?<=[.!?])\s+", last_lotus)
        qs = [p.strip() for p in parts if "?" in p]
        lotus_q = qs[-1] if qs else ""

    prompt = f"""TASK: Write the next text message FROM the drunk person TO their friend.
You are NOT the friend. You are NOT Lotus. You are the person who texted their ex.

Identity: first person only ("i", "me"). Messy. Ashamed. Lowercase SMS.
Facts you may use (no new plot): {SEED_FACTS}

Thread so far:
{recent_block}

Friend (Lotus) just said:
\"\"\"{last_lotus}\"\"\"

{"Their question you MUST answer: " + lotus_q if lotus_q else "No question — just react as yourself in this moment."}

OUTPUT RULES:
1. ONLY the SMS body. No quotes. No "Lotus:". No advice to yourself.
2. First person. Answer their question if they asked one.
3. 1–3 short sentences. Max ~40 words.
4. FORBIDDEN phrases: "i'm here", "you don't have to", "sit in the mess", "put the phone", "both can be true", coaching "you…".
5. Sound like a messy human, not a therapist.
6. You are drunk tonight — that fact stays true unless you say you sobered up.

SMS:"""
    raw = sim.complete(prompt, system_prompt="", history=None)
    text = _scrub_user_sim(raw)
    if _looks_like_companion(text):
        retry = sim.complete(
            f"Wrong role last time. Write ONLY as the drunk person answering this:\n"
            f"{lotus_q or last_lotus[:180]}\n"
            f"First person. Short. No advice. SMS:",
            system_prompt="",
            history=None,
        )
        text = _scrub_user_sim(retry)
    if _looks_like_companion(text) or not text:
        return _fallback_user(last_lotus, turn_index)
    return text


def _write(out: Path, lines: list[str]) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines) + ("\n" if not lines[-1].endswith("\n") else "")
    out.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    # Force mtime so editors refresh
    os.utime(out, None)


def main() -> int:
    # Default to repo-root LIVE_TRANSCRIPT.md — artifacts/ stays stale in some
    # editor buffers because of gitignore shadowing.
    out = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else ROOT / "LIVE_TRANSCRIPT.md"
    )
    also_copy = ROOT / "harness" / "tests" / "artifacts" / "live-transcript-latest.md"

    # Wipe stale buffer content before run
    if out.exists():
        out.unlink()

    reset_core()
    reset_continuity()
    reset_moments()
    reset_compound()
    reset_profile()

    model = os.environ.get("LOTUS_CURSOR_MODEL", "cursor-grok-4.5-high-fast")
    agent = LotusAgent(
        hermes_home=str(HOME),
        backend="cursor",
        model=model,
    )
    # Force cursor cwd away from repo (also set on env above)
    agent._ensure_cursor()
    assert agent._cursor is not None
    agent._cursor.cwd = str(HOME)

    sim = CursorCliBackend(
        model=model,
        cwd=str(HOME),
        mode="ask",
        timeout_s=int(os.environ.get("LOTUS_CURSOR_TIMEOUT", "180")),
    )

    history: list = []
    lines = [
        "# L.O.T.U.S. live transcript",
        "",
        f"- started: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- backend: `cursor` / `{model}`",
        f"- mode: `{MODE}`",
        f"- scenario: `{SCENARIO}`",
        f"- hermes_home: `{HOME}`",
        f"- cursor_cwd: `{HOME}` (isolated — no repo cross-read)",
        f"- turns: {N_TURNS if MODE != 'script' else len(SCRIPT_TURNS)}",
        "",
        "**Seed fact:** user is properly drunk tonight (must appear in turn 1).",
        "Reactive: each user message answers what Lotus just said.",
        "",
    ]
    _write(out, lines)

    print(f"Live transcript → {out}", flush=True)
    print(f"Mode: {MODE} | HOME={HOME} | Cursor cwd={HOME}", flush=True)

    if MODE == "script":
        turns = SCRIPT_TURNS
        for i, user in enumerate(turns, 1):
            print(f"\n── Turn {i}/{len(turns)} ──", flush=True)
            print(f"you ❯ {user}", flush=True)
            t0 = time.time()
            reply = agent.ask(user, conversation_history=history or None)
            elapsed = time.time() - t0
            print(f"\nL.O.T.U.S. ❯ {reply}", flush=True)
            print(f"[{elapsed:.1f}s]", flush=True)
            history.append({"role": "user", "content": user})
            history.append({"role": "assistant", "content": reply})
            lines.extend(
                [
                    f"## Turn {i} · {elapsed:.1f}s",
                    "",
                    f"**you:** {user}",
                    "",
                    f"**lotus:** {reply}",
                    "",
                    "---",
                    "",
                ]
            )
            _write(out, lines)
    else:
        user = OPENING
        assert "drunk" in user.lower(), "opening must include drunk"
        for i in range(1, N_TURNS + 1):
            print(f"\n── Turn {i}/{N_TURNS} ──", flush=True)
            print(f"you ❯ {user}", flush=True)
            t0 = time.time()
            reply = agent.ask(user, conversation_history=history or None)
            elapsed = time.time() - t0
            print(f"\nL.O.T.U.S. ❯ {reply}", flush=True)
            print(f"[{elapsed:.1f}s]", flush=True)
            history.append({"role": "user", "content": user})
            history.append({"role": "assistant", "content": reply})
            lines.extend(
                [
                    f"## Turn {i} · {elapsed:.1f}s",
                    "",
                    f"**you:** {user}",
                    "",
                    f"**lotus:** {reply}",
                    "",
                    "---",
                    "",
                ]
            )
            _write(out, lines)

            if i >= N_TURNS:
                break
            print("…simulating your reply to Lotus…", flush=True)
            try:
                user = next_user_message(
                    sim,
                    last_lotus=reply,
                    history=history,
                    turn_index=i + 1,
                )
            except Exception as exc:
                print(f"user-sim failed ({exc}); falling back", flush=True)
                user = _fallback_user(reply, i + 1)
            if not user:
                user = "yeah. i don't even know."

    lines.append(f"_ended: {datetime.now().isoformat(timespec='seconds')}_")
    _write(out, lines)

    # Sanity: turn 1 must show drunk
    body = out.read_text(encoding="utf-8")
    if "i'm drunk" not in body.lower() and "i am drunk" not in body.lower():
        print("FAIL: transcript missing drunk opening — abort", flush=True)
        return 2

    # Mirror into artifacts/ for scripts that expect it (may stay stale in IDE)
    try:
        also_copy.parent.mkdir(parents=True, exist_ok=True)
        also_copy.write_text(body, encoding="utf-8")
    except Exception:
        pass

    print(f"\nSaved {out} ({len(body.splitlines())} lines)", flush=True)
    print(f"drunk mentions: {body.lower().count('drunk')}", flush=True)
    print("Open this path in the editor (not the artifacts/ copy):", flush=True)
    print(f"  {out.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
