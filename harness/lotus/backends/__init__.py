"""Optional model backends for LotusAgent (Hermes default, Cursor CLI opt-in)."""

from .cursor_cli import CursorCliBackend, resolve_backend

__all__ = ["CursorCliBackend", "resolve_backend"]
