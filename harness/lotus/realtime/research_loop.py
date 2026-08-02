"""Research subroutine — always seeking safer, better ways to help."""

from __future__ import annotations

import json
import time
from typing import List

from .model import LivingUserModel
from .paths import approaches_md_path, research_log_path
from .understanding import UnderstandingSnapshot

# Seed research topics mapped from mission surfaces — public-science posture only.
_PROTOCOL_RESEARCH = {
    "P1_depression": [
        ("behavioral activation micro-steps", "depression support"),
        ("rumination interruption techniques evidence", "depression support"),
    ],
    "P2_health": [
        ("health anxiety coping strategies reputable", "health stress"),
        ("pacing chronic illness emotional support", "health stress"),
        ("CDC everyday words medical jargon plain language", "plain language"),
        ("OpenMed analyze_text clinical NER everyday explanation companion", "plain language"),
        ("MedlinePlus plain language lab results patient education", "plain language"),
    ],
    "P3_grief": [
        ("continuing bonds grief research", "grief"),
        ("grief waves support without forced closure", "grief"),
    ],
    "P4_major_event": [
        ("acute stress decision making delay irreversible choices", "major events"),
        ("emotional regulation after life transition", "major events"),
    ],
    "CRISIS": [
        ("crisis conversation stay-with skills non-method", "crisis safety"),
    ],
}


class ResearchSubroutine:
    """Queues and records research; injects known approaches into every turn."""

    def sync_queue(self, model: LivingUserModel, snap: UnderstandingSnapshot) -> LivingUserModel:
        for gap in snap.gaps:
            model.enqueue_research(
                topic=gap.replace("_", " "),
                reason="open understanding/help gap",
                priority="high" if snap.affect.valence in {"crisis", "low"} else "normal",
            )
        for proto in model.active_protocols:
            for topic, reason in _PROTOCOL_RESEARCH.get(proto, []):
                # Only enqueue if we lack approaches tagged with this reason
                if not any(reason in (a.get("tags") or []) for a in model.help_approaches):
                    model.enqueue_research(topic, reason=f"protocol:{reason}", priority="normal")

        if snap.affect.valence in {"low", "mixed"} and len(model.successful_moves) == 0:
            model.enqueue_research(
                "safe first-line supportive conversation techniques for emotional numbness",
                reason="no successful moves learned yet",
                priority="high",
            )
        return model

    def prompt_directives(self, model: LivingUserModel) -> str:
        queued = [q for q in model.research_queue if q.get("status") == "queued"]
        lines = [
            "[L.O.T.U.S. RESEARCH SUBROUTINE]",
            "Always look for better, safer ways to help — public reputable sources only.",
            "Never research harm methods. Never claim proprietary neural reverse-engineering.",
        ]
        if queued:
            top = queued[:3]
            lines.append("Active research queue (address when tools allow, without abandoning presence):")
            for q in top:
                lines.append(f"  • {q.get('topic')} — {q.get('reason')}")
            lines.append(
                "When you learn a useful safe approach, summarize it and persist via memory / "
                "lotus-core APPROACHES (title + 2-3 sentences + source)."
            )
        else:
            lines.append("Research queue clear — keep deepening the living model of this user.")
        if model.help_approaches:
            lines.append("Reuse approaches that already fit this person before inventing new ones.")
        return "\n".join(lines)

    def mark_researched(self, model: LivingUserModel, topic: str) -> None:
        for q in model.research_queue:
            if q.get("topic", "").lower() == topic.lower() and q.get("status") == "queued":
                q["status"] = "done"
                q["done_ts"] = time.time()
        model.touch()

    def log_finding(self, topic: str, finding: str, source: str = "") -> None:
        path = research_log_path()
        rec = {
            "ts": time.time(),
            "topic": topic,
            "finding": finding,
            "source": source,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def write_approaches_md(self, model: LivingUserModel) -> None:
        path = approaches_md_path()
        lines = [
            "# L.O.T.U.S. Help Approaches Library",
            "",
            "Evidence-informed, user-safe approaches discovered by the research subroutine.",
            "",
        ]
        if not model.help_approaches:
            lines.append("_No approaches stored yet — research pulse will fill this._")
        for a in model.help_approaches:
            lines.append(f"## {a.get('title', 'Untitled')}")
            lines.append("")
            lines.append(a.get("summary", ""))
            if a.get("source"):
                lines.append("")
                lines.append(f"Source: {a['source']}")
            tags = a.get("tags") or []
            if tags:
                lines.append("")
                lines.append("Tags: " + ", ".join(tags))
            lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def pending_topics(self, model: LivingUserModel, limit: int = 5) -> List[str]:
        return [
            q["topic"]
            for q in model.research_queue
            if q.get("status") == "queued" and q.get("topic")
        ][:limit]

    def seed_offline_approaches(self, model: LivingUserModel) -> int:
        """Seed a small safe approaches library from local foundations when empty.

        Does not replace the Hermes research cron; fills the gap until the first
        live pulse runs so the agent is never approach-blind.
        """
        if model.help_approaches:
            return 0
        seeds = [
            {
                "title": "Witness before advice",
                "summary": (
                    "Reflect what was heard in plain language before offering any step. "
                    "Reduces isolation and avoids advice-dump overwhelm."
                ),
                "source": "lotus foundations / supportive counseling basics",
                "tags": ["depression support", "continuity"],
            },
            {
                "title": "One micro-action",
                "summary": (
                    "When affect is low, offer a single small, reversible next step "
                    "(water, light, brief contact) rather than a plan of many."
                ),
                "source": "behavioral activation micro-steps (public science posture)",
                "tags": ["depression support"],
            },
            {
                "title": "Grief without forced closure",
                "summary": (
                    "Allow mixed feelings and continuing bonds. Do not rush acceptance "
                    "language; stay with the wave and invite return."
                ),
                "source": "continuing bonds grief research (public)",
                "tags": ["grief"],
            },
            {
                "title": "Crisis: stay + redirect to humans",
                "summary": (
                    "Refuse harm methods. Urge local emergency / regional crisis lines. "
                    "Stay conversationally present without digging for graphic detail."
                ),
                "source": "IASP + lotus GUARDRAILS",
                "tags": ["crisis safety"],
            },
        ]
        added = 0
        for s in seeds:
            model.help_approaches.append(s)
            added += 1
        if added:
            model.touch()
            self.write_approaches_md(model)
            self.log_finding(
                "offline_seed",
                f"seeded {added} baseline approaches (no live search)",
                source="lotus.research_loop.seed_offline_approaches",
            )
        return added

    def pulse_status(self, model: LivingUserModel) -> dict:
        queued = [q for q in model.research_queue if q.get("status") == "queued"]
        done = [q for q in model.research_queue if q.get("status") == "done"]
        log_tail: List[str] = []
        path = research_log_path()
        if path.is_file():
            try:
                lines = path.read_text(encoding="utf-8").strip().splitlines()
                log_tail = lines[-5:]
            except OSError:
                pass
        return {
            "queued": len(queued),
            "done": len(done),
            "approaches": len(model.help_approaches),
            "pending_topics": [q.get("topic") for q in queued[:5]],
            "log_tail": log_tail,
        }
