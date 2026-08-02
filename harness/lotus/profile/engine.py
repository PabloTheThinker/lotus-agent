"""ProfileEngine — build a full internal user profile while they talk with L.O.T.U.S."""

from __future__ import annotations

import re
import threading
from typing import Any, List, Optional, Sequence

from .model import InternalProfile, _remember

_LOCK = threading.RLock()
_ENGINE: Optional["ProfileEngine"] = None

_NAME_RE = re.compile(
    r"\b(?:my name is|i(?:'m| am)|call me|please call me)\s+([A-Z][a-z]{1,20})\b"
)
_NAME_RE_I = re.compile(
    r"\b(?:my name is|call me|please call me)\s+([A-Za-z][A-Za-z\-']{1,24})\b",
    re.I,
)
_ROLE_RE = re.compile(
    r"\b(?:i(?:'m| am) (?:a |an )?)(student|teacher|nurse|doctor|engineer|parent|mom|dad|"
    r"father|mother|caregiver|veteran|artist|writer|developer|therapist|retired)\b",
    re.I,
)
_STRESS_RE = re.compile(
    r"\b(?:stressed about|stress(?:ed|ing)? (?:about|from|over)|worried about|"
    r"overwhelmed by|struggling with|dealing with)\s+(.{3,80})(?:[.!]|$)",
    re.I,
)
_SUPPORT_RE = re.compile(
    r"\b(?:my (?:friend|partner|spouse|wife|husband|mom|dad|therapist|sister|brother|"
    r"kids?|dog|cat)|i talk to|i lean on)\b[^.!?]{0,40}",
    re.I,
)
_SLEEP_RE = re.compile(
    r"\b(?:can'?t sleep|insomni\w*|struggling with sleep|sleep(?:ing)? (?:bad|poor|well|better)|"
    r"exhausted|up all night|nightmares?|sleep (?:is |has been )?(?:hard|rough|awful))\b[^.!?]{0,40}",
    re.I,
)
_CONCERN_RE = re.compile(
    r"\b(?:i(?:'ve| have) been|i feel|i(?:'m| am)|the hardest part is|what hurts is)\s+(.{5,100})",
    re.I,
)


