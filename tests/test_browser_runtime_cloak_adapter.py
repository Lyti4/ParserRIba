import os
import sys
import asyncio
import builtins
from types import ModuleType

import pytest

from models.browser_runtime import BrowserRuntimeAvailability, BrowserRuntimeLaunchRequest
from utils.browser_runtime import cloak_runtime
from utils.browser_runtime.cloak_runtime import (
    DEFAULT_CLOAKBROWSER_CACHE_DIR,
    CloakBrowserContext,
    CloakBrowserRuntime,
)


def _available_cloak_context(*, user_data_dir=None) -> CloakBrowserContext:
    request = BrowserRuntimeLaunchRequest(kind="cloak", user_data_dir=user_data_dir)
    availability = BrowserRuntimeAvailability(
        kind="cloak",
        status="available",
        message_ru="available",
        diagnostics={"binary_path": "/selected/cloakbrowser"},
    )
    return CloakBrowserContext(request, availability)


def _set_original_cloak_environment(monkeypatch) -> dict[str, str]:
    original = {
        "CLOAKBROWSER_AUTO_UPDATE": "original-auto-update",
        "CLOAKBROWSER_BINARY_PATH": "original-binary",
        "CLOAKBROWSER_CACHE_DIR": "original-cache",
    }
    for key, value in original.items():
        monkeypatch.setenv(key, value)
    return original


def _assert_cloak_environment_restored(original: dict[str, str]) -> None:
    assert {key: os.environ.get(key) for key in original} == original


def test_cloak_runtime_reports_missing_package(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "cloakbrowser", raising=False)
    original_import = builtins.__import__

    def _raise_for_cloakbrowser(name, *args, **kwargs):
        if name == "cloakbrowser":
            raise ModuleNotFoundError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _raise_for_cloakbrowser)

    runtime = CloakBrowserRuntime()
    availability = runtime.availability()

    assert availability.kind == "cloak"
    assert availability.status == "missing_package"
    assert "CloakBrowser" in availability.message_ru


def test_cloak_runtime_reports_missing_binary(monkeypatch, tmp_path) -> None:
    module = ModuleType("cloakbrowser")
    module.binary_info = lambda: {  # type: ignore[attr-defined]
        "installed": False,
        "binary_path": str(tmp_path / "chrome.exe"),
        "download_url": "https://example.invalid/chrome.zip",
    }
    monkeypatch.setitem(sys.modules, "cloakbrowser", module)
    monkeypatch.delenv("CLOAKBROWSER_BINARY_PATH", raising=False)

    availability = CloakBrowserRuntime().availability()

    assert availability.status == "missing_binary"
    assert availability.diagnostics["binary_path"].endswith("chrome.exe")


def test_cloak_runtime_reports_available_binary(monkeypatch, tmp_path) -> None:
    binary_path = tmp_path / "chrome.exe"
    binary_path.write_text("fake binary", encoding="utf-8")
    module = ModuleType("cloakbrowser")
    module.binary_info = lambda: {  # type: ignore[attr-defined]
        "installed": True,
        "binary_path": str(binary_path),
        "version": "146.0.7680.177.5",
        "platform": "windows-x64",
    }
    monkeypatch.setitem(sys.modules, "cloakbrowser", module)
    monkeypatch.delenv("CLOAKBROWSER_BINARY_PATH", raising=False)

    availability = CloakBrowserRuntime().availability()

    assert availability.status == "available"
    assert availability.diagnostics["binary_path"] == str(binary_path)


def test_cloak_runtime_returns_context(monkeypatch, tmp_path) -> None:
    binary_path = tmp_path / "chrome.exe"
    binary_path.write_text("fake binary", encoding="utf-8")
    monkeypatch.setenv("CLOAKBROWSER_BINARY_PATH", str(binary_path))

    context = CloakBrowserRuntime().launch_research(
        BrowserRuntimeLaunchRequest(kind="cloak", headless=False, proxy_url="http://user:pass@example:8080")
    )

    assert isinstance(context, CloakBrowserContext)


def test_cloak_launch_environment_blocks_auto_update(monkeypatch, tmp_path) -> None:
    binary_path = tmp_path / "chrome.exe"
    binary_path.write_text("fake binary", encoding="utf-8")
    module = ModuleType("cloakbrowser")
    module.binary_info = lambda: {"installed": True, "binary_path": str(binary_path)}  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "cloakbrowser", module)
    monkeypatch.delenv("CLOAKBROWSER_AUTO_UPDATE", raising=False)
    monkeypatch.setenv("CLOAKBROWSER_BINARY_PATH", str(binary_path))

    context = CloakBrowserRuntime().launch_research(
        BrowserRuntimeLaunchRequest(kind="cloak", headless=True, user_data_dir=tmp_path / "profile")
    )
    availability = context.availability
    from utils.browser_runtime.cloak_runtime import _cloak_launch_environment

    monkeypatch.delenv("CLOAKBROWSER_BINARY_PATH", raising=False)
    with _cloak_launch_environment(availability):
        env = os.environ["CLOAKBROWSER_AUTO_UPDATE"]
        path = os.environ["CLOAKBROWSER_BINARY_PATH"]

    assert env == "false"
    assert path == str(binary_path)
    assert "CLOAKBROWSER_AUTO_UPDATE" not in os.environ
    assert "CLOAKBROWSER_BINARY_PATH" not in os.environ


