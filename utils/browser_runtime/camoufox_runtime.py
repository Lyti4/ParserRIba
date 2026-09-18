"""Camoufox browser runtime backend."""

from __future__ import annotations

from camoufox.async_api import AsyncCamoufox

from models.browser_runtime import (
    BrowserRuntimeAvailability,
    BrowserRuntimeDescriptor,
    BrowserRuntimeLaunchRequest,
)
from utils.camoufox_launcher import build_research_camoufox_options


class CamoufoxBrowserRuntime:
    """Default stable browser runtime for ParserRIba research flows."""

    descriptor = BrowserRuntimeDescriptor(
        kind="camoufox",
        display_name="Camoufox",
        is_recommended=True,
        is_experimental=False,
    )

    def availability(self) -> BrowserRuntimeAvailability:
        return BrowserRuntimeAvailability(
            kind="camoufox",
            status="available",
            message_ru="Camoufox доступен и используется по умолчанию.",
        )

    def launch_research(self, request: BrowserRuntimeLaunchRequest) -> object:
        options = build_research_camoufox_options(
            headless=request.headless,
            proxy_url=request.proxy_url,
            geoip=request.geoip,
            user_data_dir=request.user_data_dir,
        )
        return AsyncCamoufox(**options)