class ProfileEngine:
    """Compounds a professional-level internal profile across conversations."""

    def __init__(self) -> None:
        self.profile = InternalProfile.load()

    def reload(self) -> InternalProfile:
        with _LOCK:
            self.profile = InternalProfile.load()
            return self.profile

    def before_turn(self) -> str:
        with _LOCK:
            return self.profile.prompt_block()

    def after_turn(
        self,
        user_text: str,
        assistant_text: str = "",
        *,
        living_model: object = None,
        protocols: Optional[Sequence[str]] = None,
        affect: str = "",
        crisis: bool = False,
    ) -> InternalProfile:
        with _LOCK:
            self.profile.turn_count += 1
            self.profile.current_affect = affect or self.profile.current_affect
            if protocols:
                self.profile.active_protocols = list(protocols)

            self._extract_identity(user_text)
            self._extract_context(user_text)
            self._merge_living(living_model)
            self._merge_journey()
            self._merge_moments()
            self._update_formulation(user_text, crisis=crisis)
            self._write_lotus_notes(user_text, assistant_text, crisis=crisis)
            self._queue_memory_candidates()

            self.profile.save()
            return self.profile

    # --- extractors --------------------------------------------------------

    def _extract_identity(self, text: str) -> None:
        m = _NAME_RE.search(text or "") or _NAME_RE_I.search(text or "")
        if m:
            name = m.group(1).strip().title()
            if name.lower() not in {"a", "the", "just", "still", "very", "so", "not"}:
                self.profile.preferred_name = name
                if not self.profile.how_to_address:
                    self.profile.how_to_address = name
                _remember(self.profile.memory_candidates, f"Preferred name: {name}", limit=30)
        for rm in _ROLE_RE.finditer(text or ""):
            _remember(self.profile.roles, rm.group(1).lower(), limit=12)

    def _extract_context(self, text: str) -> None:
        for m in _STRESS_RE.finditer(text or ""):
            _remember(self.profile.stressors, m.group(0).strip()[:120], limit=20)
        for m in _SUPPORT_RE.finditer(text or ""):
            frag = " ".join(m.group(0).split())[:100]
            _remember(self.profile.supports, frag, limit=16)
            _remember(self.profile.people_and_anchors, frag, limit=20)
        for m in _SLEEP_RE.finditer(text or ""):
            _remember(self.profile.body_sleep_notes, " ".join(m.group(0).split())[:100], limit=12)
        # Presenting concerns from weighty first-person lines
        if len((text or "").split()) >= 6:
            cm = _CONCERN_RE.search(text or "")
            if cm:
                _remember(self.profile.presenting_concerns, " ".join(text.split())[:140], limit=20)

    def _merge_living(self, living_model: Any = None) -> None:
        if living_model is None:
            try:
                from lotus.realtime.model import LivingUserModel

                living_model = LivingUserModel.load()
            except Exception:
                return
        mapping = [
            ("strengths", "strengths"),
            ("grounding_tools_that_work", "coping_that_helps"),
            ("failed_moves", "coping_that_harms"),
            ("triggers", "stressors"),
            ("preferred_language", "language_helps"),
            ("avoided_language", "language_harms"),
            ("user_metaphors", "metaphors"),
            ("connection_anchors", "people_and_anchors"),
            ("open_gaps", "open_questions"),
            ("hypotheses", "working_hypotheses"),
            ("successful_moves", "coping_that_helps"),
            ("relatability_notes", "alliance_notes"),
        ]
        for src, dest in mapping:
            values = getattr(living_model, src, None) or []
            bucket = getattr(self.profile, dest)
            for v in list(values)[-8:]:
                _remember(bucket, str(v), limit=24)
        affect = getattr(living_model, "current_affect", None)
        if affect:
            self.profile.current_affect = str(affect)
        protos = getattr(living_model, "active_protocols", None) or []
        if protos:
            self.profile.active_protocols = list(protos)

    def _merge_journey(self) -> None:
        try:
            from lotus.compound import get_compound

            mission = get_compound().state.active()
            if not mission:
                return
            self.profile.active_mission = mission.statement
            self.profile.mission_horizon = mission.meter.estimated_horizon
            self.profile.center_checkpoint_met = mission.meter.center_met
            if mission.why:
                _remember(self.profile.presenting_concerns, f"Mission why: {mission.why}", limit=20)
        except Exception:
            return

    def _merge_moments(self) -> None:
        try:
            from lotus.moments import get_moments

            open_m = [
                m
                for m in get_moments().graph.moments
                if m.status in {"open", "active"}
            ][-8:]
            self.profile.open_moments = [f"{m.kind}: {m.title}"[:100] for m in open_m]
            for m in open_m:
                if m.kind in {"grief", "health", "life_event"}:
                    _remember(self.profile.presenting_concerns, m.summary[:140], limit=20)
                    _remember(self.profile.what_not_to_miss, f"{m.kind}: {m.title}"[:120], limit=16)
        except Exception:
            return

    def _update_formulation(self, user_text: str, *, crisis: bool) -> None:
        """Keep a short working formulation current — professional tone, no diagnosis."""
        who = self.profile.preferred_name or "The person"
        parts: List[str] = [who]
        if self.profile.presenting_concerns:
            parts.append("is carrying " + self.profile.presenting_concerns[-1][:100])
        if self.profile.active_protocols:
            parts.append("(" + ", ".join(self.profile.active_protocols[:3]) + ")")
        if self.profile.active_mission:
            parts.append(f"— mission: «{self.profile.active_mission[:80]}»")
            parts.append(f"[horizon={self.profile.mission_horizon or 'unknown'}]")
        if self.profile.strengths:
            parts.append("; strengths include " + self.profile.strengths[-1][:60])
        if self.profile.supports:
            parts.append("; supports include " + self.profile.supports[-1][:60])
        if crisis:
            parts.append("; CRISIS override — safety first")
        formulation = " ".join(parts).strip() + "."
        if len(formulation) > 15:
            self.profile.formulation = formulation[:600]

        # Hypotheses from protocols
        hypo_map = {
            "P1_depression": "Low energy/numbness may respond better to micro-activation than insight dumps.",
            "P3_grief": "Grief waves may need presence more than problem-solving.",
            "P2_health": "Health fear may ease with plain language + clinician-ready questions.",
            "P4_major_event": "Acute life change — protect against chaotic big decisions while flooded.",
        }
        for p in self.profile.active_protocols:
            if p in hypo_map:
                _remember(self.profile.working_hypotheses, hypo_map[p], limit=12)

        if not self.profile.center_checkpoint_met and self.profile.active_mission:
            _remember(
                self.profile.what_not_to_miss,
                "Center safety checkpoint not yet met — keep guidance near Safety/Body.",
                limit=16,
            )

    def _write_lotus_notes(
        self,
        user_text: str,
        assistant_text: str,
        *,
        crisis: bool,
    ) -> None:
        """Append a concise private note most turns (deduped)."""
        if not (user_text or "").strip():
            return
        # Don't spam identical notes
        snippet = " ".join(user_text.split())[:160]
        if self.profile.lotus_notes:
            last = self.profile.lotus_notes[-1].get("source_turn", "")
            if last and last[:80] == snippet[:80]:
                return

        kind = "session"
        body_parts = [f"User: {snippet}"]
        if crisis:
            kind = "risk"
            body_parts.append("Note: crisis markers — prioritized safety resources; no method exploration.")
            _remember(self.profile.risk_flags, "crisis_markers_this_turn", limit=8)
        elif self.profile.active_protocols:
            body_parts.append("Protocols: " + ", ".join(self.profile.active_protocols[:3]))
        if self.profile.current_affect:
            body_parts.append(f"Affect: {self.profile.current_affect}")
        if assistant_text:
            body_parts.append("Lotus move: " + " ".join(assistant_text.split())[:120])

        # Periodic formulation note
        if self.profile.turn_count % 5 == 0 and self.profile.formulation:
            self.profile.add_note(
                "formulation",
                self.profile.formulation,
                source_turn=snippet,
            )

        self.profile.add_note(kind, " | ".join(body_parts), source_turn=snippet)

        # Alliance note when they correct language or thank
        if re.search(r"\b(thank|helped|grateful)\b", user_text or "", re.I):
            self.profile.add_note(
                "alliance",
                "Positive alliance signal — something landed; keep that tone/move family.",
                source_turn=snippet,
            )
        if re.search(r"\b(don'?t say|too much|stop pushing)\b", user_text or "", re.I):
            self.profile.add_note(
                "alliance",
                "Repair cue — adjust language/pace; record avoidances.",
                source_turn=snippet,
            )

    def _queue_memory_candidates(self) -> None:
        if self.profile.preferred_name:
            _remember(
                self.profile.memory_candidates,
                f"Preferred name: {self.profile.preferred_name}",
                limit=30,
            )
        if self.profile.active_mission:
            _remember(
                self.profile.memory_candidates,
                f"Long-term mission: {self.profile.active_mission[:160]}",
                limit=30,
            )


def get_profile() -> ProfileEngine:
    global _ENGINE
    with _LOCK:
        if _ENGINE is None:
            _ENGINE = ProfileEngine()
        return _ENGINE


def reset_profile() -> ProfileEngine:
    global _ENGINE
    with _LOCK:
        _ENGINE = ProfileEngine()
        return _ENGINE
