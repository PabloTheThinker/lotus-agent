"""Connection Continuity — Hermes-native session bridge + memory sync."""

from .engine import ContinuityEngine, get_continuity, reset_continuity

__all__ = ["ContinuityEngine", "get_continuity", "reset_continuity"]
