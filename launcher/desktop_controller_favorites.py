"""Controller helpers for workspace favorites."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from launcher.desktop_project_workspace import profile_db_path
from launcher.desktop_state_readers import product_items
from launcher.desktop_workspace_journal import record_workspace_journal_event
from models.launcher_state import WorkspaceFavoriteState
from utils.store_profile_repository import StoreProfileRepository
from utils.workspace_favorites import resolve_favorite_refresh_target


def load_workspace_favorites(controller: Any) -> list[WorkspaceFavoriteState]:
    """Load favorites for the active project workspace."""
    rows = _repository(controller).list_workspace_favorites(_workspace_id(controller))
    controller.state.favorites.items = [WorkspaceFavoriteState(**row) for row in rows]
    return controller.state.favorites.items


def add_current_profile_favorite(controller: Any) -> list[WorkspaceFavoriteState]:
    """Add the current store profile/site as a favorite."""
    state = controller.state
    stable_key = state.profile.site_url or state.profile.domain or state.profile.profile_id
    if not stable_key:
        return load_workspace_favorites(controller)
    display_label = state.profile.display_name or state.profile.domain or stable_key
    _repository(controller).upsert_workspace_favorite(
        workspace_id=_workspace_id(controller),
        profile_id=state.profile.profile_id,
        favorite_type="store",
        display_label=display_label,
        stable_key=stable_key,
        store_label=display_label,
        source_version_id=state.profile.profile_version_id,
        payload={"shop": state.profile.shop, "site_url": state.profile.site_url, "domain": state.profile.domain},
        refresh_capability=_profile_refresh_capability(state),
    )
    _record_favorite_event(controller, event_type="favorite_added", title="\u041c\u0430\u0433\u0430\u0437\u0438\u043d \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d \u0432 \u0438\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435")
    return load_workspace_favorites(controller)


def add_selected_catalog_favorites(controller: Any) -> list[WorkspaceFavoriteState]:
    """Add selected catalog nodes as favorites."""
    state = controller.state
    for node in state.selection.selected_catalog_nodes:
        if not isinstance(node, dict):
            continue
        stable_key = str(node.get("url") or node.get("name") or "").strip()
        label = str(node.get("name") or stable_key).strip()
        if not stable_key or not label:
            continue
        _repository(controller).upsert_workspace_favorite(
            workspace_id=_workspace_id(controller),
            profile_id=state.profile.profile_id,
            favorite_type="catalog_node",
            display_label=label,
            stable_key=stable_key,
            store_label=_store_label(state),
            source_version_id=state.profile.profile_version_id,
            payload={"name": label, "url": str(node.get("url") or "")},
            refresh_capability=_profile_refresh_capability(state),
        )
    _record_favorite_event(controller, event_type="favorite_added", title="\u0420\u0430\u0437\u0434\u0435\u043b\u044b \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u044b \u0432 \u0438\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435")
    return load_workspace_favorites(controller)


def add_selected_product_favorites(controller: Any) -> list[WorkspaceFavoriteState]:
    """Add selected products as favorites."""
    state = controller.state
    selected_ids = {str(item).strip() for item in state.selection.selected_product_ids if str(item).strip()}
    for product in product_items(state):
        product_id = _product_id(product)
        if selected_ids and product_id not in selected_ids:
            continue
        stable_key = _product_stable_key(product)
        label = str(product.get("name") or stable_key).strip()
        if not stable_key or not label:
            continue
        _repository(controller).upsert_workspace_favorite(
            workspace_id=_workspace_id(controller),
            profile_id=state.profile.profile_id,
            favorite_type="product",
            display_label=label,
            stable_key=stable_key,
            store_label=_store_label(state),
            source_version_id=state.profile.profile_version_id,
            payload={"id": product_id, "url": _product_url(product), "name": label},
            refresh_capability=_profile_refresh_capability(state),
        )
    _record_favorite_event(controller, event_type="favorite_added", title="\u0422\u043e\u0432\u0430\u0440\u044b \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u044b \u0432 \u0438\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435")
    return load_workspace_favorites(controller)


def remove_workspace_favorites(controller: Any, favorite_ids: list[str]) -> list[WorkspaceFavoriteState]:
    """Remove selected favorites from the active workspace."""
    repository = _repository(controller)
    workspace_id = _workspace_id(controller)
    for favorite_id in favorite_ids:
        repository.remove_workspace_favorite(workspace_id, favorite_id)
    controller.state.favorites.selected_favorite_ids = []
    _record_favorite_event(controller, event_type="favorite_removed", title="\u0418\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u043e")
    return load_workspace_favorites(controller)


def refresh_workspace_favorites(
    controller: Any,
    *,
    favorite_ids: list[str] | None = None,
    all_refreshable: bool = False,
) -> list[WorkspaceFavoriteState]:
    """Refresh selected/all favorites with per-item results."""
    repository = _repository(controller)
    workspace_id = _workspace_id(controller)
    current = repository.list_workspace_favorites(workspace_id)
    selected = _selected_favorites(current, favorite_ids=favorite_ids, all_refreshable=all_refreshable)
    run_id = f"favorite-refresh:{uuid4().hex[:12]}"
    counts = {"success": 0, "skipped": 0, "failed": 0}
    for favorite in selected:
        status, reason, version_id = _refresh_one_favorite(controller, favorite)
        counts[status if status in counts else "failed"] += 1
        repository.record_favorite_refresh_result(
            workspace_id=workspace_id,
            refresh_run_id=run_id,
            favorite_id=str(favorite["favorite_id"]),
            profile_id=str(favorite.get("profile_id") or ""),
            status=status,
            reason=reason,
            saved_version_id=version_id,
        )
    overall = _overall_status(counts, requested=len(selected))
    repository.record_favorite_refresh_run(
        workspace_id=workspace_id,
        refresh_run_id=run_id,
        requested_scope="all_refreshable" if all_refreshable else "selected",
        overall_status=overall,
        requested_count=len(selected),
        success_count=counts["success"],
        skipped_count=counts["skipped"],
        failed_count=counts["failed"],
    )
    controller.state.favorites.latest_refresh = controller.state.favorites.latest_refresh.model_copy(
        update={
            "refresh_run_id": run_id,
            "workspace_id": workspace_id,
            "requested_scope": "all_refreshable" if all_refreshable else "selected",
            "overall_status": overall,
            "requested_count": len(selected),
            "success_count": counts["success"],
            "skipped_count": counts["skipped"],
            "failed_count": counts["failed"],
        }
    )
    _record_favorite_event(
        controller,
        event_type="favorite_refresh",
        title="\u0418\u0437\u0431\u0440\u0430\u043d\u043d\u043e\u0435 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u043e",
    )
    return load_workspace_favorites(controller)


def _repository(controller: Any) -> StoreProfileRepository:
    return StoreProfileRepository(profile_db_path(controller.root_dir))


def _selected_favorites(
    favorites: list[dict[str, Any]],
    *,
    favorite_ids: list[str] | None,
    all_refreshable: bool,
) -> list[dict[str, Any]]:
    if all_refreshable:
        return list(favorites)
    selected_ids = {str(item).strip() for item in (favorite_ids or []) if str(item).strip()}
    return [favorite for favorite in favorites if str(favorite["favorite_id"]) in selected_ids]


def _refresh_one_favorite(controller: Any, favorite: dict[str, Any]) -> tuple[str, str, str]:
    decision = resolve_favorite_refresh_target(favorite)
    if decision["status"] != "supported":
        return decision["status"], decision["reason"], ""
    favorite_type = str(favorite["favorite_type"])
    if favorite_type == "store":
        return _refresh_store_favorite(controller, favorite)
    if favorite_type == "catalog_node":
        return _refresh_catalog_favorite(controller, favorite)
    return "skipped", "product refresh needs a product adapter target", ""


def _refresh_store_favorite(controller: Any, favorite: dict[str, Any]) -> tuple[str, str, str]:
    profile_id = str(favorite.get("profile_id") or "")
    version_id = str(favorite.get("source_version_id") or "")
    if profile_id and version_id:
        loaded = controller.load_profile_session(workspace_id=_workspace_id(controller), profile_id=profile_id, version_id=version_id)
        return ("success", "profile session loaded", version_id) if loaded else ("failed", "profile session not found", "")
    return "success", "store favorite is ready", ""


def _refresh_catalog_favorite(controller: Any, favorite: dict[str, Any]) -> tuple[str, str, str]:
    payload = favorite.get("payload") if isinstance(favorite.get("payload"), dict) else {}
    node = {"name": str(payload.get("name") or favorite["display_label"]), "url": str(payload.get("url") or favorite["stable_key"])}
    profile = _profile_for_favorite(controller, favorite)
    if not profile:
        return "failed", "owning store profile not found", ""
    _apply_profile_for_refresh(controller, profile)
    controller.state.selection.selected_catalog_nodes = [node]
    controller.state.selection.categories = [node["name"]]
    controller.run_selected_export()
    return "success", "catalog node refreshed", str(controller.state.profile.profile_version_id)


def _profile_for_favorite(controller: Any, favorite: dict[str, Any]) -> dict[str, str]:
    profile_id = str(favorite.get("profile_id") or "")
    for profile in _repository(controller).list_profiles(workspace_id=_workspace_id(controller)):
        if str(profile.get("profile_id") or "") == profile_id:
            return profile
    return {}


def _apply_profile_for_refresh(controller: Any, profile: dict[str, str]) -> None:
    controller.state.profile.profile_id = str(profile.get("profile_id") or "")
    controller.state.profile.shop = str(profile.get("shop") or "")
    controller.state.profile.site_url = str(profile.get("site_url") or "")
    controller.state.profile.domain = str(profile.get("domain") or "")
    controller.state.profile.display_name = str(profile.get("display_name") or "")
    controller.state.profile.diagnostics["runtime_status"] = str(profile.get("runtime_status") or "")


def _overall_status(counts: dict[str, int], *, requested: int) -> str:
    if requested == 0:
        return "skipped"
    if counts["failed"] and counts["success"]:
        return "partial"
    if counts["failed"]:
        return "failed"
    if counts["skipped"] and counts["success"]:
        return "partial"
    if counts["success"]:
        return "success"
    return "skipped"


def _workspace_id(controller: Any) -> str:
    return str(controller.state.workspace.workspace_id or "default").strip() or "default"


def _store_label(state: Any) -> str:
    return state.profile.display_name or state.profile.domain or state.profile.shop or ""


def _profile_refresh_capability(state: Any) -> str:
    status = str(state.profile.diagnostics.get("runtime_status") or "").strip()
    return "supported" if status == "runtime_ready" else "limited"


def _product_id(product: dict[str, Any]) -> str:
    return str(product.get("id") or product.get("product_id") or "").strip()


def _product_url(product: dict[str, Any]) -> str:
    return str(product.get("product_url") or product.get("product_link") or product.get("url") or "").strip()


def _product_stable_key(product: dict[str, Any]) -> str:
    return _product_url(product) or _product_id(product)


def _record_favorite_event(controller: Any, *, event_type: str, title: str) -> None:
    record_workspace_journal_event(
        controller,
        event_type=event_type,
        title=title,
        status="succeeded",
        counts={"favorites": len(controller.state.favorites.items)},
    )