def test_cloak_availability_uses_project_cache_by_default(monkeypatch, tmp_path) -> None:
    expected_binary = DEFAULT_CLOAKBROWSER_CACHE_DIR / "chromium-test" / "chrome.exe"
    module = ModuleType("cloakbrowser")

    def _binary_info():
        assert os.environ["CLOAKBROWSER_CACHE_DIR"] == str(DEFAULT_CLOAKBROWSER_CACHE_DIR)
        assert os.environ["CLOAKBROWSER_AUTO_UPDATE"] == "false"
        return {"installed": False, "binary_path": str(expected_binary)}

    module.binary_info = _binary_info  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "cloakbrowser", module)
    monkeypatch.delenv("CLOAKBROWSER_CACHE_DIR", raising=False)
    monkeypatch.delenv("CLOAKBROWSER_AUTO_UPDATE", raising=False)
    monkeypatch.delenv("CLOAKBROWSER_BINARY_PATH", raising=False)

    availability = CloakBrowserRuntime().availability()

    assert availability.status == "missing_binary"
    assert availability.diagnostics["binary_path"] == str(expected_binary)
    assert "CLOAKBROWSER_CACHE_DIR" not in os.environ
    assert "CLOAKBROWSER_AUTO_UPDATE" not in os.environ


@pytest.mark.asyncio
async def test_cloak_failed_sdk_import_restores_environment_while_exception_is_referenced(monkeypatch) -> None:
    original = _set_original_cloak_environment(monkeypatch)
    context = _available_cloak_context()
    real_import = builtins.__import__

    def fail_cloak_import(name, *args, **kwargs):
        if name == "cloakbrowser":
            raise ModuleNotFoundError("fake cloak SDK import failure")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_cloak_import)

    with pytest.raises(ModuleNotFoundError) as caught:
        await context.__aenter__()

    error = caught.value
    assert "fake cloak SDK import failure" in str(error)
    assert context._env is None
    _assert_cloak_environment_restored(original)
    assert error is caught.value


@pytest.mark.asyncio
async def test_cloak_launch_failure_restores_environment_while_exception_is_referenced(monkeypatch) -> None:
    original = _set_original_cloak_environment(monkeypatch)
    fake_sdk = ModuleType("cloakbrowser")

    async def fail_launch(**_kwargs):
        raise RuntimeError("fake cloak launch failure")

    fake_sdk.launch_async = fail_launch
    monkeypatch.setitem(sys.modules, "cloakbrowser", fake_sdk)
    context = _available_cloak_context()

    with pytest.raises(RuntimeError) as caught:
        await context.__aenter__()

    error = caught.value
    assert "fake cloak launch failure" in str(error)
    assert context._env is None
    _assert_cloak_environment_restored(original)
    assert error is caught.value


@pytest.mark.asyncio
async def test_cloak_launch_cancellation_restores_environment_immediately(monkeypatch) -> None:
    original = _set_original_cloak_environment(monkeypatch)
    fake_sdk = ModuleType("cloakbrowser")

    async def cancel_launch(**_kwargs):
        raise asyncio.CancelledError()

    fake_sdk.launch_async = cancel_launch
    monkeypatch.setitem(sys.modules, "cloakbrowser", fake_sdk)
    context = _available_cloak_context()

    with pytest.raises(asyncio.CancelledError) as caught:
        await context.__aenter__()

    cancellation = caught.value
    assert context._env is None
    _assert_cloak_environment_restored(original)
    assert cancellation is caught.value


@pytest.mark.asyncio
async def test_cloak_profile_preparation_failure_restores_environment_immediately(monkeypatch, tmp_path) -> None:
    original = _set_original_cloak_environment(monkeypatch)
    fake_sdk = ModuleType("cloakbrowser")

    async def launch_persistent_context_async(*_args, **_kwargs):
        raise AssertionError("profile preparation should fail before SDK launch")

    fake_sdk.launch_persistent_context_async = launch_persistent_context_async
    monkeypatch.setitem(sys.modules, "cloakbrowser", fake_sdk)

    def fail_mkdir(self, *_args, **_kwargs):
        raise OSError("fake profile preparation failure")

    monkeypatch.setattr(cloak_runtime.Path, "mkdir", fail_mkdir)
    context = _available_cloak_context(user_data_dir=tmp_path / "profile")

    with pytest.raises(OSError) as caught:
        await context.__aenter__()

    error = caught.value
    assert "fake profile preparation failure" in str(error)
    assert context._env is None
    _assert_cloak_environment_restored(original)
    assert error is caught.value
