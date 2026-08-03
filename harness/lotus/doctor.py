"""Environment / install health checks for L.O.T.U.S."""

from __future__ import annotations

import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    level: str = "error"  # error | warn | ok


@dataclass
class DoctorReport:
    checks: List[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok or c.level == "warn" for c in self.checks)

    @property
    def errors(self) -> List[Check]:
        return [c for c in self.checks if not c.ok and c.level == "error"]

    def render(self) -> str:
        lines = ["L.O.T.U.S. doctor", ""]
        for c in self.checks:
            mark = "✓" if c.ok else ("⚠" if c.level == "warn" else "✗")
            lines.append(f"  {mark} {c.name}: {c.detail}")
        lines.append("")
        if self.errors:
            lines.append(f"{len(self.errors)} issue(s) need attention before full use.")
            if any(c.name == "model_provider" for c in self.errors):
                lines.append("Connect a model with Hermes:  lotus setup")
                lines.append("Web UI shows a setup banner until a model is connected.")
        else:
            lines.append("Core checks passed. Companion surfaces are ready.")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": [
                {"name": c.name, "detail": c.detail, "level": c.level}
                for c in self.errors
            ],
            "checks": [
                {
                    "name": c.name,
                    "ok": c.ok,
                    "detail": c.detail,
                    "level": c.level,
                }
                for c in self.checks
            ],
        }


def _profile_home(hermes_home: Optional[str] = None) -> Path:
    raw = hermes_home or os.environ.get("HERMES_HOME") or str(
        Path.home() / ".hermes" / "profiles" / "lotus"
    )
    return Path(raw).expanduser()


def _load_dotenv(path: Path) -> dict:
    env: dict = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _probe_gateway(api_base: str, api_key: str) -> tuple[bool, str]:
    base = api_base.rstrip("/")
    probes = [f"{base}/models", base.replace("/v1", "") + "/health"]
    last = "unreachable"
    for url in probes:
        try:
            req = urllib.request.Request(url, method="GET")
            if api_key:
                req.add_header("Authorization", f"Bearer {api_key}")
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if 200 <= resp.status < 300:
                    return True, url
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
    return False, last


