"""
Policies module for automatic error handling and recovery strategies.
Inspired by browser-act policy-driven automation patterns.
"""

from .engine import (
    ErrorType,
    ActionType,
    PolicyRule,
    PolicyResult,
    PoliciesEngine,
    classify_error,
)

__all__ = [
    "ErrorType",
    "ActionType",
    "PolicyRule",
    "PolicyResult",
    "PoliciesEngine",
    "classify_error",
]
