"""PySide6 desktop launcher shell for ParserRIba."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from launcher.desktop_action_state import build_action_enabled_map
from launcher.desktop_background_task import start_background_action
from launcher.desktop_command_strip import refresh_command_strip
from launcher.desktop_controller import DesktopLauncherController
from launcher.desktop_error_panel import refresh_error_panel
from launcher.desktop_filter_apply import apply_filter_change
from launcher.desktop_filter_panel import FILTER_WIDGET_KEYS, collect_filter_selections, refresh_filter_widgets
from launcher.desktop_favorites import refresh_favorites_box
from launcher.desktop_inspector_panel import refresh_right_inspector
from launcher.desktop_interaction_state import apply_widget_enabled_state
from launcher.desktop_product_details import build_product_detail_text, build_product_workspace_context_text
from launcher.desktop_profile_session_panel import refresh_profile_session_box
from launcher.desktop_report_panel import collect_report_column_titles, collect_report_columns, handle_report_columns_changed, refresh_report_columns, set_report_column_selection
from launcher.desktop_result_table import build_result_table
from launcher.desktop_state_readers import product_items
from launcher.desktop_result_table_widget import populate_result_table_widget, selected_product_ids_from_table, selected_row_product_ids_from_table, sync_product_select_all_checkbox
from launcher.desktop_selection_panel import (
    refresh_catalog_tree,
    refresh_category_list,
    sync_catalog_selection_from_widgets,
)
from launcher.desktop_shell_helpers import (
    build_window_icon,
    clear_filter_selections,
    current_combo_value,
    load_pyside6,
    set_category_selection,
    set_combo_value,
    set_result_selection,
    sync_setting_widgets,
)
from launcher.desktop_theme import apply_launcher_theme
from launcher.desktop_ui_text import WINDOW_TITLE
from launcher.desktop_view_helpers import build_product_workspace_summary_text, build_result_caption_text, build_status_text, build_summary_text
from launcher.desktop_workspace_shell import build_workspace_shell
from launcher.desktop_workspace_panel import refresh_workspace_box
class DesktopLauncherShell:
    """Desktop shell over the local launcher controller and task layer."""
    def __init__(self, *, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)
        self.controller = DesktopLauncherController(root_dir=self.root_dir)
        self.state = self.controller.state
        self._qtwidgets: Any | None = None
        self._qt: Any | None = None
        self.window: Any | None = None
        self.site_url_input: Any | None = None
        self.shop_combo: Any | None = None
        self.intent_combo: Any | None = None
        self.category_list: Any | None = None
        self.catalog_tree: Any | None = None
        self.headless_checkbox: Any | None = None
        self.manual_wait_checkbox: Any | None = None
        self.research_mode_combo: Any | None = None
        self.browser_runtime_combo: Any | None = None
        self.theme_combo: Any | None = None
        self.attempts_spin: Any | None = None
        self.listen_seconds_spin: Any | None = None
        self.status_label: Any | None = None
        self.summary_label: Any | None = None
        self.result_caption_label: Any | None = None
        self.result_workspace_summary_label: Any | None = None
        self.result_table: Any | None = None
        self.product_detail_text: Any | None = None
        self.profile_session_label: Any | None = None
        self.profile_session_combo: Any | None = None
        self.profile_session_versions_label: Any | None = None
        self.favorites_summary_label: Any | None = None
        self.favorites_list: Any | None = None
        self.workspace_label: Any | None = None
        self.workspace_journal_label: Any | None = None
        self.action_buttons: dict[str, Any] = {}
        self.filter_widgets: dict[str, Any] = {}
        self.filter_field_widgets: dict[str, Any] = {}
        self.filter_extra_widgets: list[Any] = []
        self.category_action_buttons: list[Any] = []
        self.filter_action_buttons: list[Any] = []
        self._refreshing_filter_widgets = False
        self._active_task_thread: Any | None = None
        self._active_task_worker: Any | None = None
    def run(self) -> int:
        """Run the launcher event loop."""
        app = self._create_application()
        assert self.window is not None
        self.window.show()
        return app.exec()
    def create_window(self) -> Any:
        """Build the launcher window without starting the full event loop."""
        self._create_application()
        return self.window
    def _create_application(self) -> Any:
        if self.window is not None:
            return load_pyside6()[0].instance()
        QApplication, qtwidgets, qt = load_pyside6()
        self._qtwidgets = qtwidgets
        self._qt = qt
        app = QApplication.instance() or QApplication([])
        icon = build_window_icon(self.root_dir)
        if icon is not None:
            app.setWindowIcon(icon)
        self.window = qtwidgets.QMainWindow()
        self.window.setWindowTitle(WINDOW_TITLE)
        if icon is not None:
            self.window.setWindowIcon(icon)
        self.window.resize(1200, 700)
        self.window.setCentralWidget(self._build_central_widget())
        apply_launcher_theme(self.window, self.state.settings.theme_mode)
        self._refresh_ui()
        return app
    def _build_central_widget(self) -> Any:
        qtwidgets = self._qtwidgets
        assert qtwidgets is not None
        return build_workspace_shell(self, qtwidgets)
    def _refresh_ui(self) -> None:
        if self.shop_combo is None or self.category_list is None:
            return
        set_combo_value(self.shop_combo, self.state.selection.shop)
        set_combo_value(self.intent_combo, self.state.selection.intent)
        refresh_category_list(self)
        refresh_catalog_tree(self)
        refresh_filter_widgets(self)
        refresh_report_columns(self)
        refresh_error_panel(self)
        refresh_command_strip(self)
        refresh_workspace_box(self)
        sync_setting_widgets(self)
        apply_launcher_theme(self.window, self.state.settings.theme_mode)
        set_combo_value(self.research_mode_combo, self.state.research.mode)
        if self.status_label is not None:
            self.status_label.setText(build_status_text(self.state))
        if self.summary_label is not None:
            self.summary_label.setText(build_summary_text(self.state))
        if self.result_caption_label is not None:
            self.result_caption_label.setText(build_result_caption_text(self.state))
        self._refresh_product_workspace_summary()
        apply_widget_enabled_state(self)
        self._refresh_action_buttons()
        self._refresh_result_table()
        refresh_profile_session_box(self)
        refresh_right_inspector(self)
        refresh_favorites_box(self)

    def _refresh_result_table(self) -> None:
        if self.result_table is None:
            return
        table = build_result_table(self.state)
        headers = table.get("headers")
        rows = table.get("rows")
        product_ids = table.get("product_ids")
        if isinstance(headers, list) and isinstance(rows, list):
            populate_result_table_widget(
                self.result_table,
                self._qtwidgets,
                self._qt,
                headers,
                rows,
                product_ids if isinstance(product_ids, list) else [],
                self.state.selection.selected_product_ids,
            )
            self._sync_selected_products_from_table()
            sync_product_select_all_checkbox(self.result_table, getattr(self, "result_select_all_checkbox", None), self._qt)
            self._refresh_product_workspace_summary()
            self._refresh_product_detail()

    def _update_state_from_widgets(self) -> None:
        sync_catalog_selection_from_widgets(self)
        self._sync_selected_products_from_table()
        self.state.report.selected_columns = collect_report_columns(self)
        self.state.report.column_titles = collect_report_column_titles(self)
        self.controller.set_filters(collect_filter_selections(self))
        self.controller.set_settings(
            {
                "headless": bool(self.headless_checkbox.isChecked()) if self.headless_checkbox is not None else True,
                "manual_wait": bool(self.manual_wait_checkbox.isChecked()) if self.manual_wait_checkbox is not None else False,
                "attempts": int(self.attempts_spin.value()) if self.attempts_spin is not None else 1,
                "listen_seconds": int(self.listen_seconds_spin.value()) if self.listen_seconds_spin is not None else 6,
                "browser_runtime": current_combo_value(self.browser_runtime_combo) or "camoufox",
                "theme_mode": str(self.theme_combo.currentData() or "dark") if self.theme_combo is not None else "dark",
            }
        )
        self.state.research.mode = current_combo_value(self.research_mode_combo) or self.state.research.mode

    def _refresh_action_buttons(self) -> None:
        for key, enabled in build_action_enabled_map(self.state).items():
            button = self.action_buttons.get(key)
            if button is not None:
                button.setEnabled(enabled)

    def _on_shop_changed(self, _: str) -> None:
        self.controller.set_selection(shop=current_combo_value(self.shop_combo))
        self._refresh_ui()
    def _on_intent_changed(self, _: str) -> None:
        self.controller.set_selection(intent=current_combo_value(self.intent_combo), categories=[])
        filters = {filter_name: [] for filter_name in FILTER_WIDGET_KEYS}
        filters["found_filters"] = {}
        self.controller.set_filters(filters)
        self._refresh_ui()
    def _on_select_all_categories(self) -> None: set_category_selection(self, True)
    def _on_clear_categories(self) -> None: set_category_selection(self, False)
    def _on_select_all_results(self) -> None: set_result_selection(self, True)
    def _on_clear_selected_products(self) -> None: set_result_selection(self, False)
    def _on_filter_changed(self, *_: Any) -> None: apply_filter_change(self)
    def _on_show_all_products(self) -> None:
        clear_filter_selections(self, FILTER_WIDGET_KEYS)
        self.state.task.message = f"Показаны все товары: {len(product_items(self.state))}."
        self._refresh_ui()
    def _on_clear_filters(self) -> None: clear_filter_selections(self, FILTER_WIDGET_KEYS)
    def _on_run_onboarding(self) -> None: self._run_ui_action(lambda: self.controller.run_onboarding_discovery(site_url=self._site_url()))
    def _on_prepare_cloak(self) -> None: self._run_ui_action(self.controller.run_cloak_runtime_install)
    def _on_run_export(self) -> None: self._run_ui_action(self.controller.run_selected_export)
    def _on_build_report(self) -> None: self._run_ui_action(self.controller.run_selected_report_export)
    def _on_report_columns_changed(self, *_: Any) -> None: handle_report_columns_changed(self)
    def _on_select_all_report_columns(self) -> None: set_report_column_selection(self, True)
    def _on_clear_report_columns(self) -> None: set_report_column_selection(self, False)
    def _on_save_settings(self) -> None:
        if self.category_list is not None:
            self._update_state_from_widgets()
        self.controller.save_settings()
        self._refresh_ui()
    def _on_open_excel(self) -> None: self._open_controller_action(self.controller.open_excel)
    def _on_open_report_dir(self) -> None: self._open_controller_action(self.controller.open_report_dir)
    def _on_result_selection_changed(self, *_: Any) -> None:
        self._sync_selected_products_from_table()
        sync_product_select_all_checkbox(self.result_table, getattr(self, "result_select_all_checkbox", None), self._qt)
        self._refresh_product_workspace_summary()
        self._refresh_product_detail()
        refresh_report_columns(self)
        self._refresh_action_buttons()
    def _on_catalog_tree_changed(self, _item: Any, _column: int) -> None:
        if self.catalog_tree is None or self._qt is None:
            return
        sync_catalog_selection_from_widgets(self)
        self._refresh_action_buttons()
    def _run_ui_action(self, action: Callable[[], Any]) -> None:
        if self.category_list is not None:
            self._update_state_from_widgets()
        if self._active_task_thread is not None:
            return
        self.state.task.status = "running"
        self.state.task.message = "Выполняется действие лаунчера..."
        self.state.task.last_error = ""
        self._refresh_ui()
        self._start_background_action(action)
    def _start_background_action(self, action: Callable[[], Any]) -> None:
        self._active_task_thread, self._active_task_worker = start_background_action(
            action=action,
            on_finished=self._on_background_action_finished,
            on_failed=self._on_background_action_failed,
            on_cleared=self._clear_background_action,
        )
    def _on_background_action_finished(self, _result: object) -> None:
        self._refresh_ui()
    def _on_background_action_failed(self, _error: object) -> None:
        self._refresh_ui()
    def _clear_background_action(self) -> None:
        thread = self._active_task_thread
        if thread is not None and thread.isRunning():
            thread.finished.connect(self._clear_background_action)
            return
        self._active_task_thread = None
        self._active_task_worker = None

    def _run_ui_action_sync_for_tests(self, action: Callable[[], Any]) -> None:
        try:
            action()
        except Exception:
            pass
        self._refresh_ui()

    def _open_controller_action(self, action: Callable[[], bool]) -> None:
        if self.category_list is not None:
            self._update_state_from_widgets()
        action()
        self._refresh_ui()

    def _site_url(self) -> str:
        return self.site_url_input.text().strip() if self.site_url_input is not None else ""

    def _sync_selected_products_from_table(self) -> None:
        if self.result_table is None or self._qt is None:
            return
        selected_product_ids = selected_product_ids_from_table(self.result_table, self._qt)
        self.controller.set_selection(selected_product_ids=selected_product_ids)

    def _refresh_product_detail(self) -> None:
        if self.product_detail_text is None:
            return
        detail_ids = selected_row_product_ids_from_table(self.result_table, self._qt) if self.result_table is not None and self._qt is not None else []
        self.product_detail_text.setPlainText(
            build_product_detail_text(
                self.state.result.json_path,
                detail_ids or self.state.selection.selected_product_ids,
                product_items(self.state),
                build_product_workspace_context_text(self.state),
            )
        )
        refresh_profile_session_box(self)

    def _refresh_product_workspace_summary(self) -> None:
        if self.result_workspace_summary_label is not None:
            self.result_workspace_summary_label.setText(build_product_workspace_summary_text(self.state))
