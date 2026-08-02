#!/usr/bin/env python3
"""L.O.T.U.S. web UI — static files + hardened proxy to Hermes API."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Deque, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parent
HERMES_API = os.environ.get("LOTUS_API_BASE", "http://127.0.0.1:8642/v1").rstrip("/")
API_KEY = os.environ.get("API_SERVER_KEY") or os.environ.get("LOTUS_API_KEY") or ""
HOST = os.environ.get("LOTUS_UI_HOST", "127.0.0.1")
PORT = int(os.environ.get("LOTUS_UI_PORT", "8787"))
MODEL = os.environ.get("LOTUS_MODEL", "hermes-agent")
RATE_LIMIT = int(os.environ.get("LOTUS_UI_RATE_LIMIT", "30"))  # requests / window
RATE_WINDOW = int(os.environ.get("LOTUS_UI_RATE_WINDOW", "60"))  # seconds
SESSION_SECRET = os.environ.get("LOTUS_UI_SESSION_SECRET") or secrets.token_hex(32)
BIND_WARN = HOST not in {"127.0.0.1", "localhost", "::1"}
HERMES_HOME = Path(
    os.environ.get("HERMES_HOME") or (Path.home() / ".hermes" / "profiles" / "lotus")
).expanduser()


def _journey_ui_enabled() -> bool:
    """Server allow-list for journey meter; client still opt-in via localStorage."""
    return os.environ.get("LOTUS_JOURNEY_UI", "1").lower() not in {"0", "false", "no", "off"}


def _crisis_payload(lang: str = "en", region: str = "US") -> dict:
    """Prefer harness single-source; fall back if lotus is not on PYTHONPATH."""
    try:
        harness = ROOT.parent / "harness"
        if str(harness) not in sys.path:
            sys.path.insert(0, str(harness))
        from lotus.guardrails import crisis_ui_payload

        return crisis_ui_payload(lang, region)
    except Exception:
        titles = {
            "en": "You matter — please reach a person now if you're in danger.",
            "es": "Importas — busca ayuda humana ahora si estás en peligro.",
            "fr": "Vous comptez — contactez une personne maintenant si vous êtes en danger.",
            "pt": "Você importa — procure ajuda humana agora se estiver em perigo.",
            "de": "Du bist wichtig — bitte hol dir jetzt menschliche Hilfe bei Gefahr.",
        }
        region_lines = {
            "US": 'US <a href="tel:988">988</a> / <a href="tel:911">911</a>',
            "CA": "Canada <strong>988</strong>",
            "GB": 'UK <a href="tel:116123">116 123</a>',
            "AU": "Australia Lifeline <strong>13 11 14</strong>",
            "NZ": "New Zealand <strong>1737</strong>",
            "IE": 'Ireland <a href="tel:116123">116 123</a>',
            "IN": "India AASRA <strong>91-9820466726</strong>",
        }
        key = (lang or "en").lower().split("-")[0]
        if key not in titles:
            key = "en"
        reg = (region or "US").upper()
        if reg not in region_lines:
            reg = "US"
        iasp = (
            '<a href="https://www.iasp.info/suicidalthoughts/" target="_blank" rel="noopener">'
            "IASP worldwide</a>"
        )
        return {
            "lang": key,
            "region": reg,
            "title": titles[key],
            "body_html": f"Local emergency services · {region_lines[reg]} · {iasp}",
        }


def _journey_payload() -> dict:
    path = HERMES_HOME / "memories" / "lotus-core" / "compound.json"
    if not path.is_file():
        return {"enabled": True, "active": False, "message": "No journey yet — keep talking."}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"enabled": True, "active": False, "message": "Journey unavailable."}
    missions = raw.get("missions") or []
    active_id = raw.get("active_mission_id") or ""
    mission = None
    for m in missions:
        if isinstance(m, dict) and m.get("id") == active_id:
            mission = m
            break
    if mission is None:
        for m in missions:
            if isinstance(m, dict) and m.get("status") == "active":
                mission = m
                break
    if not mission:
        return {"enabled": True, "active": False, "message": "No active mission yet."}
    meter = mission.get("meter") or {}
    cps = mission.get("checkpoints") or []
    return {
        "enabled": True,
        "active": True,
        "statement": str(mission.get("statement") or "")[:200],
        "status": str(mission.get("status") or ""),
        "ladder_rung": str(mission.get("current_ladder_rung") or ""),
        "meter": {
            "checkpoints_met": int(meter.get("checkpoints_met") or 0),
            "checkpoints_total": int(meter.get("checkpoints_total") or len(cps) or 0),
            "compound_score": float(meter.get("compound_score") or 0),
            "estimated_horizon": str(meter.get("estimated_horizon") or "unknown"),
            "center_met": bool(meter.get("center_met")),
            "guidance_unlocked": bool(meter.get("guidance_unlocked")),
        },
        "checkpoints": [
            {
                "title": str(c.get("title") or ""),
                "status": str(c.get("status") or ""),
                "is_center": bool(c.get("is_center")),
            }
            for c in cps
            if isinstance(c, dict)
        ][:12],
    }

_rate_lock = threading.Lock()
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def _gateway_ok() -> Tuple[bool, str]:
    url = HERMES_API.replace("/v1", "") + "/health"
    last = "unreachable"
    for probe in (f"{HERMES_API}/models", url):
        try:
            req = urllib.request.Request(probe, method="GET")
            if API_KEY:
                req.add_header("Authorization", f"Bearer {API_KEY}")
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if 200 <= resp.status < 300:
                    return True, ""
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            continue
    return False, last


def _model_ready() -> Tuple[bool, str]:
    """Best-effort: gateway /models non-empty, else profile config.yaml model.default."""
    try:
        req = urllib.request.Request(f"{HERMES_API}/models", method="GET")
        if API_KEY:
            req.add_header("Authorization", f"Bearer {API_KEY}")
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            data = body.get("data") if isinstance(body, dict) else None
            if isinstance(data, list) and data:
                return True, "gateway models available"
    except Exception:
        pass
    cfg = HERMES_HOME / "config.yaml"
    if cfg.is_file():
        try:
            text = cfg.read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.strip().startswith("default:"):
                    val = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return True, f"config model.default={val}"
        except OSError:
            pass
    env_path = HERMES_HOME / ".env"
    if env_path.is_file():
        try:
            raw = env_path.read_text(encoding="utf-8", errors="replace")
            keys = (
                "OPENROUTER_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "NOUS_API_KEY",
            )
            for line in raw.splitlines():
                if "=" not in line or line.strip().startswith("#"):
                    continue
                k, _, v = line.partition("=")
                if k.strip() in keys and v.strip():
                    return True, "provider key present (still run lotus setup if chat fails)"
        except OSError:
            pass
    return False, "no model yet — run: lotus setup"


def _prefs_payload() -> dict:
    path = HERMES_HOME / "memories" / "lotus-core" / "prefs.json"
    default = {"preferred_lang": "en", "crisis_regions": ["US", "INTL"]}
    if not path.is_file():
        return {**default, "source": "default"}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {**default, "source": "default"}
        return {
            "preferred_lang": str(raw.get("preferred_lang") or "en"),
            "crisis_regions": list(raw.get("crisis_regions") or ["US", "INTL"]),
            "source": "prefs.json",
        }
    except (json.JSONDecodeError, OSError):
        return {**default, "source": "default"}


def _issue_session() -> str:
    nonce = secrets.token_urlsafe(18)
    sig = hmac.new(SESSION_SECRET.encode(), nonce.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{nonce}.{sig}"


def _valid_session(token: Optional[str]) -> bool:
    if not token or "." not in token:
        return False
    nonce, sig = token.rsplit(".", 1)
    expect = hmac.new(SESSION_SECRET.encode(), nonce.encode(), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(sig, expect)


def _rate_allow(client: str) -> bool:
    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets[client]
        while bucket and now - bucket[0] > RATE_WINDOW:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT:
            return False
        bucket.append(now)
        return True


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[lotus-ui] {fmt % args}", file=__import__("sys").stderr)

    def _client_id(self) -> str:
        return self.client_address[0] if self.client_address else "unknown"

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Tuple[Optional[dict], Optional[str]]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}"), None
        except json.JSONDecodeError:
            return None, "Invalid JSON"

    def _require_session(self) -> bool:
        token = self.headers.get("X-Lotus-Session") or ""
        if _valid_session(token):
            return True
        self._json(401, {"error": "Missing or invalid session. Refresh the page."})
        return False

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            ok, err = _gateway_ok()
            model_ok, model_detail = _model_ready()
            self._json(
                200,
                {
                    "ok": True,
                    "gateway": ok,
                    "api_base": HERMES_API,
                    "error": None if ok else err,
                    "bind": HOST,
                    "streaming": True,
                    "journey_ui": _journey_ui_enabled(),
                    "setup_needed": not model_ok,
                    "setup_hint": None
                    if model_ok
                    else "Connect a model with Hermes: lotus setup  (or ./scripts/lotus-setup.sh)",
                    "model_detail": model_detail,
                },
            )
            return
        if path == "/api/session":
            self._json(200, {"token": _issue_session()})
            return
        if path == "/api/prefs":
            self._json(200, _prefs_payload())
            return
        if path == "/api/crisis":
            lang = "en"
            region = "US"
            if "?" in self.path:
                qs = self.path.split("?", 1)[1]
                for part in qs.split("&"):
                    if part.startswith("lang="):
                        lang = part.split("=", 1)[1] or "en"
                    if part.startswith("region="):
                        region = part.split("=", 1)[1] or "US"
            self._json(200, _crisis_payload(lang, region))
            return
        if path == "/api/journey":
            if not _journey_ui_enabled():
                self._json(200, {"enabled": False, "active": False})
                return
            self._json(200, _journey_payload())
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/api/prefs":
            if not self._require_session():
                return
            data, err = self._read_json()
            if err or data is None:
                self._json(400, {"error": err or "Invalid JSON"})
                return
            # Prefer harness prefs when importable; else write JSON directly
            try:
                import sys

                harness = HERMES_HOME / "harness"
                if harness.is_dir() and str(harness) not in sys.path:
                    sys.path.insert(0, str(harness))
                from lotus.prefs import get_prefs, reset_prefs, update_prefs  # type: ignore

                soft = bool(data.get("soft"))
                lang = data.get("preferred_lang")
                reset_prefs()
                current = get_prefs()
                kwargs = {}
                if lang is not None and str(lang).strip():
                    if soft and current.lang_locked:
                        pass  # never soft-overwrite an explicit user lock
                    else:
                        kwargs["preferred_lang"] = lang
                        kwargs["lang_locked"] = False if soft else True
                if data.get("crisis_regions") is not None:
                    kwargs["crisis_regions"] = data.get("crisis_regions")
                prefs = update_prefs(**kwargs) if kwargs else current
                self._json(
                    200,
                    {
                        "preferred_lang": prefs.preferred_lang,
                        "crisis_regions": prefs.crisis_regions,
                        "lang_locked": prefs.lang_locked,
                        "source": "prefs.json",
                    },
                )
                return
            except Exception:
                path_prefs = HERMES_HOME / "memories" / "lotus-core"
                path_prefs.mkdir(parents=True, exist_ok=True)
                payload = {
                    "preferred_lang": str(data.get("preferred_lang") or "en"),
                    "crisis_regions": list(data.get("crisis_regions") or ["US", "INTL"]),
                }
                (path_prefs / "prefs.json").write_text(
                    json.dumps(payload, indent=2) + "\n", encoding="utf-8"
                )
                self._json(200, {**payload, "source": "prefs.json"})
                return

        if path not in {"/api/chat", "/api/chat/stream"}:
            self.send_error(404)
            return
        if not self._require_session():
            return
        if not _rate_allow(self._client_id()):
            self._json(429, {"error": "Too many messages — take a breath and try again shortly."})
            return

        data, err = self._read_json()
        if err or data is None:
            self._json(400, {"error": err or "Invalid JSON"})
            return

        messages = data.get("messages") or []
        if not isinstance(messages, list) or not messages:
            self._json(400, {"error": "messages required"})
            return

        stream = path.endswith("/stream") or bool(data.get("stream"))
        payload = {
            "model": data.get("model") or MODEL,
            "messages": messages,
            "stream": stream,
        }
        headers = {
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}),
        }

        if stream:
            self._proxy_stream(payload, headers)
        else:
            self._proxy_once(payload, headers)

    def _proxy_once(self, payload: dict, headers: dict) -> None:
        req = urllib.request.Request(
            f"{HERMES_API}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self._json(exc.code, {"error": detail or str(exc)})
            return
        except Exception as exc:  # noqa: BLE001
            self._json(
                502,
                {
                    "error": (
                        f"{exc}. Start the Hermes gateway: "
                        "`./scripts/lotus-gateway.sh start`"
                    )
                },
            )
            return

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            self._json(502, {"error": "Unexpected gateway response", "raw": body})
            return
        self._json(200, {"content": content})

    def _proxy_stream(self, payload: dict, headers: dict) -> None:
        req = urllib.request.Request(
            f"{HERMES_API}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            upstream = urllib.request.urlopen(req, timeout=180)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            self._json(exc.code, {"error": detail or str(exc)})
            return
        except Exception as exc:  # noqa: BLE001
            self._json(
                502,
                {
                    "error": (
                        f"{exc}. Start the Hermes gateway: "
                        "`./scripts/lotus-gateway.sh start`"
                    )
                },
            )
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        # If upstream is not SSE (non-streaming model path), synthesize one event
        ctype = upstream.headers.get("Content-Type", "")
        try:
            if "text/event-stream" in ctype or "stream" in ctype:
                while True:
                    chunk = upstream.read(1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            else:
                body = json.loads(upstream.read().decode("utf-8"))
                content = body["choices"][0]["message"]["content"]
                # Fake SSE for clients that always prefer stream endpoint
                for piece in _chunk_text(content, 48):
                    data = json.dumps({"choices": [{"delta": {"content": piece}}]})
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
        except Exception as exc:  # noqa: BLE001
            err = json.dumps({"error": str(exc)})
            try:
                self.wfile.write(f"data: {err}\n\n".encode("utf-8"))
                self.wfile.flush()
            except Exception:  # noqa: BLE001
                pass
        finally:
            upstream.close()


def _chunk_text(text: str, size: int) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + size] for i in range(0, len(text), size)]


def main() -> None:
    if BIND_WARN and not API_KEY:
        print("Refusing non-loopback bind without API_SERVER_KEY.")
        raise SystemExit(2)
    if BIND_WARN:
        print(
            f"Warning: binding to {HOST} — ensure a reverse proxy and keep "
            "LOTUS_UI_SESSION_SECRET stable across restarts."
        )
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"L.O.T.U.S. UI → http://{HOST}:{PORT}")
    print(f"Proxying Hermes API → {HERMES_API}")
    print(f"Rate limit: {RATE_LIMIT}/{RATE_WINDOW}s · session tokens required")
    if not API_KEY:
        print("Warning: API_SERVER_KEY / LOTUS_API_KEY not set — gateway may reject requests.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
