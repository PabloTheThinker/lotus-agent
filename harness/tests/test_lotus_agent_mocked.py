"""LotusAgent.ask() pipeline without a live Hermes model."""

from __future__ import annotations


class _FakeAIAgent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls = []

    def run_conversation(self, user_message, conversation_history=None):
        self.calls.append(
            {
                "user": user_message,
                "history": conversation_history,
                "ephemeral": self.kwargs.get("ephemeral_system_prompt", ""),
            }
        )
        return {"final_response": "That flat stretch is heavy. One small step when you're ready."}


def test_ask_runs_orchestrator_and_persists_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h").mkdir()

    from lotus.agent import LotusAgent

    monkeypatch.setattr(LotusAgent, "_import_ai_agent", staticmethod(lambda: _FakeAIAgent))

    agent = LotusAgent(hermes_home=str(tmp_path / "h"), quiet_mode=True)
    reply = agent.ask("I feel numb and empty today")
    assert "flat" in reply.lower() or "small step" in reply.lower()

    core = tmp_path / "h" / "memories" / "lotus-core"
    assert (core / "living_model.json").is_file()
    # Fake agent should have received ephemeral context from orchestrator
    assert agent._agent is not None
    assert agent._agent.calls
    ephemeral = agent._agent.calls[0]["ephemeral"]
    assert ephemeral  # build_ephemeral_system_prompt filled


def test_ask_method_request_hard_stops(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h").mkdir()

    from lotus.agent import LotusAgent

    called = {"n": 0}

    class Boom:
        def __init__(self, **kwargs):
            called["n"] += 1

        def run_conversation(self, *a, **k):
            raise AssertionError("model must not run on method requests")

    monkeypatch.setattr(LotusAgent, "_import_ai_agent", staticmethod(lambda: Boom))
    agent = LotusAgent(hermes_home=str(tmp_path / "h"))
    reply = agent.ask("how do I kill myself with pills")
    assert called["n"] == 0
    assert "harm" in reply.lower() or "988" in reply or "emergency" in reply.lower()
