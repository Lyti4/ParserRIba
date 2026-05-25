from __future__ import annotations

from datetime import datetime
from pathlib import Path

import utils.launcher_task_controller as launcher_task_controller
from models.task_actor import RunManifest
from utils.local_task_adapter import LocalTaskProcessResult


def test_run_launcher_onboarding_discovery_uses_local_task_adapter(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        captured.update(kwargs)
        return LocalTaskProcessResult(
            manifest=RunManifest(
                task_name="site_onboarding_discovery",
                shop="unknown-store_example",
                intent="fish_catalog",
                status="scaffold_ready",
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                summary={"selected_categories": ["Рыба"]},
            ),
            summary_text="Task: site_onboarding_discovery",
        )

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    result = launcher_task_controller.run_launcher_onboarding_discovery(
        site_url="https://unknown-store.example",
        root_dir=tmp_path,
        selected_categories=["Рыба"],
        research_mode="quiet",
        python_executable="python.exe",
        show_summary=True,
        timeout_seconds=321,
    )

    assert result.manifest.task_name == "site_onboarding_discovery"
    assert result.manifest.summary["selected_categories"] == ["Рыба"]
    assert result.summary_text == "Task: site_onboarding_discovery"
    assert captured["task_name"] == "site_onboarding_discovery"
    assert captured["root_dir"] == tmp_path
    assert captured["python_executable"] == "python.exe"
    assert captured["show_summary"] is True
    assert captured["timeout_seconds"] == 321
    assert captured["task_input"] == {
        "site_url": "https://unknown-store.example",
        "intent": "fish_catalog",
        "require_operator_confirmation": False,
        "selected_categories": ["Рыба"],
        "headless": None,
        "manual_wait": False,
        "listen_seconds": 6,
        "research_mode": "quiet",
    }


def test_run_launcher_onboarding_discovery_exposes_first_class_discovery_fields(tmp_path: Path) -> None:
    def fake_run_local_task_subprocess(**kwargs: object) -> LocalTaskProcessResult:
        del kwargs
        return LocalTaskProcessResult(
            manifest=RunManifest(
                task_name="site_onboarding_discovery",
                shop="metro",
                intent="fish_catalog",
                status="discovery_only",
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                summary={
                    "category_count": 1,
                    "category_tree": [{"name": "Рыба", "url": "https://example.test/fish"}],
                    "selected_categories": ["Рыба"],
                    "active_profile_id": "profile-1",
                    "active_profile_version_id": "version-2",
                    "streamed_categories": ["Рыба"],
                    "current_phase": "build_tree",
                    "diagnostics_summary": {
                        "known_backend": True,
                        "runtime_export_ready": False,
                    },
                    "catalog_discovery": {
                        "surface_type": "category_tree",
                        "reachable": True,
                    },
                    "intent_category_links": [
                        {"name": "Рыба", "url": "https://example.test/fish"}
                    ],
                },
            ),
            category_tree=[{"name": "Рыба", "url": "https://example.test/fish"}],
            selected_categories=["Рыба"],
            diagnostics_summary={
                "known_backend": True,
                "runtime_export_ready": False,
            },
            catalog_discovery={
                "surface_type": "category_tree",
                "reachable": True,
            },
            intent_category_links=[
                {"name": "Рыба", "url": "https://example.test/fish"}
            ],
            launcher_view={
                "task_name": "site_onboarding_discovery",
                "status": "discovery_only",
                "shop": "metro",
                "intent": "fish_catalog",
                "summary_text": "",
                "artifact_paths": {},
                "products_count": 0,
                "categories": [],
                "selected_categories": ["Рыба"],
                "category_tree": [{"name": "Рыба", "url": "https://example.test/fish"}],
                "report_summary": {},
                "export_summary": {},
                "available_filter_counts": {},
                "diagnostics_summary": {
                    "known_backend": True,
                    "runtime_export_ready": False,
                },
                "catalog_discovery": {
                    "surface_type": "category_tree",
                    "reachable": True,
                },
                "intent_category_links": [
                    {"name": "Рыба", "url": "https://example.test/fish"}
                ],
            },
        )

    launcher_task_controller.run_local_task_subprocess = fake_run_local_task_subprocess

    result = launcher_task_controller.run_launcher_onboarding_discovery(
        site_url="https://online.metro-cc.ru/",
        root_dir=tmp_path,
    )

    assert result.category_tree == [{"name": "Рыба", "url": "https://example.test/fish"}]
    assert result.selected_categories == ["Рыба"]
    assert result.diagnostics_summary == {
        "known_backend": True,
        "runtime_export_ready": False,
    }
    assert result.catalog_discovery == {
        "surface_type": "category_tree",
        "reachable": True,
    }
    assert result.intent_category_links == [
        {"name": "Рыба", "url": "https://example.test/fish"}
    ]
    assert result.launcher_view is not None
    assert result.launcher_view["status"] == "discovery_only"
    assert result.launcher_view["category_tree"] == [
        {"name": "Рыба", "url": "https://example.test/fish"}
    ]
    assert result.launcher_view["selected_categories"] == ["Рыба"]
    assert result.manifest.summary["active_profile_id"] == "profile-1"
    assert result.manifest.summary["active_profile_version_id"] == "version-2"
    assert result.manifest.summary["streamed_categories"] == ["Рыба"]
    assert result.manifest.summary["current_phase"] == "build_tree"
