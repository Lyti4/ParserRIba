"""Local Playwright Chromium browser runtime backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from models.browser_runtime import (
    BrowserRuntimeAvailability,
    BrowserRuntimeDescriptor,
    BrowserRuntimeLaunchRequest,
)
from utils.proxy import parse_proxy_url


class ChromiumBrowserRuntime:
    """Experimental local Chromium runtime backed by Playwright."""

    descriptor = BrowserRuntimeDescriptor(
        kind="chromium",
        display_name="Chromium",
        is_recommended=False,
        is_experimental=True,
    )

    def availability(self) -> BrowserRuntimeAvailability:
        try:
            import playwright.async_api  # noqa: F401
        except ModuleNotFoundError:
            return BrowserRuntimeAvailability(
                kind="chromium",
                status="missing_package",
                message_ru="Chromium недоступен: пакет Playwright не установлен.",
            )
        return BrowserRuntimeAvailability(
            kind="chromium",
            status="available",
            message_ru="Chromium доступен как экспериментальный локальный браузер.",
        )

    def launch_research(self, request: BrowserRuntimeLaunchRequest) -> object:
        return PlaywrightChromiumContext(request)


class PlaywrightChromiumContext:
    """Async context manager yielding a Playwright-compatible browser context."""

    def __init__(self, request: BrowserRuntimeLaunchRequest) -> None:
        self.request = request
        self._playwright: Any | None = None
        self._browser_or_context: Any | None = None

    async def __aenter__(self) -> Any:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        launch_options = _build_launch_options(self.request)
        user_data_dir = self.request.user_data_dir
        if user_data_dir:
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
            self._browser_or_context = await self._playwright.chromium.launch_persistent_context(
                str(user_data_dir),
                **launch_options,
            )
        else:
            self._browser_or_context = await self._playwright.chromium.launch(**launch_options)
        return self._browser_or_context

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._browser_or_context is not None:
            await self._browser_or_context.close()
        if self._playwright is not None:
            await self._playwright.stop()


def _build_launch_options(request: BrowserRuntimeLaunchRequest) -> dict[str, Any]:
    options: dict[str, Any] = {
        "headless": _normalize_headless(request.headless),
    }
    if request.proxy_url:
        options["proxy"] = parse_proxy_url(request.proxy_url).as_playwright()
    return options


def _normalize_headless(headless: bool | str) -> bool:
    if headless in (False, "false", "False", "0"):
        return False
    return True
