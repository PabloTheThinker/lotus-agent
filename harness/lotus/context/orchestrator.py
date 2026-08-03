"""Unified turn-context orchestrator — one inject, priority + token budget."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

logger = logging.getLogger(__name__)


@dataclass
class ContextBlock:
    key: str
    priority: int  # lower = more important (kept first when trimming)
    text: str
    sticky: bool = False  # never drop entirely (truncate only as last resort)


@dataclass
class MergeResult:
    text: str
    kept: List[str] = field(default_factory=list)
    dropped: List[str] = field(default_factory=list)
    chars: int = 0
    budget: int = 0
    truncated_sticky: bool = False


def _budget_chars() -> int:
    raw = os.environ.get("LOTUS_CONTEXT_BUDGET_CHARS", "12000")
    try:
        return max(2000, int(raw))
    except ValueError:
        return 12000


def _trim_block(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + "\n…[truncated]"


def _env_on(flag: str) -> bool:
    return os.environ.get(flag, "").lower() in {"1", "true", "yes", "on"}


def merge_blocks(
    blocks: Sequence[ContextBlock],
    *,
    budget: Optional[int] = None,
) -> str:
    """Merge by priority; drop lowest-priority non-sticky blocks when over budget."""
    return merge_blocks_detailed(blocks, budget=budget).text


def merge_blocks_detailed(
    blocks: Sequence[ContextBlock],
    *,
    budget: Optional[int] = None,
) -> MergeResult:
    budget = budget if budget is not None else _budget_chars()
    ordered = sorted(
        [b for b in blocks if (b.text or "").strip()],
        key=lambda b: b.priority,
    )
    seen = set()
    unique: List[ContextBlock] = []
    for b in ordered:
        if b.key in seen:
            continue
        seen.add(b.key)
        unique.append(b)

    selected = list(unique)
    dropped: List[str] = []
    truncated_sticky = False
    while True:
        joined = "\n\n".join(b.text.strip() for b in selected)
        if len(joined) <= budget:
            result = MergeResult(
                text=joined,
                kept=[b.key for b in selected],
                dropped=dropped,
                chars=len(joined),
                budget=budget,
                truncated_sticky=truncated_sticky,
            )
            _log_merge(result)
            return result
        drop_idx = None
        for i in range(len(selected) - 1, -1, -1):
            if not selected[i].sticky:
                drop_idx = i
                break
        if drop_idx is None:
            truncated_sticky = True
            text = _trim_block(joined, budget)
            result = MergeResult(
                text=text,
                kept=[b.key for b in selected],
                dropped=dropped,
                chars=len(text),
                budget=budget,
                truncated_sticky=True,
            )
            _log_merge(result)
            return result
        dropped.append(selected[drop_idx].key)
        selected.pop(drop_idx)


def _log_merge(result: MergeResult) -> None:
    if not result.dropped and not result.truncated_sticky and not _env_on("LOTUS_CONTEXT_DEBUG"):
        return
    level = logging.INFO if (result.dropped or result.truncated_sticky) else logging.DEBUG
    logger.log(
        level,
        "lotus.context: chars=%s/%s kept=%s dropped=%s sticky_trunc=%s",
        result.chars,
        result.budget,
        ",".join(result.kept) or "-",
        ",".join(result.dropped) or "-",
        result.truncated_sticky,
    )


def _needs_llm_understand(user_text: str, *, crisis: bool, protocols: List[str], affect: str) -> bool:
    """When LOTUS_LLM_UNDERSTAND is on: enrich crisis + ambiguous turns."""
    if not _env_on("LOTUS_LLM_UNDERSTAND"):
        return False
    if crisis:
        return True
    mode = os.environ.get("LOTUS_LLM_UNDERSTAND_MODE", "crisis_ambiguous").lower()
    if mode in {"always", "all"}:
        return True
    if mode == "crisis":
        return crisis
    # crisis_ambiguous (default): no protocol beyond general, or mixed/low affect with substance
    text = (user_text or "").strip()
    if len(text) < 24:
        return False
    substantive = len(text) >= 40
    vague_protocols = not protocols or protocols == ["P0_general"]
    ambiguous_affect = affect in {"mixed", "low", "neutral", ""}
    return substantive and (vague_protocols or ambiguous_affect)


def build_turn_context(
    user_text: str,
    *,
    history: Optional[Sequence[dict]] = None,
    is_first_turn: bool = False,
    session_id: str = "",
) -> str:
    """Single entrypoint used by lotus-realtime pre_llm_call (and LotusAgent)."""
    from lotus.guardrails import assess_user_text, safety_context_for_user_text
    from lotus.plain_language import looks_medical, plain_language_directive
    from lotus.prefs import maybe_autodetect_lang, resolve_preferred_lang
    from lotus.realtime import get_core
    from lotus.realtime.voice_adapt import (
        build_adaptation_directive,
        extract_voice,
        read_hermes_memory_snippets,
    )
    from lotus.speech import build_speech_care_directive

    core = get_core()
    snap = core.get_or_read_snapshot(user_text, history=history)
    core.model.active_protocols = [p.value for p in snap.protocols]
    core.model.last_user_summary = snap.summary
    core.model.push_affect(snap.affect)
    latest_voice = extract_voice(user_text)
    core.learning._integrate_voice(core.model, latest_voice)
    core.research.sync_queue(core.model, snap)
    try:
        core.research.seed_offline_approaches(core.model)
    except Exception:
        pass
    try:
        maybe_autodetect_lang(user_text)
    except Exception:
        pass

    assessment = assess_user_text(user_text)
    crisis = assessment.inject_crisis_override or snap.affect.valence == "crisis"
    protocols = [p.value for p in snap.protocols]
    affect = snap.affect.valence
    lang = resolve_preferred_lang()

    moment_kinds: List[str] = []
    stall_horizon = ""
    progress_signal = False
    try:
        from lotus.moments import get_moments

        related = get_moments().find_related(user_text, limit=4)
        moment_kinds = [m.kind for m, _ in related]
        for m in get_moments().graph.moments:
            if m.status in {"open", "active"} and m.kind not in moment_kinds:
                moment_kinds.append(m.kind)
            if len(moment_kinds) >= 6:
                break
    except Exception:
        pass
    try:
        from lotus.compound import get_compound

        mission = get_compound().state.active()
        if mission:
            stall_horizon = mission.meter.estimated_horizon
            progress_signal = (
                mission.meter.progress_count > 0 and mission.meter.stall_count == 0
            )
    except Exception:
        pass

    blocks: List[ContextBlock] = []

    if not os_disabled("LOTUS_SAFETY_DISABLE"):
        safety = safety_context_for_user_text(user_text)
        if safety:
            blocks.append(ContextBlock("safety", 0, safety, sticky=True))

    if not os_disabled("LOTUS_REALTIME_DISABLE"):
        blocks.append(ContextBlock("living", 10, core.model.prompt_block(), sticky=True))

    if not os_disabled("LOTUS_PROFILE_DISABLE"):
        try:
            from lotus.profile import get_profile

            blocks.append(
                ContextBlock("profile", 15, get_profile().before_turn(), sticky=False)
            )
        except Exception:
            pass

    if not os_disabled("LOTUS_SPEECH_DISABLE"):
        speech = build_speech_care_directive(
            user_text=user_text,
            moment_kinds=moment_kinds,
            protocols=protocols,
            affect=affect,
            avoided_language=core.model.avoided_language,
            preferred_language=core.model.preferred_language,
            stall_horizon=stall_horizon,
            progress_signal=progress_signal,
            crisis=crisis,
            history=history,
        )
        blocks.append(ContextBlock("speech", 20, speech, sticky=crisis))

    if not os_disabled("LOTUS_REALTIME_DISABLE"):
        memory_bits = read_hermes_memory_snippets()
        adapt = build_adaptation_directive(
            core.model, latest=latest_voice, memory_snippets=memory_bits
        )
        blocks.append(ContextBlock("adaptive", 25, adapt, sticky=False))
        try:
            from lotus.memory_sync import memory_sync_directive
            from lotus.speech.patterns import load_pattern_memory

            bridge = memory_sync_directive(core.model, load_pattern_memory())
            if bridge:
                blocks.append(
                    ContextBlock("memory_bridge", 28, bridge, sticky=False)
                )
        except Exception:
            pass

    if not os_disabled("LOTUS_CONTINUITY_DISABLE"):
        try:
            from lotus.continuity import get_continuity

            cont = get_continuity().before_turn(
                user_text,
                is_first_turn=is_first_turn,
                session_id=session_id,
                living_affect=affect,
                living_protocol=protocols[0] if protocols else "",
            )
            blocks.append(ContextBlock("continuity", 30, cont, sticky=False))
        except Exception:
            pass

    if not os_disabled("LOTUS_COMPOUND_DISABLE"):
        try:
            from lotus.compound import get_compound

            cmp = get_compound().before_turn(
                user_text,
                is_first_turn=is_first_turn,
                crisis=crisis,
                affect=affect,
            )
            blocks.append(ContextBlock("compound", 35, cmp, sticky=False))
        except Exception:
            pass

    if not os_disabled("LOTUS_MOMENTS_DISABLE"):
        try:
            from lotus.moments import get_moments

            mom = get_moments().before_turn(
                user_text,
                is_first_turn=is_first_turn,
                session_id=session_id,
            )
            blocks.append(ContextBlock("moments", 40, mom, sticky=False))
        except Exception:
            pass

    if not os_disabled("LOTUS_REALTIME_DISABLE"):
        needs = (
            "[L.O.T.U.S. UNDERSTANDING SUBROUTINE]\n"
            f"needs: {', '.join(snap.needs)}\n"
            f"live_read: {snap.summary}\n"
            f"preferred_lang: {lang}\n"
            "Respond to the living person in front of you — not a generic script. "
            "Match their language when you can."
        )
        blocks.append(ContextBlock("understanding", 45, needs, sticky=False))
        research = core.research.prompt_directives(core.model)
        if research:
            blocks.append(ContextBlock("research", 50, research, sticky=False))

    # Plain-language bridge only for real medical jargon — not friend-shock hospital news
    _plain_ok = looks_medical(user_text) or "medical_plain_language_bridge" in snap.needs
    if _plain_ok:
        try:
            from lotus.speech.stated_facts import is_third_party_hospital, is_self_health_signal

            if is_third_party_hospital(user_text) and not is_self_health_signal(user_text):
                _plain_ok = False
        except Exception:
            pass
    if _plain_ok:
        blocks.append(
            ContextBlock("plain_language", 55, plain_language_directive(user_text), sticky=False)
        )

    # 56 — Honcho (Hermes memory provider) when active
    if not os_disabled("LOTUS_HONCHO_DISABLE"):
        try:
            from lotus.honcho import honcho_context_block

            honcho = honcho_context_block()
            if honcho:
                blocks.append(ContextBlock("honcho", 56, honcho, sticky=False))
        except Exception:
            pass

    if _env_on("LOTUS_LLM_EXTRACT"):
        blocks.append(
            ContextBlock(
                "llm_extract",
                60,
                (
                    "[L.O.T.U.S. STRUCTURED EXTRACT — optional]\n"
                    "If this turn revealed durable facts (name, mission, supports, avoid-words), "
                    "end your private reasoning with a fenced block:\n"
                    "```lotus-extract\n"
                    '{"preferred_name":"","preferred_lang":"","mission":"",'
                    '"supports":[],"avoid_words":[],"notes":""}\n'
                    "```\n"
                    "Omit the fence if nothing new. Never show this JSON to the user."
                ),
                sticky=False,
            )
        )

    if _needs_llm_understand(
        user_text, crisis=crisis, protocols=protocols, affect=affect
    ):
        blocks.append(
            ContextBlock(
                "llm_understand",
                58,
                (
                    "[L.O.T.U.S. UNDERSTANDING ENRICHMENT — private]\n"
                    "Regex may have missed nuance. In private reasoning only, emit:\n"
                    "```lotus-understand\n"
                    '{"affect":"crisis|low|mixed|rising|calm|neutral","protocols":[],'
                    '"needs":[],"summary":""}\n'
                    "```\n"
                    "Never show this JSON to the user. Never downgrade a clear crisis "
                    "to a calmer affect. Prefer human help language if danger is present."
                ),
                sticky=crisis,
            )
        )

    header = (
        "[L.O.T.U.S. CONTEXT ORCHESTRATOR]\n"
        f"blocks={len([b for b in blocks if b.text.strip()])} "
        f"budget_chars={_budget_chars()} crisis={crisis} lang={lang}"
    )
    merged = merge_blocks_detailed(
        [ContextBlock("header", -1, header, sticky=True), *blocks]
    )

    core.model.save()
    core.research.write_approaches_md(core.model)
    return merged.text


def os_disabled(flag: str) -> bool:
    return os.environ.get(flag, "").lower() in {"1", "true", "yes", "on"}


def parse_and_apply_llm_extract(assistant_text: str) -> bool:
    """Parse ```lotus-extract JSON from assistant output when LOTUS_LLM_EXTRACT is on."""
    import json
    import re

    if not _env_on("LOTUS_LLM_EXTRACT"):
        return False
    m = re.search(r"```lotus-extract\s*(\{.*?\})\s*```", assistant_text or "", re.S)
    if not m:
        return False
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    applied = False
    try:
        from lotus.profile import get_profile

        eng = get_profile()
        name = str(data.get("preferred_name") or "").strip()
        if name and len(name) < 40:
            eng.profile.preferred_name = name
            eng.profile.how_to_address = eng.profile.how_to_address or name
            applied = True
        pref_lang = str(data.get("preferred_lang") or "").strip().lower().split("-")[0]
        if pref_lang:
            from lotus.prefs import VALID_LANGS, update_prefs

            if pref_lang in VALID_LANGS:
                update_prefs(preferred_lang=pref_lang, lang_locked=True)
                applied = True
        mission = str(data.get("mission") or "").strip()
        if mission and len(mission) > 8:
            from lotus.compound import get_compound

            c = get_compound()
            if not c.state.active():
                c.set_mission(mission)
            applied = True
        for s in data.get("supports") or []:
            if isinstance(s, str) and s.strip():
                from lotus.profile.model import _remember

                _remember(eng.profile.supports, s.strip(), limit=16)
                applied = True
        for w in data.get("avoid_words") or []:
            if isinstance(w, str) and w.strip():
                from lotus.realtime import get_core

                get_core().model.remember("avoided_language", w.strip())
                applied = True
        note = str(data.get("notes") or "").strip()
        if note:
            eng.profile.add_note("observation", note[:400])
            applied = True
        if applied:
            eng.profile.save()
    except Exception:
        return False
    return applied


def parse_and_apply_llm_understand(
    assistant_text: str,
    *,
    regex_crisis: bool = False,
) -> bool:
    """Parse ```lotus-understand JSON; never downgrade regex crisis."""
    import json
    import re

    if not _env_on("LOTUS_LLM_UNDERSTAND"):
        return False
    m = re.search(r"```lotus-understand\s*(\{.*?\})\s*```", assistant_text or "", re.S)
    if not m:
        return False
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    try:
        import time

        from lotus.realtime import get_core
        from lotus.realtime.model import AffectSample

        core = get_core()
        affect = str(data.get("affect") or "").strip().lower()
        if affect == "neutral":
            affect = "unknown"
        allowed = {"crisis", "low", "mixed", "rising", "calm", "unknown"}
        if affect in allowed:
            if regex_crisis and affect != "crisis":
                affect = "crisis"
            intensity = 1.0 if affect == "crisis" else 0.6 if affect == "low" else 0.45
            core.model.push_affect(
                AffectSample(ts=time.time(), valence=affect, intensity=intensity)
            )
        protos = data.get("protocols") or []
        if isinstance(protos, list):
            cleaned = [str(p) for p in protos if isinstance(p, str) and p.strip()]
            if cleaned:
                if regex_crisis and "CRISIS" not in cleaned:
                    cleaned.insert(0, "CRISIS")
                core.model.active_protocols = cleaned[:8]
        summary = str(data.get("summary") or "").strip()
        if summary:
            core.model.last_user_summary = summary[:240]
        for need in data.get("needs") or []:
            if isinstance(need, str) and need.strip():
                core.model.remember("open_gaps", need.strip()[:120])
        core.model.save()
        return True
    except Exception:
        logger.exception("lotus.context: llm_understand apply failed")
        return False
