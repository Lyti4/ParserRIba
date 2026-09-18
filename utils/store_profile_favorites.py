"""Repository mixin for workspace favorites."""

from __future__ import annotations

from typing import Any

from utils.store_profile_favorite_rows import (
    get_favorite_row,
    list_favorite_rows,
    record_refresh_result_row,
    record_refresh_run_row,
    remove_favorite_row,
    upsert_favorite_row,
)
from utils.store_profile_schema import initialize_store_profile_schema


class StoreProfileFavoritesMixin:
    """Public repository methods for workspace favorites."""

    def upsert_workspace_favorite(
        self,
        *,
        workspace_id: str = "default",
        profile_id: str = "",
        favorite_type: str,
        display_label: str,
        stable_key: str,
        store_label: str = "",
        source_version_id: str = "",
        payload: dict[str, Any] | None = None,
        refresh_capability: str = "unresolved",
        favorite_id: str = "",
    ) -> dict[str, Any]:
        self.initialize()
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return upsert_favorite_row(
                connection,
                workspace_id=workspace_id,
                profile_id=profile_id,
                favorite_type=favorite_type,
                display_label=display_label,
                stable_key=stable_key,
                store_label=store_label,
                source_version_id=source_version_id,
                payload=payload,
                refresh_capability=refresh_capability,
                favorite_id=favorite_id,
            )

    def list_workspace_favorites(self, workspace_id: str, *, profile_id: str = "") -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return list_favorite_rows(connection, workspace_id, profile_id=profile_id)

    def get_workspace_favorite(self, workspace_id: str, favorite_id: str) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return get_favorite_row(connection, workspace_id, favorite_id)

    def remove_workspace_favorite(self, workspace_id: str, favorite_id: str) -> bool:
        if not self.db_path.exists():
            return False
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return remove_favorite_row(connection, workspace_id, favorite_id)

    def record_favorite_refresh_run(
        self,
        *,
        workspace_id: str = "default",
        refresh_run_id: str,
        requested_scope: str,
        overall_status: str = "partial",
        requested_count: int = 0,
        success_count: int = 0,
        skipped_count: int = 0,
        failed_count: int = 0,
        started_at: str = "",
        finished_at: str = "",
    ) -> dict[str, Any]:
        self.initialize()
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return record_refresh_run_row(
                connection,
                workspace_id=workspace_id,
                refresh_run_id=refresh_run_id,
                requested_scope=requested_scope,
                overall_status=overall_status,
                requested_count=requested_count,
                success_count=success_count,
                skipped_count=skipped_count,
                failed_count=failed_count,
                started_at=started_at,
                finished_at=finished_at,
            )

    def record_favorite_refresh_result(
        self,
        *,
        workspace_id: str = "default",
        refresh_run_id: str,
        favorite_id: str,
        status: str,
        profile_id: str = "",
        reason: str = "",
        saved_version_id: str = "",
        artifact_refs: dict[str, Any] | None = None,
        created_at: str = "",
    ) -> dict[str, Any]:
        self.initialize()
        with self._connect() as connection:
            initialize_store_profile_schema(connection)
            return record_refresh_result_row(
                connection,
                workspace_id=workspace_id,
                refresh_run_id=refresh_run_id,
                favorite_id=favorite_id,
                status=status,
                profile_id=profile_id,
                reason=reason,
                saved_version_id=saved_version_id,
                artifact_refs=artifact_refs,
                created_at=created_at,
            )
