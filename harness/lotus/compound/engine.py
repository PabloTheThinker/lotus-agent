"""CompoundEngine — grow a long-term user mission with gated checkpoints + meter."""

from __future__ import annotations

import re
import threading
from typing import List, Optional, Sequence

from .model import (
    LADDER,
    CompoundState,
    ProgressRecord,
    UserMission,
    _now,
)

_LOCK = threading.RLock()
_ENGINE: Optional["CompoundEngine"] = None

# User articulating a longer arc
_MISSION_RE = re.compile(
    r"\b(?:i (?:want|need|hope|wish) to|my (?:goal|mission|hope|dream) is(?: to)?|"
    r"what i (?:really )?want(?:\s+(?:over|for|in)\s+[^.]{0,40})?\s+is(?: to)?|"
    r"i(?:'m| am) trying to|help me (?:to )?(?:get|rebuild|recover|heal|find|become)|"
    r"i want my life to|someday i (?:want|hope)|the point is to|"
    r"rebuild a life|feel steady enough)\b(.{0,160})",
    re.I,
)

_WHY_RE = re.compile(
    r"\b(?:because|so that|so i can|for my|for the sake of)\b(.{5,120})",
    re.I,
)

_PROGRESS_RE = re.compile(
    r"\b(?:i did|i (?:managed|was able) to|that helped|i feel (?:better|lighter|steadier)|"
    r"small win|i took a step|got through|i showed up|kept going|"
    r"made it (?:through|to)|better than (?:yesterday|before))\b",
    re.I,
)

_STALL_RE = re.compile(
    r"\b(?:couldn'?t|can'?t|failed|gave up|back to square|still stuck|no progress|"
    r"worse|relapsed|didn'?t (?:do|manage|make)|too hard|not ready|"
    r"same place|going nowhere|taking forever|never going to)\b",
    re.I,
)

_EXPLICIT_METER_RE = re.compile(
    r"\b(?:how (?:am i|are we) doing|progress|meter|checkpoint|how far|"
    r"track (?:this|my)|show me (?:the )?(?:mission|journey|progress))\b",
    re.I,
)

_CENTER_MET_RE = re.compile(
    r"\b(?:i(?:'m| am) safe|not going to hurt|reached out|called (?:a friend|for help)|"
    r"stayed|i asked for help|i(?:'m| am) not alone|got through the night|"
    r"crisis (?:passed|eased)|i can stay here)\b",
    re.I,
)


