import base64
import subprocess
import sys
from pathlib import Path

from scripts.run_local_task import _render_summary


_FILTER_INPUT = '{"selection":{"shop":"pyaterochka","intent":"fish_catalog","categories":["Рыба"]},"filters":{}}'


def test_run_local_task_cli_lists_registered_tasks() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--list",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "pyaterochka_fish_export" in result.stdout
    assert "pyaterochka_wine_export" in result.stdout
    assert "site_onboarding_discovery" in result.stdout


def test_run_local_task_cli_accepts_input_file(tmp_path: Path) -> None:
    input_path = tmp_path / "task_input.json"
    input_path.write_text(_FILTER_INPUT, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--task",
            "store_report_filter_options",
            "--input-file",
            str(input_path),
            "--root-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert '"task_name": "store_report_filter_options"' in result.stdout
    assert '"status": "empty"' in result.stdout


def test_run_local_task_cli_accepts_input_from_stdin(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--task",
            "store_report_filter_options",
            "--input-stdin",
            "--root-dir",
            str(tmp_path),
        ],
        input=_FILTER_INPUT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert '"task_name": "store_report_filter_options"' in result.stdout
    assert '"status": "empty"' in result.stdout
    assert '"categories": [' in result.stdout
    assert '"Рыба"' in result.stdout


def test_run_local_task_cli_accepts_input_base64(tmp_path: Path) -> None:
    encoded = base64.b64encode(_FILTER_INPUT.encode("utf-8")).decode("ascii")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--task",
            "store_report_filter_options",
            "--input-base64",
            encoded,
            "--root-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert '"task_name": "store_report_filter_options"' in result.stdout
    assert '"status": "empty"' in result.stdout
    assert '"categories": [' in result.stdout
    assert '"Рыба"' in result.stdout


def test_run_local_task_cli_prints_compact_summary_to_stderr(tmp_path: Path) -> None:
    input_path = tmp_path / "task_input.json"
    input_path.write_text(_FILTER_INPUT, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--task",
            "store_report_filter_options",
            "--input-file",
            str(input_path),
            "--root-dir",
            str(tmp_path),
            "--summary",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert '"task_name": "store_report_filter_options"' in result.stdout
    assert "Task: store_report_filter_options" in result.stderr
    assert "Status: empty" in result.stderr
    assert "Shop: pyaterochka" in result.stderr
    assert "Products: 0" in result.stderr


def test_render_summary_includes_wine_breakdown_sections() -> None:
    manifest = {
        "task_name": "pyaterochka_wine_export",
        "status": "ok",
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "summary": {
            "products_count": 38,
            "categories": ["Безалкогольное вино", "Пиво, вино, энергетики"],
            "export_summary": {
                "wine_breakdown": {
                    "style_counts": {"Тихое": 35, "Игристое": 3},
                    "alcohol_type_counts": {"Безалкогольное": 37, "Алкогольное": 1},
                    "sugar_class_counts": {"Полусладкое": 8, "Полусухое": 3},
                    "color_counts": {"Белое": 15, "Красное": 7},
                }
            },
        },
    }

    rendered = _render_summary(manifest)

    assert "Task: pyaterochka_wine_export" in rendered
    assert "Products: 38" in rendered
    assert "Wine styles: Тихое=35, Игристое=3" in rendered
    assert "Alcohol types: Безалкогольное=37, Алкогольное=1" in rendered
    assert "Sugar classes: Полусладкое=8, Полусухое=3" in rendered
    assert "Colors: Белое=15, Красное=7" in rendered