def run_doctor(hermes_home: Optional[str] = None) -> DoctorReport:
    report = DoctorReport()
    home = _profile_home(hermes_home)
    env_file = home / ".env"
    dotenv = _load_dotenv(env_file)

    # Prefer process env over file for live overrides
    def get(k: str, default: str = "") -> str:
        return os.environ.get(k) or dotenv.get(k, default)

    # Hermes CLI
    hermes = shutil.which("hermes") or shutil.which("lotus")
    report.checks.append(
        Check(
            "hermes_cli",
            bool(hermes),
            f"found at {hermes}" if hermes else "hermes/lotus not on PATH",
        )
    )

    # Profile
    report.checks.append(
        Check(
            "profile_home",
            home.is_dir() and (home / "SOUL.md").is_file(),
            str(home) if home.is_dir() else f"missing profile at {home}",
        )
    )

    # .env
    report.checks.append(
        Check(
            "env_file",
            env_file.is_file(),
            str(env_file) if env_file.is_file() else f"missing {env_file} — copy .env.template",
        )
    )

    # Model / provider — Hermes `lotus setup` is the supported path (writes .env + config)
    provider = any(
        get(k)
        for k in (
            "OPENROUTER_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "NOUS_API_KEY",
            "HERMES_API_KEY",
        )
    )
    model_default = ""
    config_path = home / "config.yaml"
    if config_path.is_file():
        try:
            import yaml  # type: ignore

            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            model_default = str((cfg.get("model") or {}).get("default") or "").strip()
        except Exception:  # noqa: BLE001
            model_default = ""

    model_ready = bool(provider or model_default)
    if model_ready:
        detail = (
            f"model configured ({model_default})"
            if model_default
            else "provider API key present (via Hermes setup / .env)"
        )
    else:
        detail = "no model yet — run: lotus setup   (or: lotus setup model)"
    report.checks.append(
        Check(
            "model_provider",
            model_ready,
            detail,
            level="error" if not model_ready else "ok",
        )
    )

    api_enabled = get("API_SERVER_ENABLED", "").lower() in {"1", "true", "yes", "on"}
    api_key = get("API_SERVER_KEY") or get("LOTUS_API_KEY")
    report.checks.append(
        Check(
            "api_server_config",
            api_enabled and bool(api_key),
            (
                "API_SERVER_ENABLED + API_SERVER_KEY set"
                if api_enabled and api_key
                else "set API_SERVER_ENABLED=true and API_SERVER_KEY for Lotus UI"
            ),
            level="warn" if not (api_enabled and api_key) else "ok",
        )
    )

    # Harness import
    try:
        from lotus.guardrails import assess_user_text  # noqa: F401
        from lotus.realtime.core import RealtimeCore  # noqa: F401

        report.checks.append(Check("harness_import", True, "lotus harness importable"))
    except Exception as exc:  # noqa: BLE001
        report.checks.append(
            Check(
                "harness_import",
                False,
                f"cannot import lotus harness ({exc}) — run ./install.sh or pip install -e harness/",
            )
        )

    # Plugins present
    plugins = home / "plugins"
    needed = [
        "lotus-safety",
        "lotus-realtime",
        "lotus-continuity",
        "lotus-moments",
        "lotus-compound",
        "lotus-profile",
    ]
    missing = [p for p in needed if not (plugins / p).is_dir()]
    report.checks.append(
        Check(
            "plugins",
            not missing,
            "all lotus plugins present" if not missing else f"missing: {', '.join(missing)}",
        )
    )

    # Moments + compound imports
    try:
        from lotus.moments import MomentsGraph  # noqa: F401

        report.checks.append(Check("moments", True, "moments connection system importable"))
    except Exception as exc:  # noqa: BLE001
        report.checks.append(
            Check("moments", False, f"moments import failed ({exc})", level="warn")
        )
    try:
        from lotus.compound import CompoundState  # noqa: F401

        report.checks.append(Check("compound", True, "compounding mission system importable"))
    except Exception as exc:  # noqa: BLE001
        report.checks.append(
            Check("compound", False, f"compound import failed ({exc})", level="warn")
        )
    try:
        from lotus.profile import InternalProfile  # noqa: F401

        report.checks.append(Check("profile", True, "internal user profile importable"))
    except Exception as exc:  # noqa: BLE001
        report.checks.append(
            Check("profile", False, f"profile import failed ({exc})", level="warn")
        )

    # Skin / theme
    skin = (home / "skins" / "lotus.yaml").is_file()
    theme = (home / "dashboard-themes" / "lotus.yaml").is_file()
    report.checks.append(
        Check(
            "branding",
            skin and theme,
            "lotus skin + dashboard theme installed"
            if skin and theme
            else "run ./install.sh (or lotus update) to copy skins/dashboard-themes",
            level="warn" if not (skin and theme) else "ok",
        )
    )

    # Companion-lean profile (Hermes core-toolset efficiency — local/weaker models)
    lean_ok, lean_detail = _check_companion_lean(home)
    report.checks.append(
        Check(
            "companion_lean",
            lean_ok,
            lean_detail,
            level="ok" if lean_ok else "warn",
        )
    )

    # Gateway reachability
    api_base = get("LOTUS_API_BASE") or f"http://127.0.0.1:{get('API_SERVER_PORT', '8642')}/v1"
    gw_ok, gw_detail = _probe_gateway(api_base, api_key)
    report.checks.append(
        Check(
            "gateway",
            gw_ok,
            f"reachable ({gw_detail})" if gw_ok else f"not running ({gw_detail}) — lotus gateway start",
            level="warn",
        )
    )

    # OpenMed optional (opt-in via doctor recommendation)
    openmed_disabled = get("LOTUS_OPENMED_DISABLE", "").lower() in {"1", "true", "yes", "on"}
    try:
        import openmed  # type: ignore  # noqa: F401

        detail = "installed — NER/PII structure pass available"
        if openmed_disabled:
            detail += " (disabled by LOTUS_OPENMED_DISABLE)"
        report.checks.append(Check("openmed", True, detail, level="ok"))
    except ImportError:
        report.checks.append(
            Check(
                "openmed",
                True,
                "not installed — glossary fallback active. "
                "Opt-in: pip install 'lotus-harness[openmed]' (or openmed) in the harness venv",
                level="warn",
            )
        )

    # Context orchestrator budget
    budget = get("LOTUS_CONTEXT_BUDGET_CHARS") or "12000"
    try:
        budget_n = int(budget)
        budget_ok = budget_n >= 2000
    except ValueError:
        budget_n = 0
        budget_ok = False
    report.checks.append(
        Check(
            "context_budget",
            budget_ok,
            f"LOTUS_CONTEXT_BUDGET_CHARS={budget}"
            + ("" if budget_ok else " — set to an integer ≥ 2000"),
            level="ok" if budget_ok else "warn",
        )
    )

    llm_extract = get("LOTUS_LLM_EXTRACT", "").lower() in {"1", "true", "yes", "on"}
    report.checks.append(
        Check(
            "llm_extract",
            True,
            "LOTUS_LLM_EXTRACT on (gated structured extract)"
            if llm_extract
            else "LOTUS_LLM_EXTRACT off (regex extract only) — set=1 to opt in",
            level="ok",
        )
    )

    llm_understand = get("LOTUS_LLM_UNDERSTAND", "").lower() in {"1", "true", "yes", "on"}
    report.checks.append(
        Check(
            "llm_understand",
            True,
            "LOTUS_LLM_UNDERSTAND on (enrich crisis/ambiguous turns)"
            if llm_understand
            else "LOTUS_LLM_UNDERSTAND off — set=1 to opt in for hard turns",
            level="ok",
        )
    )

    session_secret = get("LOTUS_UI_SESSION_SECRET")
    report.checks.append(
        Check(
            "ui_session_secret",
            bool(session_secret),
            "LOTUS_UI_SESSION_SECRET set (stable across UI restarts)"
            if session_secret
            else "unset — UI regenerates secret each restart (re-run ./install.sh)",
            level="ok" if session_secret else "warn",
        )
    )

    # Research pulse cron
    cron_ok, cron_detail = _check_research_cron()
    report.checks.append(
        Check(
            "research_cron",
            cron_ok,
            cron_detail,
            level="ok" if cron_ok else "warn",
        )
    )

    pulse_ok, pulse_detail = _check_research_pulse_artifact(home)
    report.checks.append(
        Check(
            "research_pulse_artifact",
            True,
            pulse_detail,
            level="ok" if pulse_ok else "warn",
        )
    )

    # Honcho — Hermes memory provider (optional)
    try:
        from lotus.honcho import honcho_status

        honcho_ok, honcho_detail = honcho_status(home)
        report.checks.append(
            Check(
                "honcho",
                True,
                honcho_detail if honcho_ok else honcho_detail,
                level="ok" if honcho_ok else "warn",
            )
        )
    except Exception as exc:  # noqa: BLE001
        report.checks.append(
            Check("honcho", True, f"status unavailable ({exc})", level="warn")
        )

    try:
        from lotus.privacy import summarize_core

        st = summarize_core()
        report.checks.append(
            Check(
                "lotus_core_privacy",
                True,
                (
                    f"{st['file_count']} files / {st['bytes']}b in lotus-core — "
                    "export: lotus-harness privacy export · wipe: privacy wipe --yes"
                ),
                level="ok",
            )
        )
    except Exception as exc:  # noqa: BLE001
        report.checks.append(
            Check("lotus_core_privacy", True, f"unavailable ({exc})", level="warn")
        )

    return report


