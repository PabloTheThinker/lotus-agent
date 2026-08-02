"""User preferences — locale + crisis regions (companion UX, not clinical).

Grounded in IASP practice: always offer a path to human helplines
(https://www.iasp.info/suicidalthoughts / Find A Helpline) and prefer
region-relevant numbers when the user has set a locale/region.
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from lotus.realtime.paths import core_dir

_LOCK = threading.RLock()
_PREFS: Optional["UserPrefs"] = None

VALID_REGIONS = ("US", "CA", "GB", "AU", "NZ", "IE", "IN", "INTL")
VALID_LANGS = ("en", "es", "fr", "pt", "de")

# Strong lexical cues — not a full language detector; enough for soft prefs.
_LANG_CUES: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    ("es", re.compile(r"\b(?:quiero|estoy|me siento|ayuda|matar|vivir|deprimid[oa]|duelo)\b|[¿¡]", re.I)),
    ("fr", re.compile(r"\b(?:je veux|je suis|mourir|aide|déprim|deuil|triste)\b", re.I)),
    ("pt", re.compile(r"\b(?:quero|estou|morrer|ajuda|deprimid[oa]|luto)\b", re.I)),
    ("de", re.compile(r"\b(?:ich will|ich bin|sterben|hilfe|deprimiert|trauer)\b", re.I)),
)


def prefs_path() -> Path:
    return core_dir() / "prefs.json"


@dataclass
class UserPrefs:
    preferred_lang: str = "en"
    crisis_regions: List[str] = field(default_factory=lambda: ["US", "INTL"])
    lang_locked: bool = False  # True after explicit user/CLI/UI set
    updated_at: str = ""

    def normalize(self) -> "UserPrefs":
        lang = (self.preferred_lang or "en").lower().split("-")[0]
        self.preferred_lang = lang if lang in VALID_LANGS else "en"
        self.lang_locked = bool(self.lang_locked)
        regions: List[str] = []
        for r in self.crisis_regions or []:
            code = str(r).strip().upper()
            if code in VALID_REGIONS and code not in regions:
                regions.append(code)
        if "INTL" not in regions:
            regions.append("INTL")
        if not any(r != "INTL" for r in regions):
            regions.insert(0, "US")
        self.crisis_regions = regions
        return self

    def save(self) -> None:
        from datetime import datetime, timezone

        from lotus.schema import stamp

        self.normalize()
        self.updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        path = prefs_path()
        path.write_text(
            json.dumps(stamp(asdict(self), kind="prefs"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> "UserPrefs":
        path = prefs_path()
        if not path.is_file():
            return cls().normalize()
        try:
            from lotus.schema import ensure_schema

            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls().normalize()
        if not isinstance(raw, dict):
            return cls().normalize()
        raw = ensure_schema(raw, kind="prefs")
        return cls(
            preferred_lang=str(raw.get("preferred_lang") or "en"),
            crisis_regions=list(raw.get("crisis_regions") or ["US", "INTL"]),
            lang_locked=bool(raw.get("lang_locked")),
            updated_at=str(raw.get("updated_at") or ""),
        ).normalize()


def get_prefs() -> UserPrefs:
    global _PREFS
    with _LOCK:
        if _PREFS is None:
            _PREFS = UserPrefs.load()
        return _PREFS


def reset_prefs() -> UserPrefs:
    global _PREFS
    with _LOCK:
        _PREFS = UserPrefs.load()
        return _PREFS


def update_prefs(
    *,
    preferred_lang: Optional[str] = None,
    crisis_regions: Optional[Sequence[str]] = None,
    lang_locked: Optional[bool] = None,
) -> UserPrefs:
    with _LOCK:
        prefs = get_prefs()
        if preferred_lang is not None:
            prefs.preferred_lang = preferred_lang
            # Explicit set locks unless caller overrides
            prefs.lang_locked = True if lang_locked is None else bool(lang_locked)
        elif lang_locked is not None:
            prefs.lang_locked = bool(lang_locked)
        if crisis_regions is not None:
            prefs.crisis_regions = list(crisis_regions)
        prefs.save()
        return prefs


def detect_lang(text: str) -> Optional[str]:
    """Return a non-English lang code when strong cues match; else None."""
    raw = text or ""
    if len(raw.strip()) < 4:
        return None
    for code, rx in _LANG_CUES:
        if rx.search(raw):
            return code
    return None


_ENGLISH_HINT = re.compile(
    r"\b(i|i'm|i’m|i am|the|and|don't|dont|feel|want|here|with|that|this|just|hey)\b",
    re.I,
)


def _looks_english(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 8:
        return False
    return bool(_ENGLISH_HINT.search(t)) and detect_lang(t) is None


def maybe_autodetect_lang(text: str) -> Optional[str]:
    """Soft-update preferred_lang from message cues when not locked / not env-set.

    Never overrides ``LOTUS_PREFERRED_LANG`` or an explicit user lock.
    When unlocked, English-dominant turns soft-reset away from a prior cue lang
    so one Spanish message does not stick for the rest of the day.
    Returns the lang that was applied, or None.
    """
    env = os.environ.get("LOTUS_PREFERRED_LANG", "").strip().lower().split("-")[0]
    if env in VALID_LANGS:
        return None
    detected = detect_lang(text)
    with _LOCK:
        prefs = get_prefs()
        if prefs.lang_locked:
            return None
        if detected:
            if prefs.preferred_lang == detected:
                return None
            prefs.preferred_lang = detected
            prefs.lang_locked = False
            prefs.save()
            return detected
        if prefs.preferred_lang != "en" and _looks_english(text):
            prefs.preferred_lang = "en"
            prefs.lang_locked = False
            prefs.save()
            return "en"
        return None


def resolve_crisis_regions(
    override: Optional[Sequence[str]] = None,
) -> Tuple[str, ...]:
    """Order: explicit override → env LOTUS_CRISIS_REGIONS → prefs → default."""
    if override:
        chosen = [str(r).strip().upper() for r in override if str(r).strip()]
    else:
        env = os.environ.get("LOTUS_CRISIS_REGIONS", "").strip()
        if env:
            chosen = [p.strip().upper() for p in env.split(",") if p.strip()]
        else:
            chosen = list(get_prefs().crisis_regions)
    out: List[str] = []
    for code in chosen:
        if code in VALID_REGIONS and code not in out:
            out.append(code)
    if "INTL" not in out:
        out.append("INTL")
    if not out:
        out = ["US", "INTL"]
    return tuple(out)


def resolve_preferred_lang(override: Optional[str] = None) -> str:
    if override:
        lang = override.lower().split("-")[0]
        if lang in VALID_LANGS:
            return lang
    env = os.environ.get("LOTUS_PREFERRED_LANG", "").strip().lower().split("-")[0]
    if env in VALID_LANGS:
        return env
    return get_prefs().preferred_lang
