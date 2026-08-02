"""L.O.T.U.S. specialized Hermes harness."""

from .agent import LotusAgent
from .continuity import ContinuityEngine, get_continuity
from .protocols import Protocol, classify_protocol
from .realtime import LivingUserModel, RealtimeCore, get_core

__all__ = [
    "LotusAgent",
    "Protocol",
    "classify_protocol",
    "RealtimeCore",
    "LivingUserModel",
    "get_core",
    "ContinuityEngine",
    "get_continuity",
]
__version__ = "0.24.0"
