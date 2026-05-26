"""Launcher-safe subprocess adapter for local tasks."""

from __future__ import annotations

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
    full_catalog_tree: list[dict[str, Any]] | None = None
    full_catalog_links: list[dict[str, Any]] | None = None
    selected_categories: list[str] | None = None
    diagnostics_summary: dict[str, Any] | None = None
    catalog_discovery: dict[str, Any] | None = None
    intent_category_links: list[dict[str, Any]] | None = None
    found_filters: dict[str, Any] | None = None
    launcher_view: dict[str, Any] | None = None


def build_local_task_command(
    *,
    task_name: str,
    root_dir: Path | str | None = None,
    python_executable: str | None = None,
) -> list[str]:
    """Build one launcher task command using stdin JSON transport."""
    python_path = python_executable or sys.executable
    command = [
        python_path,
        str(RUN_LOCAL_TASK_SCRIPT),
        "--task",
        str(task_name),
        "--input-stdin",
    ]
    if root_dir is not None:
        command.extend(["--root-dir", str(Path(root_dir))])
    return command


def run_local_task_subprocess(
    *,
    task_name: str,
    task_input: dict[str, Any],
    root_dir: Path | str,
    python_executable: str | None = None,
    show_summary: bool = False,
    timeout_seconds: int = 900,
) -> LocalTaskProcessResult:
    """Run one local task via subprocess and parse the returned result."""
    command = build_local_task_command(
        task_name=task_name,
        root_dir=root_dir,
        python_executable=python_executable,
    )
    if show_summary:
        command.append("--summary")
    input_payload = json.dumps(task_input, ensure_ascii=False)
    try:
        result = subprocess.run(
            command,
            cwd=str(root_dir),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            input=input_payload,
            timeout=timeout_seconds,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(_build_subprocess_failure_message(error)) from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(_build_subprocess_timeout_message(error, timeout_seconds)) from error
    manifest = RunManifest(**_extract_manifest_payload(result.stdout))
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
        full_catalog_tree=_summary_dict_list(summary, "full_catalog_tree"),
        full_catalog_links=_summary_dict_list(summary, "full_catalog_links"),
        selected_categories=_summary_str_list(summary, "selected_categories"),
        diagnostics_summary=_summary_dict(summary, "diagnostics_summary"),
        catalog_discovery=_summary_dict(summary, "catalog_discovery"),
        intent_category_links=_summary_dict_list(summary, "intent_category_links"),
        found_filters=_summary_dict(summary, "found_filters"),
        launcher_view=build_launcher_task_view(
            manifest=manifest,
            summary_text=stderr.strip(),
            report_summary=_summary_dict(summary, "report_summary"),
            export_summary=_summary_dict(summary, "export_summary"),
            available_filter_counts=_nested_count_dict(summary, "available_filter_counts"),
            category_tree=_summary_dict_list(summary, "category_tree"),
            full_catalog_tree=_summary_dict_list(summary, "full_catalog_tree"),
            full_catalog_links=_summary_dict_list(summary, "full_catalog_links"),
            selected_categories=_summary_str_list(summary, "selected_categories"),
            diagnostics_summary=_summary_dict(summary, "diagnostics_summary"),
            catalog_discovery=_summary_dict(summary, "catalog_discovery"),
            intent_category_links=_summary_dict_list(summary, "intent_category_links"),
            found_filters=_summary_dict(summary, "found_filters"),
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


def _extract_manifest_payload(stdout: str) -> dict[str, Any]:
    """Extract one JSON manifest from noisy subprocess stdout."""
    payload_text = str(stdout or "").strip()
    if not payload_text:
        raise ValueError("Local task subprocess returned empty stdout instead of run manifest JSON.")
    decoder = json.JSONDecoder()
    for index, char in enumerate(payload_text):
        if char != "{":
            continue
        try:
            payload, _end = decoder.raw_decode(payload_text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    snippet = payload_text[:300].replace("\n", "\\n")
    raise ValueError(f"Local task subprocess stdout did not contain manifest JSON. Snippet: {snippet}")


def _build_subprocess_failure_message(error: subprocess.CalledProcessError) -> str:
    """Render one compact launcher-safe subprocess failure message."""
    stderr = str(getattr(error, "stderr", "") or "").strip()
    stdout = str(getattr(error, "stdout", "") or "").strip()
    if stderr:
        return stderr
    if stdout:
        return f"Local task subprocess failed before manifest JSON was returned. Stdout: {stdout[:300]}"
    return f"Local task subprocess failed with exit code {error.returncode}."


def _build_subprocess_timeout_message(
    error: subprocess.TimeoutExpired,
    timeout_seconds: int,
) -> str:
    """Render one compact launcher-safe subprocess timeout message."""
    command = getattr(error, "cmd", None)
    command_text = " ".join(str(part) for part in command) if isinstance(command, list) else str(command or "")
    suffix = f" Command: {command_text[:160]}" if command_text else ""
    return f"Local task subprocess timed out after {timeout_seconds} seconds.{suffix}"
