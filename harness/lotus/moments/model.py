"""Structured moments + links — connect events across conversations."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .paths import moments_json_path, moments_md_path

MOMENT_KINDS = (
    "life_event",
    "conversation",
    "thread",
    "checkin",
    "affect",
    "anchor",
    "health",
    "grief",
    "rebuild",
)

LINK_KINDS = (
    "related",
    "continues",
    "same_theme",
    "caused_by",
    "resolved_by",
    "mentions",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug_tokens(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z]{3,}", (text or "").lower())
    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "have",
        "been",
        "from",
        "about",
        "just",
        "like",
        "feel",
        "felt",
        "when",
        "what",
        "your",
        "you",
        "was",
        "are",
        "but",
        "not",
        "they",
        "them",
        "her",
        "his",
        "she",
        "him",
        "our",
        "out",
        "can",
        "could",
        "would",
        "should",
        "into",
        "over",
        "than",
        "then",
        "also",
        "very",
        "more",
        "some",
        "any",
        "all",
        "how",
        "why",
        "who",
    }
    out: List[str] = []
    seen = set()
    for w in words:
        if w in stop or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= 12:
            break
    return out


@dataclass
class Moment:
    id: str
    kind: str
    title: str
    summary: str
    status: str = "open"  # open | active | resolved | quiet
    created_at: str = ""
    updated_at: str = ""
    session_ids: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)
    affect: str = ""
    tokens: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)  # continuity|realtime|extract|user
    evidence: List[str] = field(default_factory=list)  # short quotes
    related_data: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        kind: str,
        title: str,
        summary: str,
        session_id: str = "",
        protocols: Optional[Sequence[str]] = None,
        affect: str = "",
        source: str = "extract",
        evidence: str = "",
    ) -> "Moment":
        ts = _now()
        title = " ".join((title or summary).split())[:120]
        summary = " ".join((summary or title).split())[:280]
        tokens = _slug_tokens(f"{title} {summary}")
        return cls(
            id=f"m_{uuid.uuid4().hex[:10]}",
            kind=kind if kind in MOMENT_KINDS else "conversation",
            title=title or "untitled moment",
            summary=summary,
            status="open",
            created_at=ts,
            updated_at=ts,
            session_ids=[session_id] if session_id else [],
            protocols=list(protocols or []),
            affect=affect or "",
            tokens=tokens,
            sources=[source] if source else [],
            evidence=[evidence[:160]] if evidence else [],
        )


@dataclass
class MomentLink:
    id: str
    source_id: str
    target_id: str
    kind: str = "related"
    reason: str = ""
    created_at: str = ""
    strength: float = 0.5

    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        *,
        kind: str = "related",
        reason: str = "",
        strength: float = 0.5,
    ) -> "MomentLink":
        return cls(
            id=f"l_{uuid.uuid4().hex[:8]}",
            source_id=source_id,
            target_id=target_id,
            kind=kind if kind in LINK_KINDS else "related",
            reason=(reason or "")[:160],
            created_at=_now(),
            strength=max(0.0, min(1.0, strength)),
        )


@dataclass
class MomentsGraph:
    version: int = 1
    moments: List[Moment] = field(default_factory=list)
    links: List[MomentLink] = field(default_factory=list)
    updated_at: str = ""

    def by_id(self) -> Dict[str, Moment]:
        return {m.id: m for m in self.moments}

    def save(self, path: Optional[Path] = None) -> None:
        from lotus.schema import stamp

        self.updated_at = _now()
        path = path or moments_json_path()
        payload = stamp(
            {
                "version": self.version,
                "updated_at": self.updated_at,
                "moments": [asdict(m) for m in self.moments[-200:]],
                "links": [asdict(link) for link in self.links[-400:]],
            },
            kind="moments",
        )
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self._write_md()

    def _write_md(self) -> None:
        lines = [
            "# L.O.T.U.S. Moments",
            "",
            "Connected events across conversations. Ephemeral context for the agent; "
            "durable life facts still promote to USER.md via the Hermes memory tool.",
            "",
        ]
        open_m = [m for m in self.moments if m.status in {"open", "active"}]
        if not open_m:
            lines.append("_No open moments yet._")
        else:
            lines.append("## Open / active")
            for m in open_m[-20:][::-1]:
                protos = ", ".join(m.protocols) if m.protocols else "—"
                lines.append(f"- **{m.title}** (`{m.kind}`, {m.status}) — {m.summary}")
                lines.append(f"  - id: `{m.id}` · protocols: {protos} · tokens: {', '.join(m.tokens[:6]) or '—'}")
        if self.links:
            lines.extend(["", "## Recent connections"])
            index = self.by_id()
            for link in self.links[-15:][::-1]:
                a = index.get(link.source_id)
                b = index.get(link.target_id)
                if not a or not b:
                    continue
                lines.append(
                    f"- {a.title} —[{link.kind}]→ {b.title}"
                    + (f" ({link.reason})" if link.reason else "")
                )
        moments_md_path().write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "MomentsGraph":
        path = path or moments_json_path()
        if not path.is_file():
            return cls()
        try:
            from lotus.schema import ensure_schema

            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        raw = ensure_schema(raw, kind="moments")
        moments = [Moment(**m) for m in raw.get("moments") or [] if isinstance(m, dict)]
        links = [
            MomentLink(**link) for link in raw.get("links") or [] if isinstance(link, dict)
        ]
        return cls(
            version=int(raw.get("version") or 1),
            moments=moments,
            links=links,
            updated_at=str(raw.get("updated_at") or ""),
        )
