"""Workspace journal writes for launcher actions."""

from __future__ import annotations

from typing import Any

from launcher.desktop_project_workspace import profile_db_path
from utils.store_profile_repository import StoreProfileRepository


def record_workspace_journal_event(
    controller: Any,
    *,
    event_type: str,
    title: str,
    message: str = "",
    status: str = "info",
    counts: dict[str, Any] | None = None,
    artifact_refs: dict[str, Any] | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> None:
    """Write one user-facing workspace journal event."""
    state = controller.state
    StoreProfileRepository(profile_db_path(controller.root_dir)).record_workspace_event(
        workspace_id=state.workspace.workspace_id or "default",
        profile_id=state.profile.profile_id or state.research.active_profile_id,
        version_id=state.profile.profile_version_id or state.research.active_profile_version_id,
        event_type=event_type,
        title=title,
        message=message,
        status=status,
        counts=counts or _state_counts(state),
        artifact_refs=artifact_refs or state.result.artifact_paths,
        diagnostics=diagnostics or state.profile.diagnostics,
    )


def list_workspace_journal_events(controller: Any, *, limit: int = 5) -> list[dict[str, Any]]:
    """Return recent journal events for the active workspace."""
    return StoreProfileRepository(profile_db_path(controller.root_dir)).list_workspace_events(
        controller.state.workspace.workspace_id or "default",
        limit=limit,
    )


def record_task_failed_event(controller: Any) -> None:
    """Record the current failed task state."""
    record_workspace_journal_event(
        controller,
        event_type="task_failed",
        title="Задача завершилась с ошибкой",
        message=controller.state.task.message,
        status="failed",
        diagnostics={"error": controller.state.task.last_error},
    )


def record_task_completed_event(controller: Any, *, event_type: str) -> None:
    """Record the current completed task state."""
    record_workspace_journal_event(
        controller,
        event_type=event_type or "launcher_task",
        title="Задача лаунчера завершена",
        message=controller.state.task.message,
        status=controller.state.task.status,
    )


def _state_counts(state: Any) -> dict[str, Any]:
    return {
        "catalog_nodes": len(state.catalog.full_links),
        "products": len(state.products.items),
        "filtered_products": state.result.products_count,
    }
