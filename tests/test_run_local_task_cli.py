import base64
import subprocess
import sys
from pathlib import Path

from scripts.run_local_task import _render_summary


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
    input_path.write_text(
        '{"site_url":"https://unknown-store.example","intent":"fish_catalog","selected_categories":["Рыба"]}',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--task",
            "site_onboarding_discovery",
            "--input-file",
            str(input_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert '"task_name": "site_onboarding_discovery"' in result.stdout
    assert '"status": "scaffold_ready"' in result.stdout


def test_run_local_task_cli_accepts_input_from_stdin() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--task",
            "site_onboarding_discovery",
            "--input-stdin",
        ],
        input='{"site_url":"https://unknown-store.example","intent":"fish_catalog","selected_categories":["Рыба"]}',
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert '"task_name": "site_onboarding_discovery"' in result.stdout
    assert '"status": "scaffold_ready"' in result.stdout
    assert '"selected_categories": [' in result.stdout
    assert '"Рыба"' in result.stdout


def test_run_local_task_cli_accepts_input_base64() -> None:
    payload = '{"site_url":"https://unknown-store.example","intent":"fish_catalog","selected_categories":["Рыба"]}'
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--task",
            "site_onboarding_discovery",
            "--input-base64",
            encoded,
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert '"task_name": "site_onboarding_discovery"' in result.stdout
    assert '"status": "scaffold_ready"' in result.stdout
    assert '"selected_categories": [' in result.stdout
    assert '"Рыба"' in result.stdout


def test_run_local_task_cli_prints_compact_summary_to_stderr(tmp_path: Path) -> None:
    input_path = tmp_path / "task_input.json"
    input_path.write_text(
        '{"site_url":"https://unknown-store.example","intent":"fish_catalog","selected_categories":["Рыба"]}',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_local_task.py",
            "--task",
            "site_onboarding_discovery",
            "--input-file",
            str(input_path),
            "--summary",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert '"task_name": "site_onboarding_discovery"' in result.stdout
    assert "Task: site_onboarding_discovery" in result.stderr
    assert "Status: scaffold_ready" in result.stderr
    assert "Shop: unknown-store_example" in result.stderr
    assert "Selected categories: Рыба" in result.stderr


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
