"""Integration smoke: Lotus UI proxy → mocked Hermes /v1 chat completions."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "frontend" / "server.py"


class _FakeHermes(BaseHTTPRequestHandler):
    def log_message(self, *args):  # noqa: ARG002
        return

    def do_GET(self):  # noqa: N802
        if self.path.endswith("/models"):
            body = json.dumps({"data": [{"id": "hermes-agent"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length)
        if not self.path.endswith("/chat/completions"):
            self.send_error(404)
            return
        payload = {
            "choices": [
                {"message": {"role": "assistant", "content": "I'm here with you."}}
            ]
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def fake_gateway():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeHermes)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/v1"
    server.shutdown()


def _load_ui(monkeypatch, api_base: str):
    monkeypatch.setenv("LOTUS_API_BASE", api_base)
    monkeypatch.setenv("LOTUS_UI_SESSION_SECRET", "integration-secret")
    monkeypatch.setenv("API_SERVER_KEY", "k")
    # Unique module name per load
    name = "lotus_frontend_server_int"
    spec = importlib.util.spec_from_file_location(name, SERVER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_ui_chat_roundtrip(monkeypatch, fake_gateway):
    mod = _load_ui(monkeypatch, fake_gateway)
    assert mod._gateway_ok()[0] is True

    ui = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
    port = ui.server_address[1]
    thread = threading.Thread(target=ui.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/session", timeout=3) as resp:
            token = json.loads(resp.read().decode())["token"]

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/chat",
            data=json.dumps(
                {"messages": [{"role": "user", "content": "hello"}]}
            ).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Lotus-Session": token,
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        assert data["content"] == "I'm here with you."
    finally:
        ui.shutdown()
