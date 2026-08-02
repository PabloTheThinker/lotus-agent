"""RealtimeCore — understanding, learning, research; context via orchestrator."""

from __future__ import annotations

import threading
from typing import Optional, Sequence, Tuple

from .learning import LearningSubroutine
from .model import LivingUserModel
from .research_loop import ResearchSubroutine
from .understanding import UnderstandingSnapshot, UnderstandingSubroutine

_LOCK = threading.RLock()
_CORE: Optional["RealtimeCore"] = None


class RealtimeCore:
    """Continuous nervous system of L.O.T.U.S.

    Context injection is unified in ``lotus.context.build_turn_context``.
    This class owns understanding/learning/research + living model persistence.
    """

    def __init__(self) -> None:
        self.understanding = UnderstandingSubroutine()
        self.learning = LearningSubroutine()
        self.research = ResearchSubroutine()
        self.model = LivingUserModel.load()
        self._snap_cache_key: Optional[Tuple[str, int]] = None
        self._snap_cache: Optional[UnderstandingSnapshot] = None

    def get_or_read_snapshot(
        self,
        user_text: str,
        *,
        history: Optional[Sequence[dict]] = None,
    ) -> UnderstandingSnapshot:
        """Cache understanding for the current turn (pre-inject + post-turn share it)."""
        key = (user_text or "", len(history or []))
        if self._snap_cache is not None and self._snap_cache_key == key:
            return self._snap_cache
        snap = self.understanding.read(user_text, history=history, model=self.model)
        self._snap_cache_key = key
        self._snap_cache = snap
        return snap

    def clear_turn_snapshot(self) -> None:
        self._snap_cache_key = None
        self._snap_cache = None

    def before_turn(
        self,
        user_text: str,
        *,
        history: Optional[Sequence[dict]] = None,
        is_first_turn: bool = False,
        session_id: str = "",
    ) -> str:
        """Delegate to the context orchestrator (single inject path)."""
        with _LOCK:
            from lotus.context import build_turn_context

            return build_turn_context(
                user_text,
                history=history,
                is_first_turn=is_first_turn,
                session_id=session_id,
            )

    def after_turn(
        self,
        user_text: str,
        assistant_text: str,
        *,
        history: Optional[Sequence[dict]] = None,
    ) -> LivingUserModel:
        """Learn from the completed exchange and persist."""
        with _LOCK:
            from lotus.guardrails import assess_user_text

            snap = self.get_or_read_snapshot(user_text, history=history)
            regex_crisis = (
                assess_user_text(user_text).inject_crisis_override
                or snap.affect.valence == "crisis"
            )
            self.learning.integrate(
                self.model,
                snap,
                assistant_text=assistant_text,
                user_text=user_text,
            )
            try:
                from lotus.speech import apply_corrections_to_model

                apply_corrections_to_model(self.model, user_text)
            except Exception:
                pass
            try:
                from lotus.speech.patterns import learn_from_turn

                learn_from_turn(user_text, assistant_text)
            except Exception:
                pass
            try:
                from lotus.context import (
                    parse_and_apply_llm_extract,
                    parse_and_apply_llm_understand,
                )

                parse_and_apply_llm_extract(assistant_text)
                parse_and_apply_llm_understand(
                    assistant_text, regex_crisis=regex_crisis
                )
            except Exception:
                pass
            try:
                from lotus.profile import get_profile

                get_profile().after_turn(
                    user_text,
                    assistant_text,
                    living_model=self.model,
                    protocols=[p.value for p in snap.protocols],
                    affect=snap.affect.valence,
                    crisis=regex_crisis,
                )
            except Exception:
                pass
            self.research.sync_queue(self.model, snap)
            self.model.save()
            self.research.write_approaches_md(self.model)
            self.clear_turn_snapshot()
            return self.model

    def snapshot(
        self, user_text: str, history: Optional[Sequence[dict]] = None
    ) -> UnderstandingSnapshot:
        return self.get_or_read_snapshot(user_text, history=history)

    def reload(self) -> LivingUserModel:
        with _LOCK:
            self.model = LivingUserModel.load()
            self.clear_turn_snapshot()
            return self.model


def get_core() -> RealtimeCore:
    global _CORE
    with _LOCK:
        if _CORE is None:
            _CORE = RealtimeCore()
        return _CORE


def reset_core() -> RealtimeCore:
    global _CORE
    with _LOCK:
        _CORE = RealtimeCore()
        return _CORE
