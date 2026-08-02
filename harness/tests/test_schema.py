"""JSON schema migrations for lotus-core state."""

from lotus.schema import SCHEMA_VERSIONS, ensure_schema, stamp


def test_stamp_sets_schema_version():
    out = stamp({"foo": 1}, kind="living_model")
    assert out["_schema_version"] == SCHEMA_VERSIONS["living_model"]
    assert out["foo"] == 1


def test_profile_migration_drops_pronouns():
    raw = {"preferred_name": "A", "pronouns": "they/them", "roles": "friend"}
    out = ensure_schema(raw, kind="profile")
    assert "pronouns" not in out
    assert out["_schema_version"] == 2
    assert out["roles"] == ["friend"]


def test_moments_migration_normalizes_lists():
    raw = {"moments": None, "links": "bad"}
    out = ensure_schema(raw, kind="moments")
    assert out["moments"] == []
    assert out["links"] == []
    assert out["_schema_version"] == 2


def test_compound_migration_adds_meter():
    raw = {
        "missions": [{"id": "m1", "statement": "heal", "status": "active"}],
        "records": [],
    }
    out = ensure_schema(raw, kind="compound")
    assert out["missions"][0]["meter"]["estimated_horizon"] == "unknown"
    assert out["_schema_version"] == 2


def test_does_not_confuse_payload_version_with_schema():
    """moments.version is graph format; schema uses _schema_version only."""
    raw = {"version": 1, "moments": [], "links": []}
    out = ensure_schema(raw, kind="moments")
    assert out["version"] == 1
    assert out["_schema_version"] == 2
