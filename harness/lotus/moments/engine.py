"""MomentsEngine — connect events, threads, and conversation data over time."""

from __future__ import annotations

import re
import threading
from typing import List, Optional, Sequence, Tuple

from .model import Moment, MomentLink, MomentsGraph, _now, _slug_tokens

_LOCK = threading.RLock()
_ENGINE: Optional["MomentsEngine"] = None

# Life / emotional events that deserve a durable moment node
_EVENT_PATTERNS: List[Tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            r"\b(passed away|died|funeral|bereav|lost my (?:mom|dad|mother|father|partner|friend|pet)|"
            r"falleci[oó]|murió|morreu|décédé|gestorben|duelo|luto|deuil|trauer)\b",
            re.I,
        ),
        "grief",
        "Grief / loss",
    ),
    (
        re.compile(
            r"\b(diagnos(?:ed|is)|surgery|chronic (?:pain|illness)|relapse|scan results?|"
            r"my (?:hospital|surgery|scan|biopsy|diagnosis)|"
            r"i(?:'m| am| was) (?:in|at) (?:the )?(?:hospital|er|icu)|"
            r"diagnóstico|cirugía|chirurgie)\b",
            re.I,
        ),
        "health",
        "Health stress",
    ),
    (
        re.compile(
            r"\b(fired|laid off|quit my job|new job|promot(?:ed|ion)|broke up|divorc|"
            r"evict(?:ed|ion)|moved (?:out|in|away)|relocat|wedding|graduation|windfall|"
            r"despedido|desemprego|licencié|gekündigt|separaci[oó]n|divórcio)\b",
            re.I,
        ),
        "life_event",
        "Major life event",
    ),
    (
        re.compile(
            r"\b(anniversary|that day|remember when|last time we|we talked about|"
            r"since (?:my|the)|after (?:my|the))\b",
            re.I,
        ),
        "conversation",
        "Shared recall",
    ),
    (
        re.compile(
            r"\b(we(?:'ll| will) (?:talk|come back)|not ready|another time|"
            r"still figuring|more to say|unfinished)\b",
            re.I,
        ),
        "thread",
        "Open thread",
    ),
    (
        re.compile(
            r"\b(check (?:in|back)|remind me|follow up|ask me (?:later|tomorrow|next time))\b",
            re.I,
        ),
        "checkin",
        "Pending check-in",
    ),
    (
        re.compile(
            r"\b(my (?:mom|dad|mother|father|partner|spouse|kids?|friend|therapist|dog|cat))\b",
            re.I,
        ),
        "anchor",
        "Connection anchor",
    ),
]

_RESOLVE_RE = re.compile(
    r"\b(that(?:'s| is) (?:enough|done|closed|behind me)|we (?:covered|finished) that|"
    r"i(?:'m| am) (?:done|finished) (?:with )?that|no longer (?:need|want) to talk about)\b",
    re.I,
)


