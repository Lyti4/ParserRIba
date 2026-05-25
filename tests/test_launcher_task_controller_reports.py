from __future__ import annotations

from datetime import datetime
from pathlib import Path

import utils.launcher_task_controller as launcher_task_controller
from models.task_actor import RunManifest
from utils.local_task_adapter import LocalTaskProcessResult


def _fake_result(task_name: str, *, shop: str, intent: str, summary: dict[str, object] | None = None) -> LocalTaskProcessResult:
    return LocalTaskProcessResult(
        manifest=RunManifest(
            task_name=task_name,
            shop=shop,
            intent=intent,
            status="ok",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            summary=summary or {"products_count": 1},
        ),
        summary_text=f"Task: {task_name}",
    )


def test_run_launcher_report_export_uses_named_task_and_payload(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return _fake_result("store_report_export", shop="pyaterochka", intent="wine_catalog")

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    result = launcher_task_controller.run_launcher_report_export(
        root_dir=tmp_path,
        shop="pyaterochka",
        intent="wine_catalog",
        categories=["Безалкогольное вино"],
        filters={"suppliers": ["Free Feather"]},
        output_name="wine_free_feather",
        timeout_seconds=123,
    )

    assert result.manifest.task_name == "store_report_export"
    assert captured["task_name"] == "store_report_export"
    assert captured["timeout_seconds"] == 123
    task_input = captured["task_input"]
    assert task_input["selection"] == {
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "categories": ["Безалкогольное вино"],
        "selected_product_ids": [],
    }
    assert task_input["filters"] == {"suppliers": ["Free Feather"]}
    assert task_input["output_name"] == "wine_free_feather"


def test_run_launcher_report_filter_options_uses_named_task_and_payload(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return _fake_result("store_report_filter_options", shop="pyaterochka", intent="wine_catalog")

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    result = launcher_task_controller.run_launcher_report_filter_options(
        root_dir=tmp_path,
        shop="pyaterochka",
        intent="wine_catalog",
        categories=["Безалкогольное вино"],
        timeout_seconds=124,
    )

    assert result.manifest.task_name == "store_report_filter_options"
    assert captured["task_name"] == "store_report_filter_options"
    assert captured["timeout_seconds"] == 124
    assert captured["task_input"]["selection"] == {
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "categories": ["Безалкогольное вино"],
    }


def test_run_launcher_fish_report_export_resolves_categories_from_backend(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return _fake_result("store_report_export", shop="pyaterochka", intent="fish_catalog")

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    launcher_task_controller.run_launcher_fish_report_export(
        root_dir=tmp_path,
        filters={"suppliers": ["Русское море"]},
    )

    task_input = captured["task_input"]
    assert task_input["selection"]["shop"] == "pyaterochka"
    assert task_input["selection"]["intent"] == "fish_catalog"
    assert len(task_input["selection"]["categories"]) == 4
    assert task_input["selection"]["selected_product_ids"] == []
    assert task_input["filters"] == {"suppliers": ["Русское море"]}
    assert task_input["output_name"] == "pyaterochka_fish_report"


def test_run_launcher_wine_report_export_keeps_explicit_categories(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return _fake_result("store_report_export", shop="pyaterochka", intent="wine_catalog")

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    launcher_task_controller.run_launcher_wine_report_export(
        root_dir=tmp_path,
        categories=["Безалкогольное вино"],
        filters={"suppliers": ["Free Feather"]},
        output_name="wine_free_feather",
    )

    task_input = captured["task_input"]
    assert task_input["selection"] == {
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "categories": ["Безалкогольное вино"],
        "selected_product_ids": [],
    }
    assert task_input["filters"] == {"suppliers": ["Free Feather"]}
    assert task_input["output_name"] == "wine_free_feather"


def test_run_launcher_wine_report_filter_options_resolves_categories(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return _fake_result("store_report_filter_options", shop="pyaterochka", intent="wine_catalog")

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    launcher_task_controller.run_launcher_wine_report_filter_options(root_dir=tmp_path)

    task_input = captured["task_input"]
    assert task_input["selection"]["shop"] == "pyaterochka"
    assert task_input["selection"]["intent"] == "wine_catalog"
    assert len(task_input["selection"]["categories"]) == 1
    assert task_input["filters"] == {}
    assert task_input["output_name"] == ""


def test_run_launcher_report_export_exposes_first_class_report_summary(tmp_path: Path) -> None:
    report_summary = {
        "products_count": 1,
        "categories": ["Безалкогольное вино"],
        "category_counts": {"Безалкогольное вино": 1},
        "supplier_counts": {"Free Feather": 1},
        "brand_counts": {"Free Feather": 1},
        "wine_breakdown": {
            "style_counts": {"Тихое": 1},
            "alcohol_type_counts": {"Безалкогольное": 1},
            "sugar_class_counts": {"Полусладкое": 1},
            "color_counts": {"Белое": 1},
        },
    }

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        del kwargs
        return LocalTaskProcessResult(
            manifest=RunManifest(
                task_name="store_report_export",
                shop="pyaterochka",
                intent="wine_catalog",
                status="ok",
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                summary={"products_count": 1, "report_summary": report_summary},
            ),
            report_summary=report_summary,
            launcher_view={"task_name": "store_report_export", "report_summary": report_summary},
        )

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    result = launcher_task_controller.run_launcher_report_export(
        root_dir=tmp_path,
        shop="pyaterochka",
        intent="wine_catalog",
    )

    assert result.report_summary is not None
    assert result.report_summary["supplier_counts"] == {"Free Feather": 1}
    assert result.launcher_view is not None
    assert result.launcher_view["task_name"] == "store_report_export"


def test_run_launcher_report_export_passes_selected_product_ids(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return _fake_result("store_report_export", shop="pyaterochka", intent="fish_catalog")

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    launcher_task_controller.run_launcher_report_export(
        root_dir=tmp_path,
        shop="pyaterochka",
        intent="fish_catalog",
        categories=["Рыба"],
        selected_product_ids=["fish-2", "fish-3"],
    )

    assert captured["task_input"]["selection"]["selected_product_ids"] == ["fish-2", "fish-3"]
