"""Shared browser runtime backend interface."""

from __future__ import annotations

from typing import Protocol

from models.browser_runtime import (
    BrowserRuntimeAvailability,
    BrowserRuntimeDescriptor,
    BrowserRuntimeLaunchRequest,
)


class BrowserRuntimeBackend(Protocol):
    """Protocol implemented by local browser runtime backends."""

    descriptor: BrowserRuntimeDescriptor

    def availability(self) -> BrowserRuntimeAvailability:
        """Return whether the backend can be selected."""

    def launch_research(self, request: BrowserRuntimeLaunchRequest) -> object:
        """Return an async context manager yielding a Playwright-compatible browser."""
