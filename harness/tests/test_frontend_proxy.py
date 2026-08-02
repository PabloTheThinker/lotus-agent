"""Smoke tests for the Lotus UI proxy (no live gateway required)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "frontend" / "server.py"


def _load_server(monkeypatch):
    monkeypatch.setenv("LOTUS_UI_SESSION_SECRET", "test-secret-key-for-hmac")
    monkeypatch.setenv("LOTUS_UI_HOST", "127.0.0.1")
    monkeypatch.setenv("API_SERVER_KEY", "gateway-key")
    spec = importlib.util.spec_from_file_location("lotus_frontend_server", SERVER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["lotus_frontend_server"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_session_token_roundtrip(monkeypatch):
    mod = _load_server(monkeypatch)
    token = mod._issue_session()
    assert mod._valid_session(token)
    assert not mod._valid_session("nope.bad")
    assert not mod._valid_session("")


def test_rate_limit(monkeypatch):
    monkeypatch.setenv("LOTUS_UI_RATE_LIMIT", "3")
    monkeypatch.setenv("LOTUS_UI_RATE_WINDOW", "60")
    mod = _load_server(monkeypatch)
    mod._rate_buckets.clear()
    client = "10.0.0.9"
    assert mod._rate_allow(client)
    assert mod._rate_allow(client)
    assert mod._rate_allow(client)
    assert not mod._rate_allow(client)


def test_chunk_text(monkeypatch):
    mod = _load_server(monkeypatch)
    assert mod._chunk_text("abcdef", 2) == ["ab", "cd", "ef"]


def test_health_json_shape(monkeypatch):
    """Exercise gateway probe failure path without a live server."""
    mod = _load_server(monkeypatch)
    ok, err = mod._gateway_ok()
    assert ok is False
    assert err


def test_crisis_payload_i18n(monkeypatch):
    mod = _load_server(monkeypatch)
    es = mod._crisis_payload("es", "GB")
    assert "Importas" in es["title"]
    assert "116 123" in es["body_html"]


def test_model_ready_false_without_config(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    mod = _load_server(monkeypatch)
    mod.HERMES_HOME = tmp_path
    ok, detail = mod._model_ready()
    assert ok is False
    assert "lotus setup" in detail


def test_journey_payload_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    mod = _load_server(monkeypatch)
    mod.HERMES_HOME = tmp_path
    data = mod._journey_payload()
    assert data["enabled"] is True
    assert data["active"] is False
