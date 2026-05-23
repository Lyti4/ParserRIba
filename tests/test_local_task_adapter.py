import base64
import json
import subprocess
import sys
from pathlib import Path

from models.task_actor import RunManifest
from utils.local_task_adapter import (
    LocalTaskProcessResult,
    build_local_task_command,
    build_local_task_process_result,
    run_local_task_subprocess,
)


def test_build_local_task_command_uses_base64_transport() -> None:
    command = build_local_task_command(
        task_name="site_onboarding_discovery",
        task_input={
            "site_url": "https://unknown-store.example",
            "intent": "fish_catalog",
            "selected_categories": ["Рыба"],
        },
    )

    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\run_local_task.py") or command[1].endswith("scripts/run_local_task.py")
    assert "--task" in command
    assert "--input-base64" in command
    encoded = command[command.index("--input-base64") + 1]
    decoded = json.loads(base64.b64decode(encoded).decode("utf-8"))
    assert decoded["selected_categories"] == ["Рыба"]


def test_run_local_task_subprocess_returns_manifest(tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    result = run_local_task_subprocess(
        task_name="site_onboarding_discovery",
        task_input={
            "site_url": "https://unknown-store.example",
            "intent": "fish_catalog",
            "selected_categories": ["Рыба"],
        },
        root_dir=tmp_path,
        python_executable=sys.executable,
    )

    assert isinstance(result, LocalTaskProcessResult)
    assert isinstance(result.manifest, RunManifest)
    assert result.manifest.task_name == "site_onboarding_discovery"
    assert result.manifest.status == "scaffold_ready"
    assert result.manifest.summary["selected_categories"] == ["Рыба"]


def test_run_local_task_subprocess_returns_summary_text(tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    result = run_local_task_subprocess(
        task_name="site_onboarding_discovery",
        task_input={
            "site_url": "https://unknown-store.example",
            "intent": "fish_catalog",
            "selected_categories": ["Рыба"],
        },
        root_dir=tmp_path,
        python_executable=sys.executable,
        show_summary=True,
    )

    assert isinstance(result, LocalTaskProcessResult)
    assert isinstance(result.manifest, RunManifest)
    assert result.manifest.status == "scaffold_ready"
    assert "Task: site_onboarding_discovery" in result.summary_text
    assert "Selected categories: Рыба" in result.summary_text


def test_build_local_task_process_result_exposes_first_class_report_summary() -> None:
    result = build_local_task_process_result(
        manifest=RunManifest(
            task_name="store_report_export",
            shop="pyaterochka",
            intent="wine_catalog",
            status="empty",
            summary={
                "report_summary": {
                    "products_count": 0,
                    "categories": [],
                    "category_counts": {},
                    "supplier_counts": {},
                    "brand_counts": {},
                    "wine_breakdown": {
                        "style_counts": {},
                        "alcohol_type_counts": {},
                        "sugar_class_counts": {},
                        "color_counts": {},
                    },
                }
            },
        )
    )

    assert isinstance(result, LocalTaskProcessResult)
    assert result.manifest.task_name == "store_report_export"
    assert result.report_summary == {
        "products_count": 0,
        "categories": [],
        "category_counts": {},
        "supplier_counts": {},
        "brand_counts": {},
        "wine_breakdown": {
            "style_counts": {},
            "alcohol_type_counts": {},
            "sugar_class_counts": {},
            "color_counts": {},
        },
    }
    assert result.launcher_view is not None
    assert result.launcher_view["task_name"] == "store_report_export"
    assert result.launcher_view["report_summary"]["products_count"] == 0
    assert result.launcher_view["categories"] == []


def test_build_local_task_process_result_exposes_first_class_filter_counts() -> None:
    result = build_local_task_process_result(
        manifest=RunManifest(
            task_name="store_report_filter_options",
            shop="pyaterochka",
            intent="wine_catalog",
            status="ok",
            summary={
                "available_filter_counts": {
                    "suppliers": {},
                    "brands": {"Free Feather": 1},
                }
            },
        )
    )

    assert isinstance(result, LocalTaskProcessResult)
    assert result.manifest.task_name == "store_report_filter_options"
    assert result.available_filter_counts is not None
    assert result.available_filter_counts["suppliers"] == {}
    assert result.launcher_view is not None
    assert result.launcher_view["available_filter_counts"]["brands"] == {"Free Feather": 1}


def test_build_local_task_process_result_exposes_first_class_onboarding_fields() -> None:
    result = build_local_task_process_result(
        manifest=RunManifest(
            task_name="site_onboarding_discovery",
            shop="metro",
            intent="fish_catalog",
            status="discovery_only",
            summary={
                "category_tree": [{"name": "Рыба", "url": "https://example.test/fish"}],
                "selected_categories": ["Рыба"],
                "diagnostics_summary": {"known_backend": True},
                "catalog_discovery": {"surface_type": "category_tree"},
                "intent_category_links": [{"name": "Рыба", "url": "https://example.test/fish"}],
            },
        )
    )

    assert result.category_tree == [{"name": "Рыба", "url": "https://example.test/fish"}]
    assert result.selected_categories == ["Рыба"]
    assert result.diagnostics_summary == {"known_backend": True}
    assert result.catalog_discovery == {"surface_type": "category_tree"}
    assert result.intent_category_links == [{"name": "Рыба", "url": "https://example.test/fish"}]
    assert result.launcher_view is not None
    assert result.launcher_view["category_tree"] == [{"name": "Рыба", "url": "https://example.test/fish"}]
    assert result.launcher_view["selected_categories"] == ["Рыба"]
    assert result.launcher_view["catalog_discovery"] == {"surface_type": "category_tree"}


def test_run_local_task_subprocess_tolerates_stdout_preamble(monkeypatch, tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    payload = RunManifest(
        task_name="site_onboarding_discovery",
        shop="pyaterochka",
        intent="fish_catalog",
        status="runtime_ready",
    ).model_dump_json(indent=2)

    def fake_run(*args, **kwargs):
        del args, kwargs
        return subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=f"Skipping unknown patch audio:seed : 1\n{payload}",
            stderr="",
        )

    monkeypatch.setattr("utils.local_task_adapter.subprocess.run", fake_run)

    result = run_local_task_subprocess(
        task_name="site_onboarding_discovery",
        task_input={"site_url": "https://5ka.ru/"},
        root_dir=tmp_path,
        python_executable=sys.executable,
    )

    assert result.manifest.task_name == "site_onboarding_discovery"
    assert result.manifest.status == "runtime_ready"


def test_run_local_task_subprocess_raises_runtime_error_with_stderr(monkeypatch, tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    def fake_run(*args, **kwargs):
        del args, kwargs
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["python", "scripts/run_local_task.py"],
            stderr="research failed on protected site",
            output="",
        )

    monkeypatch.setattr("utils.local_task_adapter.subprocess.run", fake_run)

    try:
        run_local_task_subprocess(
            task_name="site_onboarding_discovery",
            task_input={"site_url": "https://5ka.ru/"},
            root_dir=tmp_path,
            python_executable=sys.executable,
        )
    except RuntimeError as error:
        assert str(error) == "research failed on protected site"
    else:
        raise AssertionError("Expected RuntimeError from failed local task subprocess.")


def _prepare_root(root_dir: Path) -> None:
    (root_dir / "data").mkdir(parents=True, exist_ok=True)
    (root_dir / "knowledge_base").mkdir(parents=True, exist_ok=True)
    source = Path("knowledge_base/pyaterochka.md").read_text(encoding="utf-8")
    (root_dir / "knowledge_base" / "pyaterochka.md").write_text(source, encoding="utf-8")