def _check_companion_lean(home: Path) -> tuple[bool, str]:
    """Warn when coding-agent toolsets/skills re-bloat the lotus profile."""
    import re

    wanted = {"browser", "delegation", "code_execution", "terminal", "file"}
    cfg_text = ""
    cfg_path = home / "config.yaml"
    if cfg_path.is_file():
        try:
            cfg_text = cfg_path.read_text(encoding="utf-8")
        except OSError:
            cfg_text = ""

    disabled: set[str] = set()
    in_block = False
    for line in cfg_text.splitlines():
        if re.match(r"^\s*disabled_toolsets\s*:", line):
            in_block = True
            continue
        if in_block:
            m = re.match(r"^\s*-\s*([A-Za-z0-9_-]+)\s*$", line)
            if m:
                disabled.add(m.group(1))
                continue
            if re.match(r"^\S", line) or (
                line.strip() and not line.strip().startswith("-") and ":" in line
            ):
                in_block = False

    missing_disable = sorted(wanted - disabled)

    foreign_packs = []
    skills = home / "skills"
    if skills.is_dir():
        for name in (
            "apple",
            "autonomous-ai-agents",
            "creative",
            "email",
            "github",
            "media",
            "mlops",
            "note-taking",
            "productivity",
            "research",
            "smart-home",
            "social-media",
            "software-development",
        ):
            if (skills / name).is_dir():
                foreign_packs.append(name)

    if not missing_disable and not foreign_packs:
        return (
            True,
            "companion-lean: heavy toolsets disabled + lotus-only skills "
            "(re-enable via lotus tools; measure: lotus prompt-size)",
        )

    bits = []
    if missing_disable:
        bits.append(
            "enable agent.disabled_toolsets for "
            + ", ".join(missing_disable)
            + " (or ./install.sh)"
        )
    if foreign_packs:
        bits.append(
            f"{len(foreign_packs)} Hermes skill pack(s) present — "
            "run ./install.sh or lotus update to prune"
        )
    return False, "; ".join(bits)


