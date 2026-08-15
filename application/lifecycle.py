"""Shared workflow-to-legacy lifecycle projection."""

from __future__ import annotations

from typing import Any

from application.contracts import TerminalOutcome, WorkflowRunResult
from models.task_actor import RunManifest


def project_legacy_manifest(
    result: WorkflowRunResult,
    *,
    task_name: str,
    shop: str,
    intent: str,
    task_input: dict[str, Any] | None = None,
) -> RunManifest:
    status = {TerminalOutcome.READY: "ok", TerminalOutcome.MANUAL_ACTION_REQUIRED: "needs_operator"}.get(
        result.terminal_outcome, "failed"
    )
    return RunManifest(
        task_name=task_name,
        shop=shop,
        intent=intent,
        input=dict(task_input or {}),
        status=status,
        started_at=result.started_at,
        finished_at=result.finished_at,
        artifact_paths=dict(result.artifact_paths),
        summary={
            "terminal_outcome": result.terminal_outcome.value,
            "reason_code": result.reason_code,
            "message": result.message,
            "retryable": result.retryable,
            "event_summary": {
                "count": len(result.events),
                "terminal_count": sum(event.event_type.value == "terminal" for event in result.events),
                "last_sequence": result.events[-1].sequence if result.events else 0,
            },
            "result_summary": dict(result.result),
        },
        error="" if result.terminal_outcome is TerminalOutcome.READY else result.message,
    )


def launcher_status_for_manifest(manifest: RunManifest) -> str:
    outcome = str((manifest.summary or {}).get("terminal_outcome", ""))
    if outcome:
        return "succeeded" if manifest.status == "ok" and outcome == "ready" else "failed"
    return "succeeded" if manifest.status == "ok" else "failed"
