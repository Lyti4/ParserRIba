from __future__ import annotations

from datetime import datetime
from pathlib import Path

import utils.launcher_task_controller as launcher_task_controller
from models.task_actor import RunManifest
from utils.local_task_adapter import LocalTaskProcessResult


def test_run_launcher_wine_export_uses_named_task_and_payload(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return LocalTaskProcessResult(
            manifest=RunManifest(
                task_name="pyaterochka_wine_export",
                shop="pyaterochka",
                intent="wine_catalog",
                status="ok",
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                summary={"products_count": 38},
            ),
            summary_text="Task: pyaterochka_wine_export",
        )

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    result = launcher_task_controller.run_launcher_wine_export(
        root_dir=tmp_path,
        attempts=2,
        listen_seconds=6,
        headless=True,
        manual_wait=False,
    )

    assert result.manifest.task_name == "pyaterochka_wine_export"
    assert result.manifest.intent == "wine_catalog"
    assert captured["task_name"] == "pyaterochka_wine_export"
    task_input = captured["task_input"]
    assert task_input["attempts"] == 2
    assert task_input["listen_seconds"] == 6
    assert task_input["headless"] is True
    assert task_input["manual_wait"] is False
    assert task_input["expand_intent"] is True
    assert task_input["category_url"] == ""
    assert isinstance(task_input["category"], str)
    assert task_input["category"]


def test_run_launcher_fish_export_uses_named_task_and_payload(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return LocalTaskProcessResult(
            manifest=RunManifest(
                task_name="pyaterochka_fish_export",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                summary={"products_count": 84},
            ),
            summary_text="Task: pyaterochka_fish_export",
        )

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    result = launcher_task_controller.run_launcher_fish_export(
        root_dir=tmp_path,
        category="Р В РЎвЂ№Р В±Р В°",
        category_url="https://5ka.ru/catalog/zavtraki--251C12891/",
        attempts=1,
        listen_seconds=4,
        headless=False,
        manual_wait=True,
    )

    assert result.manifest.task_name == "pyaterochka_fish_export"
    assert result.manifest.intent == "fish_catalog"
    assert captured["task_name"] == "pyaterochka_fish_export"
    assert captured["task_input"] == {
        "category": "Р В РЎвЂ№Р В±Р В°",
        "category_url": "https://5ka.ru/catalog/zavtraki--251C12891/",
        "attempts": 1,
        "listen_seconds": 4,
        "headless": False,
        "manual_wait": True,
        "expand_intent": True,
    }
