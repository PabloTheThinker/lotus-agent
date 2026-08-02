"""Internal professional-grade user profile + Lotus private notes.

Companion chart — not a clinical record, not a diagnosis. Structured so L.O.T.U.S.
can hold a full understanding of the person across conversations.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import lotus_notes_path, profile_json_path, profile_md_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _remember(seq: List[str], value: str, *, limit: int = 24) -> None:
    value = " ".join((value or "").split()).strip()
    if not value or len(value) < 2:
        return
    if value in seq:
        seq.remove(value)
    seq.append(value)
    if len(seq) > limit:
        del seq[: len(seq) - limit]


@dataclass
class LotusNote:
    """Private working note for L.O.T.U.S. (not shown as a dump to the user)."""

    id: str
    ts: str
    kind: str  # session | formulation | hypothesis | risk | alliance | plan | observation
    body: str
    source_turn: str = ""

    @classmethod
    def create(cls, kind: str, body: str, *, source_turn: str = "") -> "LotusNote":
        import uuid

        return cls(
            id=f"n_{uuid.uuid4().hex[:8]}",
            ts=_now(),
            kind=kind,
            body=" ".join(body.split())[:500],
            source_turn=" ".join((source_turn or "").split())[:120],
        )


@dataclass
class InternalProfile:
    """Full-blown internal understanding of the user."""

    version: int = 1
    updated_at: str = ""
    turn_count: int = 0
    confidence: str = "emerging"  # emerging | developing | strong

    # Identity (only what they shared)
    preferred_name: str = ""
    roles: List[str] = field(default_factory=list)  # parent, student, nurse…
    how_to_address: str = ""

    # Presentation
    presenting_concerns: List[str] = field(default_factory=list)
    current_affect: str = "unknown"
    active_protocols: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)  # never detailed methods

    # Context (biopsychosocial-lite — companion framing)
    stressors: List[str] = field(default_factory=list)
    supports: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    coping_that_helps: List[str] = field(default_factory=list)
    coping_that_harms: List[str] = field(default_factory=list)
    body_sleep_notes: List[str] = field(default_factory=list)

    # Relational / anchors
    people_and_anchors: List[str] = field(default_factory=list)

    # Language & alliance
    language_helps: List[str] = field(default_factory=list)
    language_harms: List[str] = field(default_factory=list)
    metaphors: List[str] = field(default_factory=list)
    alliance_notes: List[str] = field(default_factory=list)

    # Journey
    active_mission: str = ""
    mission_horizon: str = ""
    center_checkpoint_met: bool = False
    open_moments: List[str] = field(default_factory=list)

    # Professional understanding (Lotus formulation — not a diagnosis)
    formulation: str = ""
    working_hypotheses: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    what_not_to_miss: List[str] = field(default_factory=list)

    # Lotus private notes (append-only, capped)
    lotus_notes: List[Dict[str, Any]] = field(default_factory=list)

    # Sync candidates for Hermes USER.md (never auto-written)
    memory_candidates: List[str] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = _now()
        if self.turn_count >= 30 and (
            self.preferred_name or self.presenting_concerns or self.formulation
        ):
            self.confidence = "strong"
        elif self.turn_count >= 8 or self.presenting_concerns:
            self.confidence = "developing"
        else:
            self.confidence = "emerging"

    def add_note(self, kind: str, body: str, *, source_turn: str = "") -> None:
        note = LotusNote.create(kind, body, source_turn=source_turn)
        self.lotus_notes.append(asdict(note))
        self.lotus_notes = self.lotus_notes[-80:]
        self.touch()

    def prompt_block(self) -> str:
        """Compact professional chart injected every turn."""
        lines = [
            "[L.O.T.U.S. INTERNAL PROFILE — professional understanding]",
            f"confidence={self.confidence} turns={self.turn_count}",
            "This is a companion working chart — not a medical record, not a diagnosis.",
            "Use it to stay continuous and precise. Do not recite the chart at the user.",
        ]
        if self.preferred_name or self.how_to_address:
            bits = []
            if self.preferred_name:
                bits.append(f"name={self.preferred_name}")
            if self.how_to_address:
                bits.append(f"address_as={self.how_to_address}")
            lines.append("identity: " + "; ".join(bits))
        if self.roles:
            lines.append("roles: " + "; ".join(self.roles[-8:]))
        if self.presenting_concerns:
            lines.append("presenting: " + "; ".join(self.presenting_concerns[-8:]))
        lines.append(
            f"affect={self.current_affect} protocols={', '.join(self.active_protocols) or '—'}"
        )
        if self.risk_flags:
            lines.append("risk_flags: " + "; ".join(self.risk_flags[-4:]))
        if self.stressors:
            lines.append("stressors: " + "; ".join(self.stressors[-8:]))
        if self.supports:
            lines.append("supports: " + "; ".join(self.supports[-6:]))
        if self.strengths:
            lines.append("strengths: " + "; ".join(self.strengths[-6:]))
        if self.coping_that_helps:
            lines.append("coping_helps: " + "; ".join(self.coping_that_helps[-6:]))
        if self.coping_that_harms:
            lines.append("coping_harms: " + "; ".join(self.coping_that_harms[-4:]))
        if self.people_and_anchors:
            lines.append("anchors: " + "; ".join(self.people_and_anchors[-8:]))
        if self.language_helps:
            lines.append("language_helps: " + "; ".join(self.language_helps[-6:]))
        if self.language_harms:
            lines.append("language_harms: " + "; ".join(self.language_harms[-6:]))
        if self.active_mission:
            lines.append(
                f"mission: {self.active_mission} · horizon={self.mission_horizon or '?'} · "
                f"center_met={self.center_checkpoint_met}"
            )
        if self.open_moments:
            lines.append("open_moments: " + "; ".join(self.open_moments[-5:]))
        if self.formulation:
            lines.append(f"formulation: {self.formulation}")
        if self.working_hypotheses:
            lines.append("hypotheses: " + "; ".join(self.working_hypotheses[-5:]))
        if self.open_questions:
            lines.append("open_questions: " + "; ".join(self.open_questions[-5:]))
        if self.what_not_to_miss:
            lines.append("do_not_miss: " + "; ".join(self.what_not_to_miss[-5:]))
        recent_notes = self.lotus_notes[-3:]
        if recent_notes:
            lines.append("lotus_private_notes (latest):")
            for n in recent_notes:
                lines.append(f"  - [{n.get('kind')}] {n.get('body', '')[:160]}")
        if self.memory_candidates:
            lines.append(
                f"memory_candidates={len(self.memory_candidates)} "
                "(promote stable facts to USER.md via memory tool when confirmed)"
            )
        lines.append(
            "Duty: deepen this profile every turn; keep notes honest; never invent biography."
        )
        return "\n".join(lines)

    def save(self, path: Optional[Path] = None) -> None:
        from lotus.schema import stamp

        self.touch()
        path = path or profile_json_path()
        path.write_text(
            json.dumps(stamp(asdict(self), kind="profile"), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self._write_profile_md()
        self._write_lotus_notes_md()

    def _write_profile_md(self) -> None:
        lines = [
            "# L.O.T.U.S. Internal User Profile",
            "",
            f"_Companion working chart · confidence `{self.confidence}` · turns {self.turn_count}_",
            "",
            "> Not a clinical record. Not a diagnosis. For L.O.T.U.S. continuity only.",
            "",
            "## Identity",
            f"- Preferred name: {self.preferred_name or '—'}",
            f"- Address as: {self.how_to_address or '—'}",
            f"- Roles: {', '.join(self.roles) or '—'}",
            "",
            "## Presentation",
            f"- Affect: **{self.current_affect}**",
            f"- Protocols: {', '.join(self.active_protocols) or '—'}",
            "- Concerns:",
            *([f"  - {c}" for c in self.presenting_concerns[-12:]] or ["  - (learning…)"]),
            "",
            "## Stressors & supports",
            "### Stressors",
            *([f"- {x}" for x in self.stressors[-12:]] or ["- (none yet)"]),
            "### Supports",
            *([f"- {x}" for x in self.supports[-10:]] or ["- (none yet)"]),
            "### Strengths",
            *([f"- {x}" for x in self.strengths[-10:]] or ["- (learning…)"]),
            "",
            "## Coping",
            "### Helps",
            *([f"- {x}" for x in self.coping_that_helps[-10:]] or ["- (learning…)"]),
            "### Harms / avoid",
            *([f"- {x}" for x in self.coping_that_harms[-8:]] or ["- (none)"]),
            "",
            "## Language alliance",
            f"- Helps: {'; '.join(self.language_helps[-8:]) or '—'}",
            f"- Harms: {'; '.join(self.language_harms[-8:]) or '—'}",
            f"- Metaphors: {'; '.join(self.metaphors[-8:]) or '—'}",
            "",
            "## Journey",
            f"- Mission: {self.active_mission or '—'}",
            f"- Horizon: {self.mission_horizon or '—'}",
            f"- Center met: {self.center_checkpoint_met}",
            f"- Open moments: {'; '.join(self.open_moments[-6:]) or '—'}",
            "",
            "## Formulation (Lotus understanding)",
            self.formulation or "_(still forming)_",
            "",
            "## Working hypotheses",
            *([f"- {h}" for h in self.working_hypotheses[-10:]] or ["- (none)"]),
            "",
            "## Open questions",
            *([f"- {q}" for q in self.open_questions[-10:]] or ["- (none)"]),
            "",
            "## Do not miss",
            *([f"- {x}" for x in self.what_not_to_miss[-10:]] or ["- (none)"]),
            "",
        ]
        profile_md_path().write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_lotus_notes_md(self) -> None:
        lines = [
            "# L.O.T.U.S. Private Notes",
            "",
            "Internal session / formulation notes. Do not dump at the user.",
            "",
        ]
        if not self.lotus_notes:
            lines.append("_No notes yet._")
        else:
            for n in self.lotus_notes[-40:][::-1]:
                lines.append(f"### {n.get('ts', '')} · {n.get('kind', 'note')}")
                lines.append(n.get("body", ""))
                if n.get("source_turn"):
                    lines.append(f"_from:_ {n['source_turn']}")
                lines.append("")
        lotus_notes_path().write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "InternalProfile":
        path = path or profile_json_path()
        if not path.is_file():
            return cls()
        try:
            from lotus.schema import ensure_schema

            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        raw = ensure_schema(raw, kind="profile")
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in raw.items() if k in known})
