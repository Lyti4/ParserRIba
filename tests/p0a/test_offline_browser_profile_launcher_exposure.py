from __future__ import annotations

from typing import cast

import pytest

from application.pyaterochka_browser_profile import (
    PYATEROCHKA_LIVE_SOURCE_PROFILE_ID,
    build_offline_pyaterochka_browser_registration,
)
from application.contracts import ApplicationContractError
import launcher.desktop_launcher as desktop_launcher
from launcher.desktop_controller import DesktopLauncherController
from launcher.desktop_launcher import DesktopLauncherShell


def test_pyaterochka_live_profile_is_visible_only_when_explicitly_injected(tmp_path) -> None:
    default_shell = DesktopLauncherShell(root_dir=tmp_path / "default")
    default_profile_ids = {
        profile.source_profile_id for profile in default_shell.source_profiles
    }

    registration = build_offline_pyaterochka_browser_registration()
    exposed_shell = DesktopLauncherShell(
        root_dir=tmp_path / "exposed",
        browser_registration=registration,
    )
    exposed_profiles = {
        profile.source_profile_id: profile for profile in exposed_shell.source_profiles
    }

    assert PYATEROCHKA_LIVE_SOURCE_PROFILE_ID not in default_profile_ids
    assert exposed_profiles[PYATEROCHKA_LIVE_SOURCE_PROFILE_ID].display_name == (
        "Пятёрочка — live (требуется активация)"
    )
    assert exposed_shell.controller.browser_registration is registration
    assert exposed_shell.controller.browser_collection_enabled is False


def test_explicit_pyaterochka_profile_inspects_static_catalog_without_browser_run(tmp_path) -> None:
    registration = build_offline_pyaterochka_browser_registration()
    controller = DesktopLauncherController(
        root_dir=tmp_path,
        browser_registration=registration,
    )

    nodes = controller.inspect_source_adapter_catalog(
        PYATEROCHKA_LIVE_SOURCE_PROFILE_ID
    )

    assert [node["display_name"] for node in nodes] == [
        "Рыба",
        "Морепродукты",
        "Котлеты и фарш",
        "Икра и закуски",
        "Пиво, вино, энергетики",
        "Безалкогольное вино",
    ]
    assert controller.state.catalog.source_locator == "https://5ka.ru"


def test_inactive_browser_profile_rejects_collection_before_runner_dispatch(tmp_path) -> None:
    runner_calls: list[dict[str, object]] = []

    def recording_runner(**kwargs: object):
        runner_calls.append(dict(kwargs))
        raise AssertionError("inactive browser profile must not dispatch the runner")

    controller = DesktopLauncherController(
        root_dir=tmp_path,
        browser_registration=build_offline_pyaterochka_browser_registration(),
        source_adapter_collection_runner=recording_runner,
    )
    expected_nodes = controller.inspect_source_adapter_catalog(
        PYATEROCHKA_LIVE_SOURCE_PROFILE_ID
    )
    controller.set_source_adapter_catalog_selection(["pyaterochka-fish"])

    with pytest.raises(ApplicationContractError) as caught:
        controller.run_source_adapter_collection(
            collection_run_id="pyaterochka-offline-exposure-001",
            source_profile_id=PYATEROCHKA_LIVE_SOURCE_PROFILE_ID,
            catalog_node_ids=["pyaterochka-fish"],
        )

    assert caught.value.code == "BROWSER_SOURCE_ACTIVATION_REQUIRED"
    assert controller.state.catalog.source_locator == "https://5ka.ru"
    assert controller.state.catalog.source_nodes == expected_nodes
    assert controller.state.catalog.selected_source_node_ids == ["pyaterochka-fish"]
    assert runner_calls == []


def test_browser_ui_collection_keeps_fixed_locator_display_only(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Combo:
        @staticmethod
        def currentData() -> str:
            return PYATEROCHKA_LIVE_SOURCE_PROFILE_ID

    class _LineEdit:
        @staticmethod
        def text() -> str:
            return "https://5ka.ru"

    class _Controller:
        @staticmethod
        def source_adapter_collection_worker_action(**kwargs: object):
            captured.update(kwargs)
            return lambda: {"status": "failed"}

        @staticmethod
        def begin_source_adapter_collection() -> None:
            return None

    class _Shell:
        _active_task_thread = None
        source_profile_combo = _Combo()
        source_locator_input = _LineEdit()
        controller = _Controller()

        @staticmethod
        def _current_combo_value(combo: _Combo) -> str:
            return combo.currentData()

        @staticmethod
        def _next_source_collection_run_id() -> str:
            return "browser-ui-display-only-001"

        @staticmethod
        def _refresh_ui() -> None:
            return None

        @staticmethod
        def _start_background_action(*_args: object, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(
        desktop_launcher,
        "selected_source_adapter_catalog_node_ids",
        lambda _shell: ["pyaterochka-fish"],
    )

    DesktopLauncherShell._on_run_source_adapter_collection(
        cast(DesktopLauncherShell, _Shell())
    )

    assert captured["source_profile_id"] == PYATEROCHKA_LIVE_SOURCE_PROFILE_ID
    assert captured["source_locator"] is None


def test_launcher_collection_policy_keeps_only_inactive_browser_profile_disabled(tmp_path) -> None:
    controller = DesktopLauncherController(
        root_dir=tmp_path,
        browser_registration=build_offline_pyaterochka_browser_registration(),
    )

    assert (
        controller.source_profile_collection_enabled(
            PYATEROCHKA_LIVE_SOURCE_PROFILE_ID
        )
        is False
    )
    assert controller.source_profile_collection_enabled("synthetic-example-catalog") is True
    assert controller.source_profile_collection_enabled("local-json-file") is True
