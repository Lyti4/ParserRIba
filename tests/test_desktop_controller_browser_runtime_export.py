from __future__ import annotations

from datetime import datetime
from pathlib import Path

import utils.launcher_task_controller as launcher_task_controller
from launcher.desktop_controller import DesktopLauncherController
from models.task_actor import RunManifest
from utils.local_task_adapter import LocalTaskProcessResult


def _successful_process_result(task_input: dict[str, object]) -> LocalTaskProcessResult:
    return LocalTaskProcessResult(
        manifest=RunManifest(
            task_name="store_catalog_export",
            shop=str(task_input["shop"]),
            intent=str(task_input["intent"]),
            status="ok",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            summary={"products_count": 0},
        ),
        summary_text="Task: store_catalog_export",
    )


def _run_selected_export_and_capture_runtime(
    monkeypatch,
    tmp_path: Path,
    browser_runtime: str | None,
) -> str:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        task_input = dict(kwargs["task_input"])
        captured.update(task_input)
        return _successful_process_result(task_input)

    monkeypatch.setattr(launcher_task_controller, "run_local_task_subprocess", fake_run_local_task_subprocess)
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.set_selection(intent="fish_catalog", categories=["Рыба"])
    if browser_runtime is not None:
        controller.state.settings.browser_runtime = browser_runtime

    controller.run_selected_export()
    return str(captured["browser_runtime"])


def test_default_desktop_export_forwards_selected_cloak_runtime_to_process_boundary(monkeypatch, tmp_path: Path) -> None:
    assert _run_selected_export_and_capture_runtime(monkeypatch, tmp_path, "cloak") == "cloak"


def test_default_desktop_export_keeps_camoufox_legacy_default(monkeypatch, tmp_path: Path) -> None:
    assert _run_selected_export_and_capture_runtime(monkeypatch, tmp_path, None) == "camoufox"
