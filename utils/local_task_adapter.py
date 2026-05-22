"""Launcher-safe subprocess adapter for local tasks."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from models.task_actor import RunManifest
from utils.launcher_task_view import build_launcher_task_view

ROOT_DIR = Path(__file__).resolve().parents[1]
RUN_LOCAL_TASK_SCRIPT = ROOT_DIR / "scripts" / "run_local_task.py"


@dataclass(frozen=True)
class LocalTaskProcessResult:
    """Structured result from one launcher-safe local task subprocess."""

    manifest: RunManifest
    summary_text: str = ""
    stdout: str = ""
    stderr: str = ""
    report_summary: dict[str, Any] | None = None
    export_summary: dict[str, Any] | None = None
    available_filter_counts: dict[str, dict[str, int]] | None = None
    category_tree: list[dict[str, Any]] | None = None
    selected_categories: list[str] | None = None
    diagnostics_summary: dict[str, Any] | None = None
    catalog_discovery: dict[str, Any] | None = None
    intent_category_links: list[dict[str, Any]] | None = None
    launcher_view: dict[str, Any] | None = None


def build_local_task_command(
    *,
    task_name: str,
    task_input: dict[str, Any],
    python_executable: str | None = None,
) -> list[str]:
    """Build one shell-safe local task command using base64 JSON transport."""
    encoded = base64.b64encode(
        json.dumps(task_input, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    python_path = python_executable or sys.executable
    return [
        python_path,
        str(RUN_LOCAL_TASK_SCRIPT),
        "--task",
        str(task_name),
        "--input-base64",
        encoded,
    ]


def run_local_task_subprocess(
    *,
    task_name: str,
    task_input: dict[str, Any],
    root_dir: Path | str,
    python_executable: str | None = None,
    show_summary: bool = False,
) -> LocalTaskProcessResult:
    """Run one local task via subprocess and parse the returned result."""
    command = build_local_task_command(
        task_name=task_name,
        task_input=task_input,
        python_executable=python_executable,
    )
    if show_summary:
        command.append("--summary")
    result = subprocess.run(
        command,
        cwd=str(root_dir),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    manifest = RunManifest(**json.loads(result.stdout))
    return build_local_task_process_result(
        manifest=manifest,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def build_local_task_process_result(
    *,
    manifest: RunManifest,
    stdout: str = "",
    stderr: str = "",
) -> LocalTaskProcessResult:
    """Build one normalized launcher-facing task result from a manifest."""
    summary = dict(manifest.summary or {})
    return LocalTaskProcessResult(
        manifest=manifest,
        summary_text=stderr.strip(),
        stdout=stdout,
        stderr=stderr,
        report_summary=_summary_dict(summary, "report_summary"),
        export_summary=_summary_dict(summary, "export_summary"),
        available_filter_counts=_nested_count_dict(summary, "available_filter_counts"),
        category_tree=_summary_dict_list(summary, "category_tree"),
        selected_categories=_summary_str_list(summary, "selected_categories"),
        diagnostics_summary=_summary_dict(summary, "diagnostics_summary"),
        catalog_discovery=_summary_dict(summary, "catalog_discovery"),
        intent_category_links=_summary_dict_list(summary, "intent_category_links"),
        launcher_view=build_launcher_task_view(
            manifest=manifest,
            summary_text=stderr.strip(),
            report_summary=_summary_dict(summary, "report_summary"),
            export_summary=_summary_dict(summary, "export_summary"),
            available_filter_counts=_nested_count_dict(summary, "available_filter_counts"),
            category_tree=_summary_dict_list(summary, "category_tree"),
            selected_categories=_summary_str_list(summary, "selected_categories"),
            diagnostics_summary=_summary_dict(summary, "diagnostics_summary"),
            catalog_discovery=_summary_dict(summary, "catalog_discovery"),
            intent_category_links=_summary_dict_list(summary, "intent_category_links"),
        ),
    )


def _summary_dict(summary: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = summary.get(key)
    if isinstance(value, dict):
        return value
    return None


def _nested_count_dict(summary: dict[str, Any], key: str) -> dict[str, dict[str, int]] | None:
    value = summary.get(key)
    if not isinstance(value, dict):
        return None
    result: dict[str, dict[str, int]] = {}
    for outer_key, nested in value.items():
        if isinstance(nested, dict):
            result[str(outer_key)] = {
                str(inner_key): int(inner_value)
                for inner_key, inner_value in nested.items()
                if isinstance(inner_value, int)
            }
    return result or None


def _summary_str_list(summary: dict[str, Any], key: str) -> list[str] | None:
    value = summary.get(key)
    if not isinstance(value, list):
        return None
    return [str(item) for item in value]


def _summary_dict_list(summary: dict[str, Any], key: str) -> list[dict[str, Any]] | None:
    value = summary.get(key)
    if not isinstance(value, list):
        return None
    result = [item for item in value if isinstance(item, dict)]
    return result or None
