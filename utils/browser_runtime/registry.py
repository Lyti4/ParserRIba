"""Registry for local browser runtime backends."""

from __future__ import annotations

from models.browser_runtime import (
    BrowserRuntimeAvailability,
    BrowserRuntimeKind,
    BrowserRuntimeLaunchRequest,
)
from utils.browser_runtime.base import BrowserRuntimeBackend
from utils.browser_runtime.camoufox_runtime import CamoufoxBrowserRuntime
from utils.browser_runtime.chromium_runtime import ChromiumBrowserRuntime
from utils.browser_runtime.cloak_runtime import CloakBrowserRuntime

DEFAULT_BROWSER_RUNTIME: BrowserRuntimeKind = "camoufox"

_RUNTIMES: dict[BrowserRuntimeKind, BrowserRuntimeBackend] = {
    "camoufox": CamoufoxBrowserRuntime(),
    "chromium": ChromiumBrowserRuntime(),
    "cloak": CloakBrowserRuntime(),
}


def get_browser_runtime(kind: BrowserRuntimeKind | str | None = None) -> BrowserRuntimeBackend:
    """Return a registered browser runtime backend."""
    runtime_kind = str(kind or DEFAULT_BROWSER_RUNTIME)
    if runtime_kind not in _RUNTIMES:
        raise ValueError(f"Unsupported browser runtime: {runtime_kind}")
    return _RUNTIMES[runtime_kind]  # type: ignore[index]


def check_browser_runtime(kind: BrowserRuntimeKind | str | None = None) -> BrowserRuntimeAvailability:
    """Return availability for a browser runtime."""
    return get_browser_runtime(kind).availability()


def launch_research_browser(request: BrowserRuntimeLaunchRequest) -> object:
    """Return an async browser context manager for a research request."""
    backend = get_browser_runtime(request.kind)
    availability = backend.availability()
    if not availability.is_available:
        raise RuntimeError(availability.message_ru)
    return backend.launch_research(request)
