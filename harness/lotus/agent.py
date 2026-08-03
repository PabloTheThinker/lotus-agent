"""LotusAgent — specialized wrapper around Hermes AIAgent or Cursor CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .backends.cursor_cli import CursorCliBackend, default_cursor_model, resolve_backend
from .guardrails import SAFE_REFUSAL, assess_user_text, filter_model_output
from .prompts import build_ephemeral_system_prompt
from .protocols import Protocol, classify_protocol
from .realtime import get_core


class LotusAgent:
    """Mental-health specialized agent.

    Default backend is Hermes ``AIAgent``. Set ``backend=\"cursor\"`` or
    ``LOTUS_BACKEND=cursor`` to route turns through the Cursor Agent CLI
    (e.g. Grok 4.5 via ``cursor-grok-4.5-high-fast``).
    """

    def __init__(
        self,
        *,
        model: str = "",
        hermes_home: Optional[str] = None,
        quiet_mode: bool = True,
        max_iterations: int = 40,
        enabled_toolsets: Optional[List[str]] = None,
        backend: str = "",
        **agent_kwargs: Any,
    ) -> None:
        if hermes_home:
            os.environ["HERMES_HOME"] = str(Path(hermes_home).expanduser())

        self._ephemeral = ""
        self._model = model
        self._quiet = quiet_mode
        self._max_iterations = max_iterations
        self._enabled_toolsets = enabled_toolsets
        self._agent_kwargs = agent_kwargs
        self._agent = None
        self._backend = resolve_backend(backend)
        self._cursor: Optional[CursorCliBackend] = None

    def _import_ai_agent(self):
        try:
            from run_agent import AIAgent  # type: ignore
            return AIAgent
        except ImportError:
            pass
        # Common install layouts
        candidates = [
            Path(os.environ.get("HERMES_HOME", "")).expanduser() / "hermes-agent",
            Path.home() / ".hermes" / "hermes-agent",
            Path.home() / "praetor" / "hermes-agent",
        ]
        import sys

        for path in candidates:
            if path.is_dir() and str(path) not in sys.path:
                sys.path.insert(0, str(path))
                try:
                    from run_agent import AIAgent  # type: ignore
                    return AIAgent
                except ImportError:
                    continue
        raise ImportError(
            "Could not import Hermes AIAgent. Install Hermes Agent and ensure "
            "hermes-agent is importable, or set HERMES_HOME to a profile whose "
            "tree includes hermes-agent. Or use LOTUS_BACKEND=cursor."
        )

    def _ensure_agent(self, user_message: str, realtime_ctx: str = ""):
        AIAgent = self._import_ai_agent()
        self._ephemeral = build_ephemeral_system_prompt(
            user_message,
            realtime_context=realtime_ctx,
        )
        kwargs: Dict[str, Any] = {
            "quiet_mode": self._quiet,
            "max_iterations": self._max_iterations,
            "ephemeral_system_prompt": self._ephemeral,
            "platform": self._agent_kwargs.pop("platform", "lotus"),
        }
        if self._model:
            kwargs["model"] = self._model
        if self._enabled_toolsets is not None:
            kwargs["enabled_toolsets"] = self._enabled_toolsets
        kwargs.update(self._agent_kwargs)
        self._agent = AIAgent(**kwargs)
        return self._agent

    def _ensure_cursor(self) -> CursorCliBackend:
        if self._cursor is None:
            model = self._model or default_cursor_model()
            repo = Path(__file__).resolve().parents[2]
            self._cursor = CursorCliBackend(
                model=model,
                cwd=str(repo),
                mode=os.environ.get("LOTUS_CURSOR_MODE", "ask"),
                timeout_s=int(os.environ.get("LOTUS_CURSOR_TIMEOUT", "180")),
            )
        return self._cursor

    def classify(self, user_message: str) -> Protocol:
        return classify_protocol(user_message)

    def ask(self, user_message: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> str:
        """Run one user turn through the unified orchestrator + model backend."""
        safety = assess_user_text(user_message)
        # Hard stop on explicit method requests before tools/model can elaborate means
        if safety.method_request:
            return SAFE_REFUSAL

        from .compound import get_compound
        from .context import build_turn_context
        from .continuity import get_continuity
        from .moments import get_moments

        core = get_core()
        continuity = get_continuity()
        moments = get_moments()
        compound = get_compound()

        # Single inject path (same as lotus-realtime pre_llm_call).
        # While LotusAgent drives the turn, tell Hermes plugins to skip their
        # inject/learn hooks so we don't double-stack the same systems.
        prev_owns = os.environ.get("LOTUS_HARNESS_OWNS_TURN")
        os.environ["LOTUS_HARNESS_OWNS_TURN"] = "1"
        try:
            bundled = build_turn_context(
                user_message,
                history=conversation_history,
                is_first_turn=not conversation_history,
            )

            if self._backend == "cursor":
                text = self._ask_cursor(user_message, bundled, conversation_history)
            else:
                agent = self._ensure_agent(user_message, realtime_ctx=bundled)
                result = agent.run_conversation(
                    user_message,
                    conversation_history=conversation_history,
                )
                if isinstance(result, dict):
                    text = result.get("final_response") or result.get("response") or ""
                else:
                    text = str(result or "")

            text = filter_model_output(text)
            try:
                from .speech.flow import scrub_verbal_tics

                text = scrub_verbal_tics(text)
            except Exception:
                pass
            core.after_turn(user_message, text, history=conversation_history)
            living = core.model
            continuity.after_turn(
                user_message,
                text,
                history=conversation_history,
                living_affect=living.current_affect or "",
                living_protocol=(living.active_protocols or [""])[0],
            )
            moments.after_turn(
                user_message,
                text,
                protocols=list(living.active_protocols or []),
                affect=living.current_affect or "",
                history=conversation_history,
            )
            compound.after_turn(
                user_message,
                text,
                protocols=list(living.active_protocols or []),
                affect=living.current_affect or "",
                crisis=safety.inject_crisis_override,
                moment_ids=[m.id for m in moments.graph.moments[-5:]],
            )
            return text
        finally:
            if prev_owns is None:
                os.environ.pop("LOTUS_HARNESS_OWNS_TURN", None)
            else:
                os.environ["LOTUS_HARNESS_OWNS_TURN"] = prev_owns

    def _ask_cursor(
        self,
        user_message: str,
        bundled: str,
        conversation_history: Optional[List[Dict[str, Any]]],
    ) -> str:
        self._ephemeral = build_ephemeral_system_prompt(
            user_message,
            realtime_context=bundled,
        )
        backend = self._ensure_cursor()
        return backend.complete(
            user_message,
            system_prompt=self._ephemeral,
            history=conversation_history,
        )
