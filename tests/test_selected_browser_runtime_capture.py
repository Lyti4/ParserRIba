"""Offline regression coverage for selected browser runtime product capture."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from utils import pyaterochka_catalog_capture as catalog_capture
from utils.store_export_runtime import _run_discover_func


class _CancelledPage:
    def on(self, *_args: Any) -> None:
        pass

    async def set_extra_http_headers(self, _headers: dict[str, str]) -> None:
        pass

    async def goto(self, *_args: Any, **_kwargs: Any) -> None:
        raise asyncio.CancelledError


class _RecordingBrowser:
    async def new_page(self) -> _CancelledPage:
        return _CancelledPage()


class _RecordingRuntime:
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> _RecordingBrowser:
        self.entered = True
        return _RecordingBrowser()

    async def __aexit__(self, *_args: Any) -> None:
        self.exited = True


@pytest.mark.asyncio
async def test_capture_launches_selected_cloak_runtime_and_closes_it_on_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched_requests: list[Any] = []
    runtime = _RecordingRuntime()

    def launch(request: Any) -> _RecordingRuntime:
        launched_requests.append(request)
        return runtime

    monkeypatch.setattr(catalog_capture, "launch_research_browser", launch)

    with pytest.raises(asyncio.CancelledError):
        await catalog_capture.capture_pyaterochka_catalog(
            category_name="Fixture category",
            category_url="https://example.test/catalog",
            browser_runtime="cloak",
        )

    assert launched_requests[0].kind == "cloak"
    assert runtime.entered is True
    assert runtime.exited is True


@pytest.mark.asyncio
async def test_capture_keeps_camoufox_as_the_default_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launched_requests: list[Any] = []

    def launch(request: Any) -> _RecordingRuntime:
        launched_requests.append(request)
        return _RecordingRuntime()

    monkeypatch.setattr(catalog_capture, "launch_research_browser", launch)

    with pytest.raises(asyncio.CancelledError):
        await catalog_capture.capture_pyaterochka_catalog(
            category_name="Fixture category",
            category_url="https://example.test/catalog",
        )

    assert launched_requests[0].kind == "camoufox"


@pytest.mark.asyncio
async def test_export_bridge_forwards_runtime_only_to_supported_discoverers() -> None:
    async def selected_runner(**kwargs: Any) -> dict[str, Any]:
        return kwargs

    async def legacy_runner(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ) -> dict[str, Any]:
        return {
            "category_name": category_name,
            "listen_seconds": listen_seconds,
            "headless": headless,
            "manual_wait": manual_wait,
        }

    selected = await _run_discover_func(
        selected_runner,
        category_name="Fixture category",
        category_url="https://example.test/catalog",
        listen_seconds=1,
        headless=True,
        manual_wait=False,
        browser_runtime="cloak",
    )
    legacy = await _run_discover_func(
        legacy_runner,
        category_name="Fixture category",
        category_url="https://example.test/catalog",
        listen_seconds=1,
        headless=True,
        manual_wait=False,
        browser_runtime="cloak",
    )

    assert selected["browser_runtime"] == "cloak"
    assert "browser_runtime" not in legacy
