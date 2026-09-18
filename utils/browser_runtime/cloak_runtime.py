"""Optional CloakBrowser browser runtime backend."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from models.browser_runtime import (
    BrowserRuntimeAvailability,
    BrowserRuntimeDescriptor,
    BrowserRuntimeLaunchRequest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLOAKBROWSER_CACHE_DIR = PROJECT_ROOT / "profiles" / "browser_binaries" / "cloakbrowser"


class CloakBrowserRuntime:
    """Experimental local Chromium runtime backed by CloakBrowser."""

    descriptor = BrowserRuntimeDescriptor(
        kind="cloak",
        display_name="CloakBrowser",
        is_recommended=False,
        is_experimental=True,
    )

    def availability(self) -> BrowserRuntimeAvailability:
        try:
            from cloakbrowser import binary_info
        except ModuleNotFoundError:
            return BrowserRuntimeAvailability(
                kind="cloak",
                status="missing_package",
                message_ru=(
                    "CloakBrowser недоступен: пакет не установлен. "
                    "Установите его отдельно, если принимаете лицензию binary."
                ),
            )

        binary_path = _configured_binary_path()
        if binary_path is not None:
            if binary_path.exists():
                return BrowserRuntimeAvailability(
                    kind="cloak",
                    status="available",
                    message_ru="CloakBrowser доступен через CLOAKBROWSER_BINARY_PATH.",
                    diagnostics={"binary_path": str(binary_path)},
                )
            return BrowserRuntimeAvailability(
                kind="cloak",
                status="missing_binary",
                message_ru="CloakBrowser недоступен: CLOAKBROWSER_BINARY_PATH указывает на несуществующий файл.",
                diagnostics={"binary_path": str(binary_path)},
            )

        try:
            with _cloak_cache_environment():
                info = binary_info()
        except Exception as exc:  # pragma: no cover - defensive around optional package internals
            return BrowserRuntimeAvailability(
                kind="cloak",
                status="missing_binary",
                message_ru=f"CloakBrowser недоступен: не удалось проверить binary ({exc}).",
            )

        installed = bool(info.get("installed"))
        binary = str(info.get("binary_path") or "")
        if installed and binary and Path(binary).exists():
            return BrowserRuntimeAvailability(
                kind="cloak",
                status="available",
                message_ru="CloakBrowser доступен как экспериментальный локальный браузер.",
                diagnostics={
                    "binary_path": binary,
                    "version": str(info.get("version") or ""),
                    "platform": str(info.get("platform") or ""),
                },
            )

        return BrowserRuntimeAvailability(
            kind="cloak",
            status="missing_binary",
            message_ru=(
                "CloakBrowser установлен, но binary ещё не установлен. "
                "ParserRIba не скачивает его скрыто: запустите явную установку CloakBrowser отдельно."
            ),
            diagnostics={
                "binary_path": binary,
                "download_url": str(info.get("download_url") or ""),
            },
        )

    def launch_research(self, request: BrowserRuntimeLaunchRequest) -> object:
        return CloakBrowserContext(request, self.availability())


class CloakBrowserContext:
    """Async context manager yielding a CloakBrowser Playwright-compatible object."""

    def __init__(
        self,
        request: BrowserRuntimeLaunchRequest,
        availability: BrowserRuntimeAvailability,
    ) -> None:
        self.request = request
        self.availability = availability
        self._browser_or_context: Any | None = None
        self._env: Iterator[None] | None = None

    async def __aenter__(self) -> Any:
        if not self.availability.is_available:
            raise RuntimeError(self.availability.message_ru)

        self._env = _cloak_launch_environment(self.availability)
        self._env.__enter__()
        try:
            if self.request.user_data_dir:
                from cloakbrowser import launch_persistent_context_async

                user_data_dir = Path(self.request.user_data_dir)
                user_data_dir.mkdir(parents=True, exist_ok=True)
                self._browser_or_context = await launch_persistent_context_async(
                    str(user_data_dir),
                    **_build_launch_options(self.request),
                )
            else:
                from cloakbrowser import launch_async

                self._browser_or_context = await launch_async(**_build_launch_options(self.request))
            return self._browser_or_context
        except BaseException as error:
            environment = self._env
            self._env = None
            if environment is not None:
                environment.__exit__(type(error), error, error.__traceback__)
            raise

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            if self._browser_or_context is not None:
                await self._browser_or_context.close()
        finally:
            if self._env is not None:
                self._env.__exit__(exc_type, exc, traceback)


def _build_launch_options(request: BrowserRuntimeLaunchRequest) -> dict[str, Any]:
    options: dict[str, Any] = {
        "headless": _normalize_headless(request.headless),
        "humanize": True,
    }
    if request.proxy_url:
        options["proxy"] = request.proxy_url
        options["geoip"] = bool(request.geoip)
    return options


def _normalize_headless(headless: bool | str) -> bool:
    if headless in (False, "false", "False", "0"):
        return False
    return True


def _configured_binary_path() -> Path | None:
    value = os.environ.get("CLOAKBROWSER_BINARY_PATH")
    if not value:
        return None
    return Path(value)


@contextmanager
def _cloak_launch_environment(availability: BrowserRuntimeAvailability) -> Iterator[None]:
    previous_auto_update = os.environ.get("CLOAKBROWSER_AUTO_UPDATE")
    previous_binary_path = os.environ.get("CLOAKBROWSER_BINARY_PATH")
    previous_cache_dir = os.environ.get("CLOAKBROWSER_CACHE_DIR")
    binary_path = availability.diagnostics.get("binary_path")
    try:
        os.environ["CLOAKBROWSER_AUTO_UPDATE"] = "false"
        os.environ.setdefault("CLOAKBROWSER_CACHE_DIR", str(DEFAULT_CLOAKBROWSER_CACHE_DIR))
        if binary_path:
            os.environ["CLOAKBROWSER_BINARY_PATH"] = str(binary_path)
        yield
    finally:
        _restore_env("CLOAKBROWSER_AUTO_UPDATE", previous_auto_update)
        _restore_env("CLOAKBROWSER_BINARY_PATH", previous_binary_path)
        _restore_env("CLOAKBROWSER_CACHE_DIR", previous_cache_dir)


@contextmanager
def _cloak_cache_environment() -> Iterator[None]:
    previous_auto_update = os.environ.get("CLOAKBROWSER_AUTO_UPDATE")
    previous_cache_dir = os.environ.get("CLOAKBROWSER_CACHE_DIR")
    try:
        os.environ["CLOAKBROWSER_AUTO_UPDATE"] = "false"
        os.environ.setdefault("CLOAKBROWSER_CACHE_DIR", str(DEFAULT_CLOAKBROWSER_CACHE_DIR))
        yield
    finally:
        _restore_env("CLOAKBROWSER_AUTO_UPDATE", previous_auto_update)
        _restore_env("CLOAKBROWSER_CACHE_DIR", previous_cache_dir)


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
