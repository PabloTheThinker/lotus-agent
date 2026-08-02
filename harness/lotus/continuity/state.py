"""Durable continuity state — resume cards, open threads, sync candidates."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .paths import continuity_path, memory_sync_path, resume_card_path


def _now() -> float:
    return time.time()


@dataclass
class ContinuityState:
    version: int = 1
    updated_at: float = field(default_factory=_now)
    session_count: int = 0
    last_session_id: str = ""
    last_platform: str = ""
    last_affect: str = "unknown"
    last_protocol: str = ""
    resume_summary: str = ""
    open_threads: List[str] = field(default_factory=list)
    pending_checkins: List[str] = field(default_factory=list)
    warmth_notes: List[str] = field(default_factory=list)
    memory_promotions: List[Dict[str, str]] = field(default_factory=list)
    turn_in_session: int = 0

    def touch(self) -> None:
        self.updated_at = _now()

    def remember_thread(self, text: str, *, limit: int = 12) -> None:
        text = (text or "").strip()
        if not text:
            return
        if text in self.open_threads:
            self.open_threads.remove(text)
        self.open_threads.append(text)
        if len(self.open_threads) > limit:
            self.open_threads = self.open_threads[-limit:]
        self.touch()

    def remember_checkin(self, text: str, *, limit: int = 8) -> None:
        text = (text or "").strip()
        if not text:
            return
        if text in self.pending_checkins:
            return
        self.pending_checkins.append(text)
        if len(self.pending_checkins) > limit:
            self.pending_checkins = self.pending_checkins[-limit:]
        self.touch()

    def queue_promotion(self, kind: str, content: str) -> None:
        content = (content or "").strip()
        if not content:
            return
        for p in self.memory_promotions:
            if p.get("content") == content:
                return
        self.memory_promotions.append({"kind": kind, "content": content, "ts": str(_now())})
        if len(self.memory_promotions) > 30:
            self.memory_promotions = self.memory_promotions[-30:]
        self.touch()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContinuityState":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        from lotus.schema import stamp

        continuity_path().write_text(
            json.dumps(stamp(self.to_dict(), kind="continuity"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        self._write_resume_md()
        self._write_memory_sync_md()

    def _write_resume_md(self) -> None:
        lines = [
            "# L.O.T.U.S. Resume Card",
            "",
            f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.updated_at))}",
            f"Sessions: {self.session_count}",
            f"Last affect: {self.last_affect}",
            f"Last protocol: {self.last_protocol or '—'}",
            "",
            "## Where we left off",
            self.resume_summary or "_(new relationship — listen first)_",
            "",
            "## Open threads",
        ]
        if self.open_threads:
            lines.extend(f"- {t}" for t in self.open_threads[-10:])
        else:
            lines.append("- (none)")
        lines += ["", "## Gentle check-ins"]
        if self.pending_checkins:
            lines.extend(f"- {t}" for t in self.pending_checkins[-8:])
        else:
            lines.append("- (none)")
        lines += ["", "## Warmth"]
        if self.warmth_notes:
            lines.extend(f"- {t}" for t in self.warmth_notes[-8:])
        else:
            lines.append("- (learning…)")
        lines.append("")
        resume_card_path().write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_memory_sync_md(self) -> None:
        lines = [
            "# L.O.T.U.S. Memory Sync Candidates",
            "",
            "Stable facts ready to promote into Hermes `USER.md` / `MEMORY.md`",
            "via the built-in `memory` tool (do not invent; confirm against conversation).",
            "",
        ]
        if not self.memory_promotions:
            lines.append("_No pending promotions._")
        else:
            for p in self.memory_promotions[-20:]:
                lines.append(f"- **{p.get('kind', 'note')}**: {p.get('content', '')}")
        lines.append("")
        memory_sync_path().write_text("\n".join(lines) + "\n", encoding="utf-8")

    @classmethod
    def load(cls) -> "ContinuityState":
        path = continuity_path()
        if not path.exists():
            st = cls()
            st.save()
            return st
        try:
            from lotus.schema import ensure_schema

            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return cls()
            data = ensure_schema(data, kind="continuity")
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, OSError):
            return cls()
