"""Compounding long-term user mission, checkpoints, and journey meter."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .paths import compound_json_path, compound_md_path

LADDER = ("safety", "body", "contact", "horizon", "structure", "meaning")

MISSION_STATUSES = ("draft", "active", "paused", "completed", "archived")
CHECKPOINT_STATUSES = ("upcoming", "center", "offered", "met", "stalled", "skipped")
RECORD_KINDS = (
    "mission_set",
    "mission_refined",
    "center_met",
    "progress",
    "stall",
    "journey_extended",
    "crisis_pause",
    "completed",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class Checkpoint:
    id: str
    title: str
    ladder_rung: str = "safety"
    status: str = "upcoming"  # upcoming | center | offered | met | stalled | skipped
    is_center: bool = False
    order: int = 0
    notes: str = ""
    evidence: List[str] = field(default_factory=list)
    offered_at: str = ""
    met_at: str = ""
    stall_count: int = 0

    @classmethod
    def create(
        cls,
        title: str,
        *,
        ladder_rung: str = "safety",
        order: int = 0,
        is_center: bool = False,
        status: str = "upcoming",
    ) -> "Checkpoint":
        rung = ladder_rung if ladder_rung in LADDER else "safety"
        return cls(
            id=_id("cp"),
            title=" ".join(title.split())[:140],
            ladder_rung=rung,
            status="center" if is_center else status,
            is_center=is_center,
            order=order,
        )


@dataclass
class JourneyMeter:
    """How far the shared journey has compounded toward the mission."""

    checkpoints_total: int = 0
    checkpoints_met: int = 0
    center_met: bool = False
    compound_score: float = 0.0  # 0..1 internal
    stall_count: int = 0
    progress_count: int = 0
    estimated_horizon: str = "unknown"  # near | steady | longer | much_longer
    last_progress_at: str = ""
    last_stall_at: str = ""
    guidance_unlocked: bool = False  # True only after center checkpoint is met

    def recompute(self, checkpoints: Sequence[Checkpoint]) -> None:
        total = len(checkpoints) or 1
        met = sum(1 for c in checkpoints if c.status == "met")
        self.checkpoints_total = len(checkpoints)
        self.checkpoints_met = met
        self.center_met = any(c.is_center and c.status == "met" for c in checkpoints)
        # Compound: met ratio + progress events, penalized by stalls
        base = met / total
        boost = min(0.25, self.progress_count * 0.04)
        penalty = min(0.45, self.stall_count * 0.06)
        self.compound_score = max(0.0, min(1.0, base + boost - penalty))
        self.guidance_unlocked = self.center_met and self.compound_score >= 0.15
        if self.stall_count >= 5 or (self.stall_count >= 3 and met == 0):
            self.estimated_horizon = "much_longer"
        elif self.stall_count >= 2 or self.compound_score < 0.25:
            self.estimated_horizon = "longer"
        elif self.compound_score >= 0.65:
            self.estimated_horizon = "near"
        else:
            self.estimated_horizon = "steady"


@dataclass
class ProgressRecord:
    id: str
    kind: str
    ts: str
    summary: str
    checkpoint_id: str = ""
    evidence: str = ""
    affect: str = ""
    protocol: str = ""

    @classmethod
    def create(
        cls,
        kind: str,
        summary: str,
        *,
        checkpoint_id: str = "",
        evidence: str = "",
        affect: str = "",
        protocol: str = "",
    ) -> "ProgressRecord":
        return cls(
            id=_id("pr"),
            kind=kind if kind in RECORD_KINDS else "progress",
            ts=_now(),
            summary=" ".join(summary.split())[:240],
            checkpoint_id=checkpoint_id,
            evidence=(evidence or "")[:160],
            affect=affect or "",
            protocol=protocol or "",
        )


@dataclass
class UserMission:
    id: str
    statement: str
    why: str = ""
    status: str = "draft"
    consent: str = "implicit"  # implicit | explicit — meter shown gently only if explicit or asked
    created_at: str = ""
    updated_at: str = ""
    protocol_tags: List[str] = field(default_factory=list)
    current_ladder_rung: str = "safety"
    linked_moment_ids: List[str] = field(default_factory=list)
    understanding_notes: List[str] = field(default_factory=list)
    checkpoints: List[Checkpoint] = field(default_factory=list)
    meter: JourneyMeter = field(default_factory=JourneyMeter)

    @classmethod
    def create(
        cls,
        statement: str,
        *,
        why: str = "",
        protocols: Optional[Sequence[str]] = None,
        consent: str = "implicit",
    ) -> "UserMission":
        ts = _now()
        mission = cls(
            id=_id("ms"),
            statement=" ".join(statement.split())[:280],
            why=" ".join((why or "").split())[:280],
            status="active",
            consent=consent if consent in {"implicit", "explicit"} else "implicit",
            created_at=ts,
            updated_at=ts,
            protocol_tags=list(protocols or []),
            current_ladder_rung="safety",
        )
        mission.seed_default_checkpoints()
        mission.meter.recompute(mission.checkpoints)
        return mission

    def seed_default_checkpoints(self) -> None:
        """Center = Safety rung — must be met before long-horizon guidance compounds."""
        if self.checkpoints:
            return
        # Center stays Safety (gate). Early *offered* steps lean Body/Contact so
        # rebuild missions don't open with crisis-line homework in conversation.
        seeds = [
            ("Know help is reachable if things get sharp (quiet gate)", "safety", True),
            ("One body steadiness micro-step tied to this mission", "body", False),
            ("One warm contact or safe space (person, pet, place)", "contact", False),
            ("Name a near-horizon hope tied to this mission", "horizon", False),
            ("Tiny structure that supports the mission", "structure", False),
            ("Meaning / values thread (only when steady)", "meaning", False),
        ]
        for i, (title, rung, center) in enumerate(seeds):
            self.checkpoints.append(
                Checkpoint.create(title, ladder_rung=rung, order=i, is_center=center)
            )
        # Mark center as the active gate
        for cp in self.checkpoints:
            if cp.is_center:
                cp.status = "center"
                break

    def center_checkpoint(self) -> Optional[Checkpoint]:
        for cp in self.checkpoints:
            if cp.is_center:
                return cp
        return self.checkpoints[0] if self.checkpoints else None

    def touch(self) -> None:
        self.updated_at = _now()
        self.meter.recompute(self.checkpoints)


@dataclass
class CompoundState:
    version: int = 1
    updated_at: str = ""
    active_mission_id: str = ""
    missions: List[UserMission] = field(default_factory=list)
    records: List[ProgressRecord] = field(default_factory=list)

    def active(self) -> Optional[UserMission]:
        if self.active_mission_id:
            for m in self.missions:
                if m.id == self.active_mission_id:
                    return m
        for m in self.missions:
            if m.status == "active":
                return m
        return None

    def save(self, path: Optional[Path] = None) -> None:
        from lotus.schema import stamp

        self.updated_at = _now()
        path = path or compound_json_path()
        payload = stamp(
            {
                "version": self.version,
                "updated_at": self.updated_at,
                "active_mission_id": self.active_mission_id,
                "missions": [_mission_dict(m) for m in self.missions[-20:]],
                "records": [asdict(r) for r in self.records[-120:]],
            },
            kind="compound",
        )
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self._write_md()

    def _write_md(self) -> None:
        lines = [
            "# L.O.T.U.S. Compound Journey",
            "",
            "Long-term mission understood from the user over time. "
            "The **center checkpoint** gates deeper guidance. "
            "When progress compounds, the meter moves forward; when it stalls, "
            "the journey is recorded as longer — without shame.",
            "",
        ]
        mission = self.active()
        if not mission:
            lines.append("_No active user mission yet — listen for what they want to rebuild toward._")
        else:
            meter = mission.meter
            lines.append("## Active mission")
            lines.append(f"**{mission.statement}**")
            if mission.why:
                lines.append(f"_Why:_ {mission.why}")
            lines.append("")
            lines.append(f"- Status: `{mission.status}` · Ladder rung: `{mission.current_ladder_rung}`")
            lines.append(
                f"- Meter: {meter.checkpoints_met}/{meter.checkpoints_total} checkpoints · "
                f"score={meter.compound_score:.2f} · horizon=`{meter.estimated_horizon}`"
            )
            lines.append(
                f"- Center met: {'yes' if meter.center_met else 'no'} · "
                f"Guidance unlocked: {'yes' if meter.guidance_unlocked else 'not yet'}"
            )
            lines.append("")
            lines.append("### Checkpoints")
            for cp in mission.checkpoints:
                mark = "◆" if cp.is_center else "•"
                lines.append(
                    f"- {mark} **{cp.title}** (`{cp.ladder_rung}` / {cp.status})"
                    + (f" — stalls:{cp.stall_count}" if cp.stall_count else "")
                )
        if self.records:
            lines.extend(["", "## Recent journey log"])
            for r in self.records[-12:][::-1]:
                lines.append(f"- [{r.kind}] {r.summary}")
        compound_md_path().write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CompoundState":
        path = path or compound_json_path()
        if not path.is_file():
            return cls()
        try:
            from lotus.schema import ensure_schema

            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        raw = ensure_schema(raw, kind="compound")
        missions = [_mission_from_dict(m) for m in raw.get("missions") or [] if isinstance(m, dict)]
        records = [ProgressRecord(**r) for r in raw.get("records") or [] if isinstance(r, dict)]
        return cls(
            version=int(raw.get("version") or 1),
            updated_at=str(raw.get("updated_at") or ""),
            active_mission_id=str(raw.get("active_mission_id") or ""),
            missions=missions,
            records=records,
        )


def _mission_dict(m: UserMission) -> Dict:
    d = asdict(m)
    return d


def _mission_from_dict(raw: Dict) -> UserMission:
    cps = [Checkpoint(**c) for c in raw.get("checkpoints") or [] if isinstance(c, dict)]
    meter_raw = raw.get("meter") or {}
    meter = JourneyMeter(**{k: v for k, v in meter_raw.items() if k in JourneyMeter.__dataclass_fields__})
    fields = {k: v for k, v in raw.items() if k in UserMission.__dataclass_fields__ and k not in {"checkpoints", "meter"}}
    mission = UserMission(**fields, checkpoints=cps, meter=meter)
    mission.meter.recompute(mission.checkpoints)
    return mission
