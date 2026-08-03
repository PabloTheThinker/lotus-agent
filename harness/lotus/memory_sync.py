"""Bridge lotus-core learning → Hermes-visible memory (production).

- Inject: nudge the model to use Hermes `memory` tool for durable prefs
- Persist: write MEMORY_SYNC.md so continuity / operators can see candidates
- Queue: push high-confidence pattern prefs into continuity promotions
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from lotus.realtime.model import LivingUserModel
    from lotus.speech.patterns import TalkPatternMemory


def _candidates(
    model: "LivingUserModel",
    pattern_mem: Optional["TalkPatternMemory"] = None,
) -> List[str]:
    candidates: List[str] = []

    if model.avoided_language:
        candidates.append(
            "Never use these words/phrases with this person: "
            + "; ".join(model.avoided_language[-6:])
        )
    if model.preferred_language:
        candidates.append(
            "Style they asked for: " + "; ".join(model.preferred_language[-4:])
        )

    style = model.voice_style or {}
    if style.get("reply_length") == "short" or (
        pattern_mem and pattern_mem.prefers_short
    ):
        candidates.append("They prefer shorter SMS-length replies.")
    if pattern_mem and pattern_mem.hates_worksheets:
        candidates.append("They hate five-step worksheets — one path / talk-through only.")
    if pattern_mem and pattern_mem.hates_meta:
        candidates.append("Never announce what you won't do (meta-negation).")
    if pattern_mem and pattern_mem.soft_company:
        candidates.append("Sometimes wants company over tips — listen first.")
    if pattern_mem and getattr(pattern_mem, "hates_lecture", False):
        candidates.append("They hate lectures — statements only when they say so.")
    if pattern_mem and pattern_mem.soft_loop_count >= 2:
        candidates.append(
            "Soft-hope loop detected recently — escalate with hard truth + one path."
        )

    if model.connection_anchors:
        candidates.append(
            "Connection anchors (confirm before USER.md): "
            + "; ".join(model.connection_anchors[-4:])
        )

    try:
        from lotus.continuity import get_continuity

        for p in list(get_continuity().state.memory_promotions)[-5:]:
            if not isinstance(p, dict):
                continue
            kind = str(p.get("kind") or "note")
            content = str(p.get("content") or "").strip()
            if content:
                candidates.append(f"{kind}: {content[:120]}")
    except Exception:
        pass

    # de-dupe preserve order
    seen = set()
    out: List[str] = []
    for c in candidates:
        k = c.lower()
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out


def memory_sync_directive(
    model: "LivingUserModel",
    pattern_mem: Optional["TalkPatternMemory"] = None,
) -> str:
    """Ephemeral inject: what Hermes should persist via the memory tool."""
    candidates = _candidates(model, pattern_mem)
    if not candidates:
        return ""

    lines = [
        "[HERMES MEMORY BRIDGE — production]",
        "Lotus learned these prefs this session. When Hermes `memory` tool is available "
        "AND the chat confirmed them, persist into USER.md (style/prefs) or MEMORY.md "
        "(stable facts). Do not invent. Do not dump the whole list unprompted in chat.",
        "Pending promotions (act on 1–2 that are clearly confirmed):",
    ]
    for c in candidates[:8]:
        lines.append(f"  · {c}")
    return "\n".join(lines)


def write_memory_sync_md(
    model: "LivingUserModel",
    pattern_mem: Optional["TalkPatternMemory"] = None,
) -> Path:
    """Write lotus-core/MEMORY_SYNC.md for operators + Hermes-facing continuity."""
    from lotus.realtime.paths import core_dir

    path = core_dir() / "MEMORY_SYNC.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    candidates = _candidates(model, pattern_mem)
    lines = [
        "# L.O.T.U.S. Memory Sync Candidates",
        "",
        "Stable prefs / facts ready to promote into Hermes `USER.md` / `MEMORY.md`",
        "via the built-in `memory` tool (confirm against conversation — do not invent).",
        "",
        f"Living turns: {getattr(model, 'turn_count', 0)}",
        "",
        "## Pending",
        "",
    ]
    if not candidates:
        lines.append("_No pending promotions._")
    else:
        for c in candidates[:20]:
            lines.append(f"- {c}")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def queue_pattern_promotions(
    model: "LivingUserModel",
    pattern_mem: Optional["TalkPatternMemory"] = None,
) -> None:
    """Push high-confidence pattern prefs into continuity promotions."""
    if pattern_mem is None:
        return
    try:
        from lotus.continuity import get_continuity

        cont = get_continuity()
        if pattern_mem.prefers_short:
            cont.state.queue_promotion("user_preference", "prefers shorter SMS-length replies")
        if pattern_mem.hates_worksheets:
            cont.state.queue_promotion(
                "user_preference", "hates five-step worksheets — talk-through only"
            )
        if pattern_mem.soft_company:
            cont.state.queue_promotion(
                "user_preference", "sometimes wants company over tips"
            )
        if getattr(pattern_mem, "hates_lecture", False):
            cont.state.queue_promotion(
                "user_preference", "hates lectures — no interrogation when refused"
            )
        cont.state.save()
    except Exception:
        pass


def sync_for_production(
    model: "LivingUserModel",
    pattern_mem: Optional["TalkPatternMemory"] = None,
) -> str:
    """Queue promotions + write MEMORY_SYNC.md; return inject directive."""
    queue_pattern_promotions(model, pattern_mem)
    write_memory_sync_md(model, pattern_mem)
    return memory_sync_directive(model, pattern_mem)
