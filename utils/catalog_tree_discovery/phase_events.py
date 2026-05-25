"""Helpers for launcher-facing discovery phase updates."""

from __future__ import annotations

from models.catalog_discovery import DiscoveryPhaseEvent


def make_phase_event(
    phase: str,
    status: str,
    message_ru: str,
    categories: list[str] | None = None,
) -> DiscoveryPhaseEvent:
    """Build one discovery phase event with optional streamed categories."""
    return DiscoveryPhaseEvent(
        phase=phase,
        status=status,
        message_ru=message_ru,
        discovered_categories=list(categories or []),
    )
