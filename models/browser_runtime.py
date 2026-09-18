"""Browser runtime contracts for local browser-backed research flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

BrowserRuntimeKind = Literal["camoufox", "chromium", "cloak"]
BrowserRuntimeAvailabilityStatus = Literal[
    "available",
    "missing_package",
    "missing_binary",
    "license_blocked",
    "smoke_failed",
    "disabled_by_policy",
]


class BrowserRuntimeDescriptor(BaseModel):
    """User-facing metadata for a browser runtime backend."""

    kind: BrowserRuntimeKind
    display_name: str
    is_recommended: bool = False
    is_experimental: bool = False


class BrowserRuntimeAvailability(BaseModel):
    """Selection readiness and safe diagnostics for one browser runtime."""

    kind: BrowserRuntimeKind
    status: BrowserRuntimeAvailabilityStatus
    message_ru: str
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.status == "available"


class BrowserRuntimeLaunchRequest(BaseModel):
    """Normalized launch input shared by browser runtime backends."""

    kind: BrowserRuntimeKind = "camoufox"
    headless: bool | str = True
    proxy_url: str | None = None
    geoip: bool = False
    user_data_dir: Path | str | None = None