class MomentsEngine:
    """Connects moments across sessions — file-backed graph under lotus-core."""

    def __init__(self) -> None:
        self.graph = MomentsGraph.load()

    def reload(self) -> MomentsGraph:
        with _LOCK:
            self.graph = MomentsGraph.load()
            return self.graph

    def before_turn(
        self,
        user_text: str,
        *,
        is_first_turn: bool = False,
        session_id: str = "",
    ) -> str:
        """Ephemeral connected-context block for pre_llm_call."""
        with _LOCK:
            related = self.find_related(user_text, limit=5)
            open_cluster = [
                m for m in self.graph.moments if m.status in {"open", "active"}
            ][-6:]

            lines = [
                "[L.O.T.U.S. MOMENTS — connection system]",
                "Bring related events, open threads, and prior conversation data together.",
                "Speak naturally — never dump IDs at the user. Offer one gentle bridge if it fits.",
            ]
            if is_first_turn and open_cluster:
                lines.append("Open moments across time:")
                for m in open_cluster[::-1]:
                    lines.append(f"  • [{m.kind}/{m.status}] {m.title} — {m.summary[:120]}")

            if related:
                lines.append("Connected to what they just said:")
                for m, score in related:
                    neighbors = self._neighbor_titles(m.id, limit=3)
                    bridge = f" · linked: {', '.join(neighbors)}" if neighbors else ""
                    lines.append(
                        f"  • {m.title} ({m.kind}, score={score:.2f}) — {m.summary[:100]}{bridge}"
                    )
            else:
                lines.append("No strong prior moment match this turn — listen for new events.")

            lines.append(
                "Hermes pattern: this block is ephemeral. Confirmed life facts → memory tool → USER.md."
            )
            if session_id:
                lines.append(f"session_id={session_id}")
            return "\n".join(lines)

    def after_turn(
        self,
        user_text: str,
        assistant_text: str = "",
        *,
        session_id: str = "",
        protocols: Optional[Sequence[str]] = None,
        affect: str = "",
        history: Optional[Sequence[dict]] = None,
    ) -> MomentsGraph:
        with _LOCK:
            created = self._extract_moments(
                user_text,
                assistant_text,
                session_id=session_id,
                protocols=list(protocols or []),
                affect=affect or "",
            )
            # Also pull light signals from recent history (multi-turn threads)
            if history:
                for msg in list(history)[-4:]:
                    if msg.get("role") == "user":
                        created.extend(
                            self._extract_moments(
                                str(msg.get("content") or ""),
                                "",
                                session_id=session_id,
                                protocols=list(protocols or []),
                                affect=affect or "",
                                source="history",
                            )
                        )

            # Dedup / merge near-duplicates into existing nodes
            for moment in created:
                merged = self._merge_or_add(moment)
                self._auto_link(merged)

            if _RESOLVE_RE.search(user_text or ""):
                self._try_resolve(user_text)

            # Bridge flat lists from continuity / living model when available
            self._ingest_external_lists(session_id=session_id, protocols=list(protocols or []), affect=affect)

            self.graph.save()
            return self.graph

    def on_session_end(self) -> None:
        with _LOCK:
            # Quiet stale thin conversation moments older than keep-active ones
            for m in self.graph.moments:
                if m.kind == "conversation" and m.status == "open" and len(m.evidence) == 0:
                    m.status = "quiet"
            self.graph.save()

    def find_related(self, text: str, *, limit: int = 5) -> List[Tuple[Moment, float]]:
        tokens = set(_slug_tokens(text))
        if not tokens and not text:
            return []
        scored: List[Tuple[Moment, float]] = []
        lowered = (text or "").lower()
        for m in self.graph.moments:
            if m.status == "quiet" and m.kind == "conversation":
                continue
            overlap = len(tokens & set(m.tokens))
            title_hit = 1.0 if m.title.lower() in lowered or any(
                t in lowered for t in m.tokens[:4]
            ) else 0.0
            kind_boost = 0.15 if m.kind in {"grief", "health", "life_event", "thread"} else 0.0
            status_boost = 0.1 if m.status in {"open", "active"} else 0.0
            score = overlap * 0.35 + title_hit * 0.4 + kind_boost + status_boost
            # Graph neighbors of any token-matching moment get a small bump later
            if score > 0.2:
                scored.append((m, min(1.0, score)))
        scored.sort(key=lambda x: x[1], reverse=True)

        # Include 1-hop neighbors of top hits
        seen = {m.id for m, _ in scored}
        extras: List[Tuple[Moment, float]] = []
        index = self.graph.by_id()
        for m, score in scored[:3]:
            for n_id in self._neighbor_ids(m.id):
                if n_id in seen:
                    continue
                n = index.get(n_id)
                if n:
                    extras.append((n, max(0.25, score * 0.7)))
                    seen.add(n_id)
        scored.extend(extras)
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def link(
        self,
        source_id: str,
        target_id: str,
        *,
        kind: str = "related",
        reason: str = "",
        strength: float = 0.5,
    ) -> Optional[MomentLink]:
        with _LOCK:
            if source_id == target_id:
                return None
            for existing in self.graph.links:
                if {existing.source_id, existing.target_id} == {source_id, target_id} and existing.kind == kind:
                    existing.strength = max(existing.strength, strength)
                    if reason and reason not in existing.reason:
                        existing.reason = (existing.reason + "; " + reason)[:160]
                    self.graph.save()
                    return existing
            link = MomentLink.create(
                source_id, target_id, kind=kind, reason=reason, strength=strength
            )
            self.graph.links.append(link)
            self.graph.save()
            return link

    def resolve(self, moment_id: str) -> bool:
        with _LOCK:
            for m in self.graph.moments:
                if m.id == moment_id:
                    m.status = "resolved"
                    m.updated_at = _now()
                    self.graph.save()
                    return True
            return False

    # --- internals ---------------------------------------------------------

    def _extract_moments(
        self,
        user_text: str,
        assistant_text: str,
        *,
        session_id: str,
        protocols: List[str],
        affect: str,
        source: str = "extract",
    ) -> List[Moment]:
        text = user_text or ""
        if not text.strip():
            return []
        found: List[Moment] = []
        for rx, kind, title_prefix in _EVENT_PATTERNS:
            m = rx.search(text)
            if not m:
                continue
            # Third-party hospital shock ≠ personal health moment
            if kind == "health":
                try:
                    from lotus.speech.stated_facts import (
                        is_self_health_signal,
                        is_third_party_hospital,
                    )

                    if is_third_party_hospital(text) and not is_self_health_signal(text):
                        continue
                except Exception:
                    pass
            snippet = " ".join(text.split())[:180]
            # Specialize title
            title = f"{title_prefix}: {snippet[:80]}"
            proto = list(protocols)
            if kind == "grief" and "P3_grief" not in proto:
                proto.append("P3_grief")
            if kind == "health" and "P2_health" not in proto:
                proto.append("P2_health")
            if kind == "life_event" and "P4_major_event" not in proto:
                proto.append("P4_major_event")
            found.append(
                Moment.create(
                    kind=kind,
                    title=title,
                    summary=snippet,
                    session_id=session_id,
                    protocols=proto,
                    affect=affect,
                    source=source,
                    evidence=m.group(0)[:120],
                )
            )
        # Protocol-driven moment when patterns miss but protocol is clear
        if not found and protocols:
            for p in protocols:
                if p in {"P3_grief", "P2_health", "P4_major_event", "P1_depression"} and len(text) > 40:
                    kind_map = {
                        "P3_grief": "grief",
                        "P2_health": "health",
                        "P4_major_event": "life_event",
                        "P1_depression": "affect",
                    }
                    found.append(
                        Moment.create(
                            kind=kind_map[p],
                            title=f"Protocol moment ({p})",
                            summary=" ".join(text.split())[:180],
                            session_id=session_id,
                            protocols=[p],
                            affect=affect,
                            source=source,
                            evidence=text[:100],
                        )
                    )
                    break
        # Assistant offered revisit → thread
        if assistant_text and re.search(
            r"(?:we can (?:come back|return)|whenever you(?:'re| are) ready)",
            assistant_text,
            re.I,
        ):
            found.append(
                Moment.create(
                    kind="thread",
                    title="Assistant offered to revisit",
                    summary=" ".join((user_text or "").split())[:160] or "Hard topic left open",
                    session_id=session_id,
                    protocols=protocols,
                    affect=affect,
                    source="assistant",
                    evidence="revisit offer",
                )
            )
        return found

    def _merge_or_add(self, moment: Moment) -> Moment:
        tokens = set(moment.tokens)
        for existing in self.graph.moments:
            if existing.status == "resolved":
                continue
            overlap = len(tokens & set(existing.tokens))
            same_kind = existing.kind == moment.kind or {
                existing.kind,
                moment.kind,
            } <= {"life_event", "grief", "health", "conversation"}
            if overlap >= 2 and same_kind:
                # Merge into existing
                existing.updated_at = moment.updated_at
                existing.status = "active"
                for sid in moment.session_ids:
                    if sid and sid not in existing.session_ids:
                        existing.session_ids.append(sid)
                        existing.session_ids = existing.session_ids[-12:]
                for p in moment.protocols:
                    if p not in existing.protocols:
                        existing.protocols.append(p)
                for t in moment.tokens:
                    if t not in existing.tokens:
                        existing.tokens.append(t)
                existing.tokens = existing.tokens[:16]
                for e in moment.evidence:
                    if e and e not in existing.evidence:
                        existing.evidence.append(e)
                existing.evidence = existing.evidence[-8:]
                if len(moment.summary) > len(existing.summary):
                    existing.summary = moment.summary
                if moment.affect:
                    existing.affect = moment.affect
                for s in moment.sources:
                    if s not in existing.sources:
                        existing.sources.append(s)
                return existing
        self.graph.moments.append(moment)
        self.graph.moments = self.graph.moments[-200:]
        return moment

    def _auto_link(self, moment: Moment) -> None:
        tokens = set(moment.tokens)
        for other in self.graph.moments:
            if other.id == moment.id:
                continue
            overlap = tokens & set(other.tokens)
            if len(overlap) >= 2:
                kind = "same_theme"
                if moment.kind == "thread" or other.kind == "thread":
                    kind = "continues"
                if {"grief", "health", "life_event"} & {moment.kind, other.kind}:
                    kind = "related"
                self.link(
                    moment.id,
                    other.id,
                    kind=kind,
                    reason="shared themes: " + ", ".join(sorted(overlap)[:5]),
                    strength=min(0.95, 0.35 + 0.15 * len(overlap)),
                )
            # Same protocol cluster
            elif set(moment.protocols) & set(other.protocols) and moment.kind == other.kind:
                self.link(
                    moment.id,
                    other.id,
                    kind="related",
                    reason="same protocol cluster",
                    strength=0.4,
                )

    def _try_resolve(self, user_text: str) -> None:
        related = self.find_related(user_text, limit=2)
        for m, score in related:
            if score >= 0.35 and m.status in {"open", "active"}:
                m.status = "resolved"
                m.updated_at = _now()

    def _ingest_external_lists(
        self,
        *,
        session_id: str,
        protocols: List[str],
        affect: str,
    ) -> None:
        """Pull open_threads / shared_moments into the graph (bridge, don't duplicate forever)."""
        try:
            from lotus.continuity.state import ContinuityState
            from lotus.realtime.model import LivingUserModel

            cont = ContinuityState.load()
            for thread in (cont.open_threads or [])[-5:]:
                self._merge_or_add(
                    Moment.create(
                        kind="thread",
                        title=f"Thread: {thread[:80]}",
                        summary=thread[:200],
                        session_id=session_id or cont.last_session_id,
                        protocols=protocols or ([cont.last_protocol] if cont.last_protocol else []),
                        affect=affect or cont.last_affect,
                        source="continuity",
                        evidence=thread[:120],
                    )
                )
            for checkin in (cont.pending_checkins or [])[-3:]:
                self._merge_or_add(
                    Moment.create(
                        kind="checkin",
                        title=f"Check-in: {checkin[:80]}",
                        summary=checkin[:200],
                        session_id=session_id or cont.last_session_id,
                        source="continuity",
                        evidence=checkin[:120],
                    )
                )

            living = LivingUserModel.load()
            for sm in (living.shared_moments or [])[-5:]:
                self._merge_or_add(
                    Moment.create(
                        kind="conversation",
                        title=f"Shared: {sm[:80]}",
                        summary=sm[:200],
                        session_id=session_id,
                        protocols=list(living.active_protocols or protocols),
                        affect=affect or living.current_affect,
                        source="realtime",
                        evidence=sm[:120],
                    )
                )
            for anchor in (living.connection_anchors or [])[-4:]:
                self._merge_or_add(
                    Moment.create(
                        kind="anchor",
                        title=f"Anchor: {anchor[:80]}",
                        summary=anchor[:200],
                        session_id=session_id,
                        source="realtime",
                        evidence=anchor[:120],
                    )
                )
        except Exception:
            # Bridge is best-effort — never break the turn
            return

    def _neighbor_ids(self, moment_id: str) -> List[str]:
        out: List[str] = []
        for link in self.graph.links:
            if link.source_id == moment_id:
                out.append(link.target_id)
            elif link.target_id == moment_id:
                out.append(link.source_id)
        return out

    def _neighbor_titles(self, moment_id: str, limit: int = 3) -> List[str]:
        index = self.graph.by_id()
        titles = []
        for nid in self._neighbor_ids(moment_id):
            m = index.get(nid)
            if m:
                titles.append(m.title[:60])
            if len(titles) >= limit:
                break
        return titles


def get_moments() -> MomentsEngine:
    global _ENGINE
    with _LOCK:
        if _ENGINE is None:
            _ENGINE = MomentsEngine()
        return _ENGINE


def reset_moments() -> MomentsEngine:
    global _ENGINE
    with _LOCK:
        _ENGINE = MomentsEngine()
        return _ENGINE