class CompoundEngine:
    """Compounds conversation + understanding into a long-term user mission."""

    def __init__(self) -> None:
        self.state = CompoundState.load()

    def reload(self) -> CompoundState:
        with _LOCK:
            self.state = CompoundState.load()
            return self.state

    def before_turn(
        self,
        user_text: str,
        *,
        is_first_turn: bool = False,
        crisis: bool = False,
        affect: str = "",
    ) -> str:
        """Ephemeral compound-mission context for pre_llm_call."""
        with _LOCK:
            mission = self.state.active()
            lines = [
                "[L.O.T.U.S. COMPOUND — long-term mission journey]",
                "Grow understanding of *their* mission over time. Compound progress only when real.",
                "Center checkpoint gates deeper guidance. Never pressure. Never shame stalls.",
            ]

            if crisis or affect == "crisis":
                lines.append(
                    "CRISIS ACTIVE — pause mission/meter guidance. Safety only. "
                    "Do not mention checkpoints or horizons until they are steadier."
                )
                if mission and mission.status == "active":
                    lines.append(f"(Mission held quietly: {mission.statement[:120]})")
                return "\n".join(lines)

            if not mission:
                lines.append(
                    "No active user mission yet. Listen for what they want to rebuild toward. "
                    "When they name a goal, reflect it gently and begin the compound journey."
                )
                return "\n".join(lines)

            meter = mission.meter
            center = mission.center_checkpoint()
            lines.append(f"Active mission: {mission.statement}")
            if mission.why:
                lines.append(f"Why (their words/values): {mission.why}")
            lines.append(f"Ladder focus: {mission.current_ladder_rung}")
            if center:
                lines.append(
                    f"Center checkpoint ({center.status}): {center.title} "
                    "— must be met before unlocking longer-horizon guidance."
                )
            lines.append(
                f"Meter: {meter.checkpoints_met}/{meter.checkpoints_total} met · "
                f"compound={meter.compound_score:.2f} · journey_horizon={meter.estimated_horizon} · "
                f"stalls={meter.stall_count} · progress_events={meter.progress_count}"
            )

            if not meter.center_met:
                lines.append(
                    "GUIDANCE MODE: center not met — hold Safety quietly as the gate. "
                    "When they ask for a small checkpoint, prefer Body/Contact micro-steps "
                    "tied to their mission (water, light, 2-minute steadiness, pet, one warm "
                    "text). Do NOT lead with crisis-line homework unless affect is crisis or "
                    "they ask about safety. Tiny collaborative steps only — no meaning leaps."
                )
            elif meter.guidance_unlocked:
                lines.append(
                    "GUIDANCE MODE: center met — you may gently guide the next checkpoint "
                    "toward their mission. Still one small step. Celebrate quietly."
                )
            else:
                lines.append(
                    "GUIDANCE MODE: center met but compound still thin — keep consolidating, "
                    "then offer the next rung when they have energy."
                )

            if meter.estimated_horizon in {"longer", "much_longer"}:
                lines.append(
                    f"JOURNEY SIGNAL: horizon is `{meter.estimated_horizon}`. "
                    "Be honest with yourself and, if they ask or consent, with them: "
                    "this mission may take longer — that is data, not failure. Shrink the next step."
                )
                # Surface recent stall records for the agent
                stalls = [r for r in self.state.records if r.kind in {"stall", "journey_extended"}][-3:]
                for r in stalls:
                    lines.append(f"  · logged: {r.summary}")

            show_meter = (
                mission.consent == "explicit"
                or bool(_EXPLICIT_METER_RE.search(user_text or ""))
            )
            if show_meter:
                lines.append(
                    "USER ASKED / CONSENTED FOR PROGRESS — you may share a gentle plain-language "
                    "read of the journey (no gamification, no percentages unless they ask)."
                )
            else:
                lines.append(
                    "Do not dump the meter unprompted. Hold it for guidance; offer a soft check-in "
                    "only if it fits their energy."
                )

            if is_first_turn:
                lines.append("Returning: one optional bridge to their mission — never force.")

            lines.append(
                "Hermes pattern: ephemeral context. Durable mission facts → memory tool → USER.md when confirmed."
            )
            return "\n".join(lines)

    def after_turn(
        self,
        user_text: str,
        assistant_text: str = "",
        *,
        protocols: Optional[Sequence[str]] = None,
        affect: str = "",
        crisis: bool = False,
        moment_ids: Optional[Sequence[str]] = None,
    ) -> CompoundState:
        with _LOCK:
            if crisis or affect == "crisis":
                self._pause_for_crisis(affect=affect)
                self.state.save()
                return self.state

            self._capture_or_refine_mission(
                user_text, protocols=list(protocols or []), affect=affect
            )
            mission = self.state.active()
            if not mission:
                self.state.save()
                return self.state

            if moment_ids:
                for mid in moment_ids:
                    if mid and mid not in mission.linked_moment_ids:
                        mission.linked_moment_ids.append(mid)
                mission.linked_moment_ids = mission.linked_moment_ids[-24:]

            # Understanding compounds even without explicit progress language
            if user_text and len(user_text.split()) > 8:
                note = " ".join(user_text.split())[:140]
                if note not in mission.understanding_notes:
                    mission.understanding_notes.append(note)
                    mission.understanding_notes = mission.understanding_notes[-20:]

            progress_hit = bool(_PROGRESS_RE.search(user_text or ""))
            stall_hit = bool(_STALL_RE.search(user_text or ""))
            center_hit = bool(_CENTER_MET_RE.search(user_text or ""))

            if _EXPLICIT_METER_RE.search(user_text or ""):
                mission.consent = "explicit"

            # Center only from clear safety / reach-out signals — never from generic "progress"
            if center_hit:
                self._try_meet_center(
                    mission, user_text, affect=affect, protocols=list(protocols or [])
                )

            if progress_hit and not stall_hit:
                self._record_progress(
                    mission, user_text, affect=affect, protocols=list(protocols or [])
                )
            elif stall_hit:
                self._record_stall(
                    mission, user_text, affect=affect, protocols=list(protocols or [])
                )

            # Advance ladder focus when center met and progress compounds
            if mission.meter.center_met and mission.meter.progress_count > 0:
                self._maybe_advance_rung(mission)

            # Resume from pause when affect calms
            if mission.status == "paused" and affect in {"calm", "rising", "mixed"}:
                mission.status = "active"
                self._log("progress", "Mission gently resumed after pause", affect=affect)

            mission.touch()
            self.state.save()
            return self.state

    def set_mission(
        self,
        statement: str,
        *,
        why: str = "",
        protocols: Optional[Sequence[str]] = None,
        consent: str = "implicit",
    ) -> UserMission:
        with _LOCK:
            mission = UserMission.create(
                statement, why=why, protocols=protocols, consent=consent
            )
            self.state.missions.append(mission)
            self.state.active_mission_id = mission.id
            self._log(
                "mission_set",
                f"Mission established: {mission.statement}",
                evidence=statement[:160],
            )
            self.state.save()
            return mission

    # --- internals ---------------------------------------------------------

    def _capture_or_refine_mission(
        self,
        user_text: str,
        *,
        protocols: List[str],
        affect: str,
    ) -> None:
        text = user_text or ""
        m = _MISSION_RE.search(text)
        if not m:
            return
        # Prefer the trailing clause; fall back to the full match (no double-concat)
        clause = (m.group(1) or "").strip(" .:;-")
        lead = m.group(0)[: m.start(1) - m.start(0)].strip() if m.lastindex else m.group(0)
        if clause:
            statement = " ".join(f"{lead} {clause}".split())[:280]
        else:
            statement = " ".join(m.group(0).split())[:280]
        why = ""
        why_m = _WHY_RE.search(text)
        if why_m:
            why = " ".join(why_m.group(0).split())[:200]

        active = self.state.active()
        if not active:
            mission = UserMission.create(
                statement, why=why, protocols=protocols, consent="implicit"
            )
            self.state.missions.append(mission)
            self.state.active_mission_id = mission.id
            self._log(
                "mission_set",
                f"Mission heard from user: {mission.statement}",
                evidence=statement[:160],
                affect=affect,
                protocol=(protocols[0] if protocols else ""),
            )
            return

        # Refine if clearly new wording (not tiny echo)
        if statement.lower() not in active.statement.lower() and len(statement) > 20:
            # Keep core; append refined understanding
            if len(statement) > len(active.statement) * 0.6:
                old = active.statement
                active.statement = statement
                if why:
                    active.why = why
                for p in protocols:
                    if p not in active.protocol_tags:
                        active.protocol_tags.append(p)
                active.touch()
                self._log(
                    "mission_refined",
                    f"Mission refined from «{old[:80]}» → «{statement[:80]}»",
                    evidence=statement[:160],
                    affect=affect,
                )

    def _try_meet_center(
        self,
        mission: UserMission,
        user_text: str,
        *,
        affect: str,
        protocols: List[str],
    ) -> None:
        center = mission.center_checkpoint()
        if not center or center.status == "met":
            return
        # Only meet center when affect is not crisis and user shows safety signal
        if affect == "crisis":
            return
        center.status = "met"
        center.met_at = _now()
        center.evidence.append(" ".join(user_text.split())[:140])
        center.evidence = center.evidence[-6:]
        mission.meter.center_met = True
        mission.current_ladder_rung = "body"
        mission.touch()
        self._log(
            "center_met",
            f"Center checkpoint met: {center.title}. Guidance may compound carefully.",
            checkpoint_id=center.id,
            evidence=user_text[:160],
            affect=affect,
            protocol=(protocols[0] if protocols else ""),
        )

    def _record_progress(
        self,
        mission: UserMission,
        user_text: str,
        *,
        affect: str,
        protocols: List[str],
    ) -> None:
        mission.meter.progress_count += 1
        mission.meter.last_progress_at = _now()
        # Meet the next non-center upcoming/offered/stalled checkpoint if center is done
        if mission.meter.center_met:
            for cp in sorted(mission.checkpoints, key=lambda c: c.order):
                if cp.is_center:
                    continue
                if cp.status in {"upcoming", "offered", "stalled", "center"}:
                    cp.status = "met"
                    cp.met_at = _now()
                    cp.evidence.append(" ".join(user_text.split())[:140])
                    break
        else:
            # Progress before center: still counts toward understanding, offer center gently
            center = mission.center_checkpoint()
            if center and center.status == "center":
                center.status = "offered"
                center.offered_at = center.offered_at or _now()

        # Horizon improves slightly on progress
        if mission.meter.estimated_horizon == "much_longer" and mission.meter.stall_count > 0:
            mission.meter.stall_count = max(0, mission.meter.stall_count - 1)
        mission.touch()
        self._log(
            "progress",
            "Progress compounded toward the mission.",
            evidence=user_text[:160],
            affect=affect,
            protocol=(protocols[0] if protocols else ""),
        )

    def _record_stall(
        self,
        mission: UserMission,
        user_text: str,
        *,
        affect: str,
        protocols: List[str],
    ) -> None:
        mission.meter.stall_count += 1
        mission.meter.last_stall_at = _now()
        # Stall the active offered/center checkpoint
        target = None
        for cp in mission.checkpoints:
            if cp.status in {"offered", "center"}:
                target = cp
                break
        if not target:
            for cp in mission.checkpoints:
                if cp.status not in {"met", "skipped"}:
                    target = cp
                    break
        if target:
            if target.status != "met":
                target.status = "stalled"
            target.stall_count += 1
            target.evidence.append(" ".join(user_text.split())[:140])
            target.evidence = target.evidence[-6:]

        prev_horizon = mission.meter.estimated_horizon
        mission.touch()
        self._log(
            "stall",
            "Stall recorded — shrink the next step; no shame.",
            checkpoint_id=target.id if target else "",
            evidence=user_text[:160],
            affect=affect,
            protocol=(protocols[0] if protocols else ""),
        )
        if mission.meter.estimated_horizon != prev_horizon and mission.meter.estimated_horizon in {
            "longer",
            "much_longer",
        }:
            self._log(
                "journey_extended",
                f"Journey horizon moved to `{mission.meter.estimated_horizon}` — "
                "reaching the mission will take longer based on what we learned together.",
                checkpoint_id=target.id if target else "",
                evidence=user_text[:160],
                affect=affect,
            )

    def _maybe_advance_rung(self, mission: UserMission) -> None:
        order = {r: i for i, r in enumerate(LADDER)}
        current = order.get(mission.current_ladder_rung, 0)
        # Advance when a checkpoint on the next rung is met
        for cp in mission.checkpoints:
            if cp.status == "met":
                idx = order.get(cp.ladder_rung, 0)
                if idx > current:
                    current = idx
                    mission.current_ladder_rung = cp.ladder_rung

    def _pause_for_crisis(self, *, affect: str) -> None:
        mission = self.state.active()
        if not mission or mission.status != "active":
            return
        mission.status = "paused"
        mission.touch()
        self._log(
            "crisis_pause",
            "Mission paused for crisis safety — meter guidance silenced.",
            affect=affect,
        )

    def _log(
        self,
        kind: str,
        summary: str,
        *,
        checkpoint_id: str = "",
        evidence: str = "",
        affect: str = "",
        protocol: str = "",
    ) -> None:
        self.state.records.append(
            ProgressRecord.create(
                kind,
                summary,
                checkpoint_id=checkpoint_id,
                evidence=evidence,
                affect=affect,
                protocol=protocol,
            )
        )
        self.state.records = self.state.records[-120:]


def get_compound() -> CompoundEngine:
    global _ENGINE
    with _LOCK:
        if _ENGINE is None:
            _ENGINE = CompoundEngine()
        return _ENGINE


def reset_compound() -> CompoundEngine:
    global _ENGINE
    with _LOCK:
        _ENGINE = CompoundEngine()
        return _ENGINE
