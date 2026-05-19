"""Registry of launcher protection strategies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProtectionStrategy:
    """Behavior contract for protected-site onboarding."""

    name: str
    pause_for_operator: bool


def get_protection_strategy(name: str) -> ProtectionStrategy:
    """Return one known protection strategy."""
    normalized = str(name or "").strip().casefold()
    if normalized == "pause_for_operator":
        return ProtectionStrategy(name="pause_for_operator", pause_for_operator=True)
    raise ValueError(f"Unsupported protection strategy: {name}")
