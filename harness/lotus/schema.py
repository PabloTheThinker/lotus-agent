"""Schema versioning + soft migrations for lotus-core JSON state."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, MutableMapping

SCHEMA_VERSIONS = {
    "living_model": 2,
    "continuity": 2,
    "moments": 2,
    "compound": 2,
    "profile": 2,
    "prefs": 1,
}


def ensure_schema(
    data: MutableMapping[str, Any],
    *,
    kind: str,
    migrate: Callable[[MutableMapping[str, Any], int], MutableMapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Normalize loaded JSON; run migrate(data, from_version) when behind.

    Uses ``_schema_version`` only (not payload ``version`` fields used by
    moments/compound graphs).
    """
    target = SCHEMA_VERSIONS.get(kind, 1)
    raw_ver = data.get("_schema_version", 1)
    try:
        current = int(raw_ver)
    except (TypeError, ValueError):
        current = 1
    if current < target:
        migrator = migrate or _default_migrate(kind)
        if migrator is not None:
            data = migrator(data, current)
    data["_schema_version"] = target
    return dict(data)


def stamp(payload: Dict[str, Any], *, kind: str) -> Dict[str, Any]:
    out = dict(payload)
    out["_schema_version"] = SCHEMA_VERSIONS.get(kind, 1)
    return out


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def migrate_living_model(data: MutableMapping[str, Any], from_version: int) -> MutableMapping[str, Any]:
    out = dict(data)
    for key in (
        "successful_moves",
        "grounding_tools_that_work",
        "preferred_language",
        "avoided_language",
        "user_phrases",
        "user_metaphors",
        "connection_anchors",
        "shared_moments",
        "triggers",
        "strengths",
        "open_gaps",
        "research_queue",
        "active_protocols",
        "affect_history",
    ):
        if key in out:
            out[key] = _as_list(out.get(key))
        elif from_version < 2:
            out.setdefault(key, [])
    out.setdefault("turn_count", 0)
    out.setdefault("current_affect", "neutral")
    out.setdefault("current_intensity", 0.0)
    return out


def migrate_continuity(data: MutableMapping[str, Any], from_version: int) -> MutableMapping[str, Any]:
    out = dict(data)
    for key in (
        "open_threads",
        "pending_checkins",
        "warmth_notes",
        "memory_promotions",
    ):
        if key in out or from_version < 2:
            out[key] = _as_list(out.get(key))
    out.setdefault("session_count", 0)
    out.setdefault("resume_summary", "")
    return out


def migrate_moments(data: MutableMapping[str, Any], from_version: int) -> MutableMapping[str, Any]:
    out = dict(data)
    out["moments"] = [m for m in _as_list(out.get("moments")) if isinstance(m, dict)]
    out["links"] = [link for link in _as_list(out.get("links")) if isinstance(link, dict)]
    if from_version < 2:
        for m in out["moments"]:
            m.setdefault("status", "open")
            m.setdefault("tokens", [])
            m.setdefault("protocols", [])
    out.setdefault("version", 1)
    return out


def migrate_compound(data: MutableMapping[str, Any], from_version: int) -> MutableMapping[str, Any]:
    out = dict(data)
    out["missions"] = [m for m in _as_list(out.get("missions")) if isinstance(m, dict)]
    out["records"] = [r for r in _as_list(out.get("records")) if isinstance(r, dict)]
    out.setdefault("active_mission_id", "")
    out.setdefault("version", 1)
    if from_version < 2:
        for m in out["missions"]:
            m.setdefault("status", "active")
            m.setdefault("checkpoints", [])
            if "meter" not in m or not isinstance(m.get("meter"), dict):
                m["meter"] = {
                    "checkpoints_met": 0,
                    "checkpoints_total": 0,
                    "compound_score": 0.0,
                    "estimated_horizon": "unknown",
                    "center_met": False,
                    "guidance_unlocked": False,
                    "progress_count": 0,
                    "stall_count": 0,
                }
    return out


def migrate_profile(data: MutableMapping[str, Any], from_version: int) -> MutableMapping[str, Any]:
    out = dict(data)
    # Pronouns removed from product surface — drop stale field
    out.pop("pronouns", None)
    for key in (
        "roles",
        "presenting_concerns",
        "stressors",
        "supports",
        "strengths",
        "coping_that_helps",
        "coping_that_harms",
        "language_helps",
        "language_harms",
        "metaphors",
        "open_moments",
        "working_hypotheses",
        "open_questions",
        "what_not_to_miss",
        "lotus_notes",
        "memory_candidates",
        "active_protocols",
    ):
        if key in out or from_version < 2:
            out[key] = _as_list(out.get(key))
    out.setdefault("preferred_name", "")
    out.setdefault("how_to_address", "")
    out.setdefault("confidence", "low")
    out.setdefault("turn_count", 0)
    return out


def migrate_prefs(data: MutableMapping[str, Any], from_version: int) -> MutableMapping[str, Any]:
    out = dict(data)
    out.setdefault("preferred_lang", "en")
    out.setdefault("lang_locked", False)
    regions = _as_list(out.get("crisis_regions"))
    out["crisis_regions"] = [str(r).upper() for r in regions if r]
    if from_version < 1:
        out.setdefault("updated_at", "")
    return out


_MIGRATE = {
    "living_model": migrate_living_model,
    "continuity": migrate_continuity,
    "moments": migrate_moments,
    "compound": migrate_compound,
    "profile": migrate_profile,
    "prefs": migrate_prefs,
}


def _default_migrate(
    kind: str,
) -> Callable[[MutableMapping[str, Any], int], MutableMapping[str, Any]] | None:
    return _MIGRATE.get(kind)
