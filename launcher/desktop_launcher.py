"""PySide6 desktop launcher shell for ParserRIba."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from launcher.desktop_action_state import build_action_enabled_map
from launcher.desktop_controller import DesktopLauncherController
from launcher.desktop_filter_panel import (
    FILTER_WIDGET_KEYS,
    build_filter_box,
    collect_filter_selections,
    refresh_filter_widgets,
)
from launcher.desktop_interaction_state import apply_widget_enabled_state
from launcher.desktop_result_table import build_result_table
from launcher.desktop_result_table_widget import populate_result_table_widget
from launcher.desktop_shell_helpers import (
    build_window_icon,
    clear_filter_selections,
    load_pyside6,
    set_category_selection,
    sync_setting_widgets,
)
from launcher.desktop_ui_text import INTENT_LABELS, SHOP_LABELS, WINDOW_TITLE
from launcher.desktop_view_helpers import build_result_caption_text, build_status_text, build_summary_text
from launcher.desktop_window_sections import (
    build_actions_box,
    build_results_box,
    build_settings_box,
    build_status_box,
)

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
        self.headless_checkbox: Any | None = None
        self.manual_wait_checkbox: Any | None = None
        self.research_mode_combo: Any | None = None
        self.attempts_spin: Any | None = None
        self.listen_seconds_spin: Any | None = None
        self.status_label: Any | None = None
        self.summary_label: Any | None = None
        self.result_caption_label: Any | None = None
        self.result_table: Any | None = None
        self.action_buttons: dict[str, Any] = {}
        self.filter_widgets: dict[str, Any] = {}
        self.filter_field_widgets: dict[str, Any] = {}
        self.filter_extra_widgets: list[Any] = []
        self.category_action_buttons: list[Any] = []
        self.filter_action_buttons: list[Any] = []
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
        self.window.resize(1320, 765)
        self.window.setCentralWidget(self._build_central_widget())
        self._refresh_ui()
        return app

    def _build_central_widget(self) -> Any:
        qtwidgets = self._qtwidgets
        assert qtwidgets is not None
        container = qtwidgets.QWidget()
        layout = qtwidgets.QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        controls_widget = qtwidgets.QWidget()
        controls_layout = qtwidgets.QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)
        controls_layout.addWidget(self._build_selection_box(qtwidgets))
        for builder in (build_filter_box, build_actions_box, build_settings_box, build_status_box):
            controls_layout.addWidget(builder(self, qtwidgets))
        controls_scroll = qtwidgets.QScrollArea()
        controls_scroll.setObjectName("launcherControlsScrollArea")
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(load_pyside6()[2].ScrollBarAlwaysOff)
        controls_scroll.setFrameShape(qtwidgets.QFrame.Shape.NoFrame)
        controls_scroll.setWidget(controls_widget)
        layout.addWidget(controls_scroll, stretch=0)
        layout.addWidget(build_results_box(self, qtwidgets), stretch=1)
        return container

    def _build_selection_box(self, qtwidgets: Any) -> Any:
        box = qtwidgets.QGroupBox("Выбор")
        layout = qtwidgets.QGridLayout(box)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        layout.addWidget(qtwidgets.QLabel("URL сайта"), 0, 0)
        self.site_url_input = qtwidgets.QLineEdit("https://5ka.ru")
        layout.addWidget(self.site_url_input, 0, 1, 1, 3)
        layout.addWidget(qtwidgets.QLabel("Магазин"), 1, 0)
        self.shop_combo = qtwidgets.QComboBox()
        for value, label in SHOP_LABELS.items():
            self.shop_combo.addItem(label, value)
        self.shop_combo.currentTextChanged.connect(self._on_shop_changed)
        layout.addWidget(self.shop_combo, 1, 1)
        layout.addWidget(qtwidgets.QLabel("Раздел"), 1, 2)
        self.intent_combo = qtwidgets.QComboBox()
        for value, label in INTENT_LABELS.items():
            self.intent_combo.addItem(label, value)
        self.intent_combo.currentTextChanged.connect(self._on_intent_changed)
        layout.addWidget(self.intent_combo, 1, 3)
        layout.addWidget(qtwidgets.QLabel("Категории"), 2, 0)
        self.category_list = qtwidgets.QListWidget()
        self.category_list.setSelectionMode(qtwidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self.category_list.setMinimumHeight(86)
        self.category_list.setMaximumHeight(100)
        layout.addWidget(self.category_list, 2, 1, 1, 3)
        button_grid = qtwidgets.QGridLayout()
        button_grid.setContentsMargins(0, 0, 0, 0)
        button_grid.setHorizontalSpacing(8)
        for index, (label, handler) in enumerate(
            (
                ("Выбрать все категории", self._on_select_all_categories),
                ("Очистить категории", self._on_clear_categories),
            )
        ):
            button = qtwidgets.QPushButton(label)
            button.clicked.connect(handler)
            self.category_action_buttons.append(button)
            button_grid.addWidget(button, 0, index)
        layout.addLayout(button_grid, 3, 1, 1, 3)
        return box

    def _refresh_ui(self) -> None:
        if self.shop_combo is None or self.intent_combo is None or self.category_list is None:
            return
        self._set_combo_value(self.shop_combo, self.state.selection.shop)
        self._set_combo_value(self.intent_combo, self.state.selection.intent)
        self._refresh_category_list()
        refresh_filter_widgets(self)
        sync_setting_widgets(self)
        self._set_combo_value(self.research_mode_combo, self.state.research.mode)
        if self.status_label is not None:
            self.status_label.setText(build_status_text(self.state))
        if self.summary_label is not None:
            self.summary_label.setText(build_summary_text(self.state))
        if self.result_caption_label is not None:
            self.result_caption_label.setText(build_result_caption_text(self.state))
        apply_widget_enabled_state(self)
        self._refresh_action_buttons()
        self._refresh_result_table()

    def _refresh_category_list(self) -> None:
        assert self.category_list is not None
        self.category_list.clear()
        selected = set(self.state.selection.categories)
        for category_name in self.controller.list_available_categories():
            item = self._qtwidgets.QListWidgetItem(category_name)
            self.category_list.addItem(item)
            item.setSelected(category_name in selected)

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

    def _update_state_from_widgets(self) -> None:
        assert self.category_list is not None
        self.controller.set_selection(categories=[item.text() for item in self.category_list.selectedItems()])
        self._sync_selected_products_from_table()
        self.controller.set_filters(collect_filter_selections(self))
        self.controller.set_settings(
            {
                "headless": bool(self.headless_checkbox.isChecked()) if self.headless_checkbox is not None else True,
                "manual_wait": bool(self.manual_wait_checkbox.isChecked()) if self.manual_wait_checkbox is not None else False,
                "attempts": int(self.attempts_spin.value()) if self.attempts_spin is not None else 1,
                "listen_seconds": int(self.listen_seconds_spin.value()) if self.listen_seconds_spin is not None else 6,
            }
        )
        self.state.research.mode = self._current_combo_value(self.research_mode_combo) or self.state.research.mode

    def _refresh_action_buttons(self) -> None:
        for key, enabled in build_action_enabled_map(self.state).items():
            button = self.action_buttons.get(key)
            if button is not None:
                button.setEnabled(enabled)

    def _on_shop_changed(self, _: str) -> None:
        self.controller.set_selection(shop=self._current_combo_value(self.shop_combo))
        self._refresh_ui()

    def _on_intent_changed(self, _: str) -> None:
        self.controller.set_selection(intent=self._current_combo_value(self.intent_combo), categories=[])
        self.controller.set_filters({filter_name: [] for filter_name in FILTER_WIDGET_KEYS})
        self._refresh_ui()

    def _on_select_all_categories(self) -> None: set_category_selection(self, True)
    def _on_clear_categories(self) -> None: set_category_selection(self, False)
    def _on_clear_filters(self) -> None: clear_filter_selections(self, FILTER_WIDGET_KEYS)
    def _on_run_onboarding(self) -> None: self._run_ui_action(lambda: self.controller.run_onboarding_discovery(site_url=self._site_url()))
    def _on_run_export(self) -> None: self._run_ui_action(self.controller.run_selected_export)
    def _on_load_filters(self) -> None: self._run_ui_action(self.controller.load_filter_options)
    def _on_build_report(self) -> None: self._run_ui_action(self.controller.run_selected_report_export)

    def _on_save_settings(self) -> None:
        if self.category_list is not None:
            self._update_state_from_widgets()
        self.controller.save_settings()
        self._refresh_ui()

    def _on_open_excel(self) -> None: self._open_controller_action(self.controller.open_excel)
    def _on_open_report_dir(self) -> None: self._open_controller_action(self.controller.open_report_dir)
    def _on_open_json(self) -> None: self._open_controller_action(self.controller.open_json)
    def _on_result_selection_changed(self) -> None: self._sync_selected_products_from_table()

    def _run_ui_action(self, action: Callable[[], Any]) -> None:
        if self.category_list is not None:
            self._update_state_from_widgets()
        self.state.task.status = "running"
        self.state.task.message = "Выполняется действие лаунчера..."
        self._refresh_ui()
        app = load_pyside6()[0].instance()
        if app is not None:
            app.processEvents()
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
        return (self.site_url_input.text().strip() if self.site_url_input is not None else "") or "https://5ka.ru"

    def _sync_selected_products_from_table(self) -> None:
        if self.result_table is None or self._qt is None:
            return
        selected_product_ids: list[str] = []
        for item in self.result_table.selectedItems():
            product_id = str(item.data(self._qt.ItemDataRole.UserRole) or "").strip()
            if product_id and product_id not in selected_product_ids:
                selected_product_ids.append(product_id)
        self.controller.set_selection(selected_product_ids=selected_product_ids)

    @staticmethod
    def _current_combo_value(combo: Any) -> str:
        return str(combo.currentData() if combo is not None else "")

    @staticmethod
    def _set_combo_value(combo: Any, value: str) -> None:
        if combo is None:
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
