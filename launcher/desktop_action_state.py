"""Enabled-state rules for desktop launcher actions."""

from __future__ import annotations

from launcher.desktop_state_readers import report_product_items
from launcher.desktop_store_identity import active_store_code
from models.launcher_state import LauncherAppState
from utils.store_catalog_registry import get_store_export_backend


def build_action_enabled_map(state: LauncherAppState) -> dict[str, bool]:
    """Return one stable enabled map for launcher action buttons."""
    if state.task.status == "running":
        return {
            "onboarding": False,
            "run_export": False,
            "build_report": False,
            "save_settings": False,
            "open_excel": False,
            "open_folder": False,
            "load_profile_session": False,
            "save_profile_session": False,
            "add_favorite_profile": False,
            "add_favorite_catalog": False,
            "add_favorite_products": False,
            "refresh_selected_favorites": False,
            "refresh_all_favorites": False,
            "remove_favorites": False,
            "select_report_columns": False,
            "clear_report_columns": False,
        }
    has_categories = bool(state.selection.categories)
    has_catalog_tree = bool(state.catalog.full_tree or state.catalog.full_links)
    has_export_targets = bool(state.selection.selected_catalog_nodes) if has_catalog_tree else has_categories
    has_products = bool(report_product_items(state))
    has_report_columns = bool(state.report.available_columns)
    has_selected_report_columns = bool(state.report.selected_columns) or (
        has_report_columns and not state.report.columns_touched
    )
    has_export_backend = _has_export_backend(state)
    return {
        "onboarding": True,
        "run_export": has_export_targets and has_export_backend,
        "build_report": has_products and has_selected_report_columns,
        "save_settings": True,
        "open_excel": bool(str(state.result.excel_path or "").strip()),
        "open_folder": bool(str(state.result.report_dir or "").strip()),
        "load_profile_session": True,
        "save_profile_session": _has_current_profile(state),
        "add_favorite_profile": _has_current_profile(state),
        "add_favorite_catalog": bool(state.selection.selected_catalog_nodes),
        "add_favorite_products": bool(state.selection.selected_product_ids),
        "refresh_selected_favorites": bool(state.favorites.selected_favorite_ids),
        "refresh_all_favorites": bool(state.favorites.items),
        "remove_favorites": bool(state.favorites.selected_favorite_ids),
        "select_report_columns": has_report_columns,
        "clear_report_columns": has_report_columns,
    }


def _has_current_profile(state: LauncherAppState) -> bool:
    return bool(str(state.profile.profile_id or state.profile.site_url or "").strip())


def _has_export_backend(state: LauncherAppState) -> bool:
    shop = active_store_code(state)
    if not shop:
        return False
    try:
        get_store_export_backend(shop, state.selection.intent)
    except ValueError:
        return False
    return True
