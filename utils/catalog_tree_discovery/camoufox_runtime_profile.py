"""Camoufox research runtime defaults for discovery flows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CamoufoxResearchRuntimeProfile:
    """Focused browser policy for serial catalog research runs."""

    locale: str = "ru-RU"
    humanize: float = 1.5
    block_images: bool = False
    block_webgl: bool = False
    require_persistent_context: bool = True
    allow_disable_coop: bool = False