def _check_research_cron() -> tuple[bool, str]:
    import subprocess

    hermes = shutil.which("hermes") or shutil.which("lotus")
    if not hermes:
        return False, "hermes not on PATH — cannot verify lotus-research-pulse"
    try:
        proc = subprocess.run(
            [hermes, "-p", "lotus", "cron", "list"],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"cron list failed ({exc})"
    out = (proc.stdout or "") + (proc.stderr or "")
    if "lotus-research-pulse" in out.lower():
        return True, "lotus-research-pulse scheduled"
    if proc.returncode != 0 and not out.strip():
        return False, "cron list unavailable — schedule via ./install.sh"
    return False, "lotus-research-pulse not found — re-run ./install.sh"


def _check_research_pulse_artifact(home: Path) -> tuple[bool, str]:
    """Warn when cron is the only signal — no approaches / research log yet."""
    core = home / "memories" / "lotus-core"
    log = core / "research_log.jsonl"
    approaches = core / "APPROACHES.md"
    living = core / "living_model.json"
    bits: list[str] = []
    if log.is_file() and log.stat().st_size > 2:
        bits.append(f"research_log.jsonl ({log.stat().st_size}b)")
    if approaches.is_file():
        text = approaches.read_text(encoding="utf-8", errors="ignore")
        if "No approaches stored yet" not in text and "## " in text:
            bits.append("APPROACHES.md has entries")
    n_approaches = 0
    if living.is_file():
        try:
            import json

            raw = json.loads(living.read_text(encoding="utf-8"))
            n_approaches = len(raw.get("help_approaches") or [])
        except (json.JSONDecodeError, OSError):
            pass
    if n_approaches:
        bits.append(f"{n_approaches} help_approaches in living model")
    if bits:
        return True, "research artifacts present: " + "; ".join(bits)
    return (
        False,
        "no research artifacts yet — run lotus-harness research-seed or wait for cron pulse",
    )
