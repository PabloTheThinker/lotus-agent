"""ContinuityEngine — session bridge + memory sync (Hermes hook-friendly)."""

from __future__ import annotations

import re
import threading
from typing import Optional, Sequence

from .state import ContinuityState

_LOCK = threading.RLock()
_ENGINE: Optional["ContinuityEngine"] = None

_OPEN_THREAD_RE = re.compile(
    r"(?:we(?:'ll| will) (?:talk|come back)|later|not ready|another time|"
    r"i'll think|still figuring|unfinished|more to say)",
    re.I,
)
_CHECKIN_RE = re.compile(
    r"(?:check (?:in|back)|remind me|ask me (?:later|tomorrow|next time)|"
    r"follow up|how (?:am|are) i doing)",
    re.I,
)
# Durable prefs only — NOT transient states ("i'm drunk", "i'm tired")
_PREF_RE = re.compile(
    r"(?:i (?:prefer|like|hate|don't like|do not like|dont like)\b|"
    r"call me \w+|my name is \w+|"
    r"please (?:don'?t|dont) (?:lecture|say|call)|"
    r"don'?t (?:want|give) (?:me )?(?:advice|a lecture|homework))",
    re.I,
)
_QUESTION_LEFT_RE = re.compile(r"\?\s*$")


class ContinuityEngine:
    """Keeps connection alive across sessions — Hermes-native, file-backed."""

    def __init__(self) -> None:
        self.state = ContinuityState.load()

    def on_session_start(
        self,
        *,
        session_id: str = "",
        platform: str = "",
    ) -> None:
        with _LOCK:
            self.state = ContinuityState.load()
            self.state.session_count += 1
            self.state.last_session_id = session_id or self.state.last_session_id
            self.state.last_platform = platform or self.state.last_platform
            self.state.turn_in_session = 0
            self.state.touch()
            self.state.save()

    def before_turn(
        self,
        user_text: str,
        *,
        is_first_turn: bool = False,
        session_id: str = "",
        living_affect: str = "",
        living_protocol: str = "",
    ) -> str:
        """Ephemeral continuity context for pre_llm_call."""
        with _LOCK:
            self.state.turn_in_session += 1
            if living_affect:
                self.state.last_affect = living_affect
            if living_protocol:
                self.state.last_protocol = living_protocol
            if session_id:
                self.state.last_session_id = session_id

            lines = [
                "[L.O.T.U.S. CONTINUITY — connection across time]",
                f"session_turns={self.state.turn_in_session} lifetime_sessions={self.state.session_count}",
            ]
            if is_first_turn or self.state.turn_in_session <= 1:
                lines.append("Returning / opening: greet with continuity, not a cold restart.")
                if self.state.resume_summary:
                    lines.append(f"resume_card: {self.state.resume_summary}")
                if self.state.open_threads:
                    lines.append(
                        "open_threads: " + "; ".join(self.state.open_threads[-5:])
                    )
                if self.state.pending_checkins:
                    lines.append(
                        "pending_checkins: " + "; ".join(self.state.pending_checkins[-4:])
                    )
                if self.state.warmth_notes:
                    lines.append(
                        "warmth: " + "; ".join(self.state.warmth_notes[-4:])
                    )
                lines.append(
                    "Offer one gentle bridge to last time only if it fits — never force recall."
                )
            else:
                lines.append("Mid-session: keep the thread; update open loops silently.")

            if self.state.memory_promotions:
                lines.append(
                    f"memory_sync_pending={len(self.state.memory_promotions)} "
                    "(promote stable prefs to USER.md via memory tool when appropriate)"
                )

            lines.append(
                "Hermes pattern: this block is ephemeral user-context — durable facts go to "
                "USER.md/MEMORY.md via memory tool; session bridge stays in lotus-core."
            )
            self.state.save()
            return "\n".join(lines)

    def after_turn(
        self,
        user_text: str,
        assistant_text: str,
        *,
        history: Optional[Sequence[dict]] = None,
        living_affect: str = "",
        living_protocol: str = "",
    ) -> ContinuityState:
        with _LOCK:
            if living_affect:
                self.state.last_affect = living_affect
            if living_protocol:
                self.state.last_protocol = living_protocol

            self._capture_threads(user_text, assistant_text)
            self._capture_promotions(user_text)
            self._refresh_resume(user_text, assistant_text)
            self.state.save()
            return self.state

    def on_session_end(self, *, completed: bool = True) -> None:
        with _LOCK:
            if not self.state.resume_summary and self.state.open_threads:
                self.state.resume_summary = (
                    "Open threads: " + "; ".join(self.state.open_threads[-3:])
                )
            note = "Session paused — hold the bond; resume without erasing what mattered."
            if note not in self.state.warmth_notes:
                self.state.warmth_notes.append(note)
                self.state.warmth_notes = self.state.warmth_notes[-8:]
            self.state.touch()
            self.state.save()

    def _capture_threads(self, user_text: str, assistant_text: str) -> None:
        u = user_text or ""
        a = assistant_text or ""
        if _OPEN_THREAD_RE.search(u) or _OPEN_THREAD_RE.search(a):
            snippet = " ".join(u.split())[:140]
            if snippet:
                self.state.remember_thread(f"user left open: {snippet}")
        if _CHECKIN_RE.search(u):
            self.state.remember_checkin(" ".join(u.split())[:120])
        # Unanswered user question → open thread
        if _QUESTION_LEFT_RE.search(u.strip()) and len(u) < 200:
            self.state.remember_thread(f"question: {u.strip()[:140]}")
        # Assistant offered to revisit
        if re.search(r"(?:we can (?:come back|return)|whenever you(?:'re| are) ready)", a, re.I):
            self.state.remember_thread("assistant offered to revisit a hard topic")

    def _capture_promotions(self, user_text: str) -> None:
        for m in _PREF_RE.finditer(user_text or ""):
            frag = m.group(0).strip()
            if 8 <= len(frag) <= 120:
                self.state.queue_promotion("user_preference", frag)

    def _refresh_resume(self, user_text: str, assistant_text: str) -> None:
        affect = self.state.last_affect or "unknown"
        proto = self.state.last_protocol or "general"
        user_bit = " ".join((user_text or "").split())[:100]
        self.state.resume_summary = (
            f"Last felt {affect} under {proto}. They said≈ {user_bit or '…'}"
        )
        # Warmth: short collaborative note
        if re.search(r"\b(thank|grateful|helped|better)\b", user_text or "", re.I):
            self.state.warmth_notes.append("They expressed that something helped — honor that continuity.")
            self.state.warmth_notes = self.state.warmth_notes[-8:]

    def reload(self) -> ContinuityState:
        with _LOCK:
            self.state = ContinuityState.load()
            return self.state


def get_continuity() -> ContinuityEngine:
    global _ENGINE
    with _LOCK:
        if _ENGINE is None:
            _ENGINE = ContinuityEngine()
        return _ENGINE


def reset_continuity() -> ContinuityEngine:
    global _ENGINE
    with _LOCK:
        _ENGINE = ContinuityEngine()
        return _ENGINE
