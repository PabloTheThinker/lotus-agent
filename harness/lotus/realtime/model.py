"""Living user model — continuously updated understanding of the person."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .paths import insights_md_path, living_model_path


def _now() -> float:
    return time.time()


@dataclass
class AffectSample:
    ts: float
    valence: str  # low | mixed | rising | crisis | calm | unknown
    intensity: float  # 0..1
    signals: List[str] = field(default_factory=list)


@dataclass
class LivingUserModel:
    """Durable, always-learning model of the user for L.O.T.U.S."""

    version: int = 1
    updated_at: float = field(default_factory=_now)
    turn_count: int = 0

    # Real-time read
    current_affect: str = "unknown"
    current_intensity: float = 0.0
    active_protocols: List[str] = field(default_factory=list)
    affect_trajectory: List[Dict[str, Any]] = field(default_factory=list)

    # Deep understanding
    preferred_language: List[str] = field(default_factory=list)
    avoided_language: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    support_people: List[str] = field(default_factory=list)
    grounding_tools_that_work: List[str] = field(default_factory=list)

    # Adaptive voice / relatability (learned from their words + memories)
    user_phrases: List[str] = field(default_factory=list)
    user_metaphors: List[str] = field(default_factory=list)
    emotion_lexicon: List[str] = field(default_factory=list)
    connection_anchors: List[str] = field(default_factory=list)
    shared_moments: List[str] = field(default_factory=list)
    voice_style: Dict[str, Any] = field(default_factory=dict)
    relatability_notes: List[str] = field(default_factory=list)

    # Learning loop
    successful_moves: List[str] = field(default_factory=list)
    failed_moves: List[str] = field(default_factory=list)
    open_gaps: List[str] = field(default_factory=list)  # what we still need to understand/help
    hypotheses: List[str] = field(default_factory=list)

    # Research loop
    research_queue: List[Dict[str, Any]] = field(default_factory=list)
    help_approaches: List[Dict[str, Any]] = field(default_factory=list)

    # Session notes
    last_user_summary: str = ""
    last_next_step: str = ""

    def touch(self) -> None:
        self.updated_at = _now()

    def push_affect(self, sample: AffectSample, *, max_len: int = 40) -> None:
        self.current_affect = sample.valence
        self.current_intensity = sample.intensity
        self.affect_trajectory.append(asdict(sample))
        if len(self.affect_trajectory) > max_len:
            self.affect_trajectory = self.affect_trajectory[-max_len:]
        self.touch()

    def remember(self, bucket: str, value: str, *, limit: int = 24) -> None:
        if not value or not value.strip():
            return
        value = value.strip()
        seq: List[str] = getattr(self, bucket)
        if value in seq:
            # bump to end (recency)
            seq.remove(value)
        seq.append(value)
        if len(seq) > limit:
            del seq[: len(seq) - limit]
        self.touch()

    def enqueue_research(self, topic: str, reason: str, *, priority: str = "normal") -> None:
        topic = topic.strip()
        if not topic:
            return
        for item in self.research_queue:
            if item.get("topic", "").lower() == topic.lower() and item.get("status") == "queued":
                return
        self.research_queue.append(
            {
                "topic": topic,
                "reason": reason,
                "priority": priority,
                "status": "queued",
                "ts": _now(),
            }
        )
        # keep queue bounded
        if len(self.research_queue) > 40:
            self.research_queue = self.research_queue[-40:]
        self.touch()

    def add_approach(self, title: str, summary: str, source: str = "", tags: Optional[List[str]] = None) -> None:
        title = title.strip()
        if not title:
            return
        for a in self.help_approaches:
            if a.get("title", "").lower() == title.lower():
                a["summary"] = summary
                a["source"] = source or a.get("source", "")
                a["tags"] = tags or a.get("tags", [])
                a["ts"] = _now()
                self.touch()
                return
        self.help_approaches.append(
            {
                "title": title,
                "summary": summary,
                "source": source,
                "tags": tags or [],
                "ts": _now(),
                "times_suggested": 0,
            }
        )
        if len(self.help_approaches) > 60:
            self.help_approaches = self.help_approaches[-60:]
        self.touch()

    def prompt_block(self, *, max_approaches: int = 5) -> str:
        """Compact block injected every turn so the agent always 'sees' the user."""
        lines = [
            "[L.O.T.U.S. REALTIME CORE — living user model]",
            f"turns={self.turn_count} affect={self.current_affect} intensity={self.current_intensity:.2f}",
            f"active_protocols={', '.join(self.active_protocols) or 'none'}",
        ]
        if self.last_user_summary:
            lines.append(f"last_read: {self.last_user_summary}")
        if self.preferred_language:
            lines.append("language_that_helps: " + "; ".join(self.preferred_language[-6:]))
        if self.avoided_language:
            lines.append("language_to_avoid: " + "; ".join(self.avoided_language[-6:]))
        style = self.voice_style or {}
        if style.get("frequent_needs") or style.get("sms_short") or style.get("hates_worksheets"):
            bits = []
            if style.get("reply_length"):
                bits.append(f"reply_length={style.get('reply_length')}")
            if style.get("frequent_needs"):
                bits.append(f"needs={style.get('frequent_needs')}")
            if style.get("hates_worksheets"):
                bits.append("no_worksheets")
            if style.get("hates_meta"):
                bits.append("no_meta")
            if int(style.get("soft_loop_count") or 0) >= 2:
                bits.append(f"soft_loop={style.get('soft_loop_count')}")
            if bits:
                lines.append("talk_patterns: " + "; ".join(bits))
        if self.user_phrases:
            lines.append("their_phrases: " + "; ".join(self.user_phrases[-8:]))
        if self.user_metaphors:
            lines.append("their_metaphors: " + "; ".join(self.user_metaphors[-6:]))
        if self.connection_anchors:
            lines.append("connection_anchors: " + "; ".join(self.connection_anchors[-8:]))
        if self.shared_moments:
            lines.append("shared_moments: " + "; ".join(self.shared_moments[-5:]))
        if self.triggers:
            lines.append("triggers: " + "; ".join(self.triggers[-8:]))
        if self.strengths:
            lines.append("strengths: " + "; ".join(self.strengths[-6:]))
        if self.grounding_tools_that_work:
            lines.append("grounding_that_works: " + "; ".join(self.grounding_tools_that_work[-6:]))
        if self.successful_moves:
            lines.append("successful_moves: " + "; ".join(self.successful_moves[-6:]))
        if self.failed_moves:
            lines.append("failed_moves: " + "; ".join(self.failed_moves[-4:]))
        if self.open_gaps:
            lines.append("open_gaps: " + "; ".join(self.open_gaps[-6:]))
        queued = [q for q in self.research_queue if q.get("status") == "queued"]
        if queued:
            lines.append(
                "research_queue: "
                + "; ".join(f"{q['topic']} ({q.get('priority','normal')})" for q in queued[-5:])
            )
        approaches = self.help_approaches[-max_approaches:]
        if approaches:
            lines.append("help_approaches_ready:")
            for a in approaches:
                lines.append(f"  - {a.get('title')}: {a.get('summary', '')[:160]}")
        if self.last_next_step:
            lines.append(f"last_offered_step: {self.last_next_step}")
        lines.append(
            "Duty: keep reading the user in real time; adapt language from their memories; "
            "learn what helps; research safer ways — never chaos/harm."
        )
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LivingUserModel":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        from lotus.schema import stamp

        path = living_model_path()
        path.write_text(
            json.dumps(stamp(self.to_dict(), kind="living_model"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        self._write_insights_md()
        try:
            from .voice_adapt import write_voice_md

            write_voice_md(self)
        except Exception:
            pass

    def _write_insights_md(self) -> None:
        path = insights_md_path()

        def bullets(items: List[str], empty: str) -> List[str]:
            chunk = items[-12:]
            return [f"- {x}" for x in chunk] if chunk else [empty]

        lines = [
            "# L.O.T.U.S. Living Insights",
            "",
            f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.updated_at))}",
            f"Turns observed: {self.turn_count}",
            f"Current affect: **{self.current_affect}** (intensity {self.current_intensity:.2f})",
            f"Protocols: {', '.join(self.active_protocols) or '—'}",
            "",
            "## What helps",
            *bullets(self.successful_moves, "- (learning…)"),
            "",
            "## Grounding tools that work",
            *bullets(self.grounding_tools_that_work, "- (learning…)"),
            "",
            "## Language that helps",
            *bullets(self.preferred_language, "- (learning…)"),
            "",
            "## Their phrases (optional light touch — do not parrot)",
            *bullets(self.user_phrases, "- (learning…)"),
            "",
            "## Their metaphors",
            *bullets(self.user_metaphors, "- (learning…)"),
            "",
            "## Connection anchors",
            *bullets(self.connection_anchors, "- (learning…)"),
            "",
            "## Shared moments",
            *bullets(self.shared_moments, "- (none yet)"),
            "",
            "## Avoid",
            *bullets(self.avoided_language, "- (none recorded)"),
            "",
            "## Triggers",
            *bullets(self.triggers, "- (none recorded)"),
            "",
            "## Strengths",
            *bullets(self.strengths, "- (learning…)"),
            "",
            "## Open gaps (research these)",
            *bullets(self.open_gaps, "- (none)"),
            "",
            "## Research queue",
        ]
        queued = [q for q in self.research_queue if q.get("status") == "queued"]
        if queued:
            for q in queued[-15:]:
                lines.append(
                    f"- [{q.get('priority','normal')}] {q.get('topic')} — {q.get('reason','')}"
                )
        else:
            lines.append("- (empty)")
        lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def load(cls) -> "LivingUserModel":
        path = living_model_path()
        if not path.exists():
            model = cls()
            model.save()
            return model
        try:
            from lotus.schema import ensure_schema

            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return cls()
            data = ensure_schema(data, kind="living_model")
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, OSError):
            return cls()
