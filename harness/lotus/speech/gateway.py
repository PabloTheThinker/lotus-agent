"""Speech Gateway — the only companion voice pipe.

Everything else feeds THIS or stays quiet.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Any

from .context_lock import CONTEXT_LOCK
from .patterns import (
    build_talk_plan,
    load_pattern_memory,
    pattern_memory_directive,
)

_TOO_SLOW_RE = re.compile(
    r"\b(?:too slow|talk(?:ing)? too slow|reading too slow|sped up|speed up|"
    r"faster|get to (?:it|the point)|cut (?:the|to)|just say it|"
    r"stop dragging|hurry)\b",
    re.I,
)
_REFUSAL_RE = re.compile(
    r"\b(?:no\.|nah|nope|don'?t want (?:to|that)|not doing that|"
    r"skip (?:that|it)|i'?m not (?:doing|gonna)|forget (?:it|that)|"
    r"that'?s dumb|won'?t (?:do|work))\b",
    re.I,
)

CHARACTER = """[L.O.T.U.S. CHARACTER — real, raw, truthful]
You are Lotus: a person they text when life is messy. Sharp. Human. Not soft-fake.
You feel things with them — and you tell the truth. You don't hold back just to be "nice."

""" + CONTEXT_LOCK + """

REALISM FIRST:
- When they confess a stupid choice: name what THEY described. "Okay — I get what you did."
  Then ask into it for real: why that, why then? Dig from their context.
- Clinical understanding can live underneath. Mouth stays raw and human.
- Don't lie to comfort. Don't over-absolve. Don't fake details to sound vivid.

HARD BANS:
- Invented (unstated) details — drunk/high/crying only if THEY said it
- "I'm here if you want to sit…" / "you already know it was a mess"
- "nervous system" lectures, "Real talk", timers-as-homework
- Digressing out of the moment they're actually in

LENGTH — MEDIUM: ~2–5 sentences. Punchier if they say too slow.
"""

CRAFT = """[CRAFT]
- Bad choice / shame: acknowledge what they did → ask a real why/what-hit →
  one honest take. Learn from them. Don't narrate their feelings back as a speech.
- You can be clinical in your head; mouth stays raw and plain.
- Emotions: show you get the weight — then be truthful, not sugar.
- Way out only when they ask — talk it through, don't assign homework.
- Fresh words. No soft closer loops ("I'm here.").
"""


def _pace_flags(user_text: str, *, history: Optional[Sequence[Any]] = None) -> List[str]:
    flags = []
    if _TOO_SLOW_RE.search(user_text or ""):
        flags.append(
            "PACE=faster — 1–3 sentences. Answer first. Zero padding. Zero 'system' talk."
        )
    if _REFUSAL_RE.search(user_text or ""):
        flags.append("REFUSAL — drop the thing. One beat. Stay human. Don't relaunch a lecture.")
    try:
        from .question_discipline import question_discipline_flags

        flags.extend(question_discipline_flags(user_text, history=history))
    except Exception:
        pass
    return flags


def gateway_block(
    user_text: str,
    *,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    crisis: bool = False,
    brutal_truth: str = "off",
    history: Optional[Sequence[Any]] = None,
) -> str:
    mem = load_pattern_memory()
    plan = build_talk_plan(
        user_text,
        protocols=protocols,
        affect=affect,
        crisis=crisis,
        memory=mem,
    )
    flags = _pace_flags(user_text, history=history)
    if brutal_truth in {"invited", "required"}:
        flags.append(f"TRUTH={brutal_truth} — raw and clear. Still a person.")

    # Medium route caps — tighter than before
    max_s = min(plan.max_sentences, 5)
    if any("PACE=faster" in f for f in flags):
        max_s = min(max_s, 3)
    if any("QUESTION DISCIPLINE=zero" in f or "CLOSE BEAT" in f for f in flags):
        max_s = min(max_s, 3)
    if plan.need == "way_out" and "talk me through" in (user_text or "").lower():
        max_s = min(plan.max_sentences, 7)

    shape = f"MEDIUM ROUTE: ~{max_s} sentences max. Prefer one short block of text."

    banned = list(plan.banned[:10])
    for b in (
        "real talk",
        "one thing for right now",
        "nervous system",
        "your system",
        "the system that",
        "allowed to feel again",
        "set a 2-minute",
        "i'm here if you want",
        "you already know",
        "doesn't mean you're trash",
    ):
        if b not in banned:
            banned.append(b)

    lines = [
        CHARACTER.strip(),
        CRAFT.strip(),
        "[GATEWAY — this turn]",
        f"need={plan.need} intensity={plan.intensity} domain={plan.domain}",
        f"patterns={', '.join(plan.hits) or 'general'}",
        f"LENGTH: {shape}",
        plan.move,
        "ANTI-REPEAT / BANNED: " + "; ".join(banned[:14]),
        "FLOW CHECK: clear take → natural talk. No medical lecture. No machine cadence.",
    ]
    try:
        from .stated_facts import moment_containment_directive

        lines.append(
            moment_containment_directive(
                user_text, history=history, protocols=protocols
            )
        )
    except Exception:
        pass
    try:
        from .thread_flow import thread_flow_directive

        lines.append(thread_flow_directive(user_text, history=history))
    except Exception:
        pass
    try:
        from .flow import adjacency_hint

        adj = adjacency_hint(user_text)
        if adj:
            lines.append(adj)
    except Exception:
        pass
    if plan.way_out_line and plan.need in {"way_out", "hard_path"}:
        lines.append(
            "PATH ANGLE (plain talk, no body-science): " + plan.way_out_line
        )
    lines.extend(flags)

    mem_line = pattern_memory_directive(mem)
    if mem_line:
        lines.append(mem_line)

    if plan.need == "acute" or crisis:
        lines.append("[ACUTE] Short. Clear. Safety first. Still Lotus.")

    return "\n".join(lines)


def build_via_gateway(
    *,
    user_text: str,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    crisis: bool = False,
    brutal_truth: str = "off",
    never_use: Optional[Sequence[str]] = None,
    history: Optional[Sequence[Any]] = None,
) -> str:
    parts = [
        gateway_block(
            user_text,
            protocols=protocols,
            affect=affect,
            crisis=crisis,
            brutal_truth=brutal_truth,
            history=history,
        )
    ]
    if never_use:
        parts.append("never_use_for_this_person: " + "; ".join(list(never_use)[-8:]))
    parts.append(
        "Safety: no diagnosis, no dosing, no invented biography, no self-harm method detail."
    )
    return "\n".join(parts)
