from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from models.browser_runtime import BrowserRuntimeAvailability
from scripts import cloak_runtime_probe


class _FakePage:
    def __init__(self, marker: str) -> None:
        self.marker = marker

    async def set_content(self, html: str) -> None:
        assert "cloak-dom-ok" in html

    async def evaluate(self, expression: str) -> str:
        assert "#probe" in expression
        return self.marker


class _FakeBrowser:
    def __init__(self, marker: str) -> None:
        self.page = _FakePage(marker)

    async def new_page(self) -> _FakePage:
        return self.page


def _available() -> BrowserRuntimeAvailability:
    return BrowserRuntimeAvailability(kind="cloak", status="available", message_ru="ok", diagnostics={"version": "0.5.10", "platform": "windows-x64"})


@pytest.mark.asyncio
async def test_cloak_probe_writes_allowlisted_success_receipt(monkeypatch, tmp_path: Path) -> None:
    closed = False

    @asynccontextmanager
    async def fake_launch(_request):
        nonlocal closed
        try:
            yield _FakeBrowser("cloak-dom-ok")
        finally:
            closed = True

    monkeypatch.setenv("PARSERRIBA_CLOAK_PROBE_PROFILE", str(tmp_path / "profile"))
    monkeypatch.setattr(cloak_runtime_probe, "check_browser_runtime", lambda kind: _available())
    monkeypatch.setattr(cloak_runtime_probe, "launch_research_browser", fake_launch)
    result_path = tmp_path / "probe.json"

    assert await cloak_runtime_probe._run_cloak_probe(result_path) == 0
    receipt = json.loads(result_path.read_text(encoding="utf-8"))
    assert receipt["runtime"] == "cloak"
    assert receipt["started"] is True and receipt["closed"] is True
    assert receipt["dom_marker"] == "cloak-dom-ok"
    assert set(receipt) == {"runtime", "frozen", "started", "dom_marker", "availability_status", "sdk_version", "runtime_identity", "closed"}
    assert closed is True


@pytest.mark.asyncio
async def test_cloak_probe_fails_closed_without_available_sdk(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PARSERRIBA_CLOAK_PROBE_PROFILE", str(tmp_path / "profile"))
    missing = BrowserRuntimeAvailability(kind="cloak", status="missing_binary", message_ru="missing")
    monkeypatch.setattr(cloak_runtime_probe, "check_browser_runtime", lambda kind: missing)

    with pytest.raises(RuntimeError, match="missing"):
        await cloak_runtime_probe._run_cloak_probe(tmp_path / "probe.json")
    assert not (tmp_path / "probe.json").exists()


@pytest.mark.asyncio
async def test_cloak_probe_fails_without_receipt_on_dom_mismatch(monkeypatch, tmp_path: Path) -> None:
    @asynccontextmanager
    async def fake_launch(_request):
        yield _FakeBrowser("wrong-marker")

    monkeypatch.setenv("PARSERRIBA_CLOAK_PROBE_PROFILE", str(tmp_path / "profile"))
    monkeypatch.setattr(cloak_runtime_probe, "check_browser_runtime", lambda kind: _available())
    monkeypatch.setattr(cloak_runtime_probe, "launch_research_browser", fake_launch)
    result_path = tmp_path / "probe.json"

    with pytest.raises(RuntimeError, match="DOM marker mismatch"):
        await cloak_runtime_probe._run_cloak_probe(result_path)
    assert not result_path.exists()
