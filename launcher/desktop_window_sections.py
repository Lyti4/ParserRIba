"""Section builders for the desktop launcher window."""

from __future__ import annotations

from typing import Any

from launcher.desktop_result_table_widget import set_all_product_checks
from launcher.desktop_ui_text import BROWSER_RUNTIME_LABELS, RESEARCH_MODE_LABELS


def build_research_actions_box(shell: Any, qtwidgets: Any) -> Any:
    """Build compact research-stage action controls."""
    return _build_action_row_box(
        shell,
        qtwidgets,
        "Действия",
        (
            ("onboarding", "Исследование", shell._on_run_onboarding),
            ("save_settings", "Запомнить режим запуска", shell._on_save_settings),
        ),
    )


def build_catalog_actions_box(shell: Any, qtwidgets: Any) -> Any:
    """Build catalog-stage product collection controls."""
    return _build_action_row_box(
        shell,
        qtwidgets,
        "Сбор товаров",
        (("run_export", "Собрать товары по выбранным разделам", shell._on_run_export),),
    )


def build_report_box(shell: Any, qtwidgets: Any) -> Any:
    """Build report-stage controls."""
    return _build_action_row_box(
        shell,
        qtwidgets,
        "Отчёт",
        (
            ("build_report", "Собрать Excel", shell._on_build_report),
            ("open_excel", "Открыть Excel", shell._on_open_excel),
            ("open_folder", "Открыть папку", shell._on_open_report_dir),
        ),
    )


def build_settings_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the launcher settings section."""
    box = qtwidgets.QGroupBox("Настройки запуска")
    layout = qtwidgets.QGridLayout(box)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    shell.headless_checkbox = qtwidgets.QCheckBox("Скрыть браузер")
    shell.manual_wait_checkbox = qtwidgets.QCheckBox("Пауза для ручной проверки")
    shell.research_mode_combo = qtwidgets.QComboBox()
    shell.browser_runtime_combo = qtwidgets.QComboBox()
    shell.attempts_spin = qtwidgets.QSpinBox()
    shell.listen_seconds_spin = qtwidgets.QSpinBox()
    for value, label in RESEARCH_MODE_LABELS.items():
        shell.research_mode_combo.addItem(label, value)
    for value, label in BROWSER_RUNTIME_LABELS.items():
        shell.browser_runtime_combo.addItem(label, value)
    shell.research_mode_combo.setMinimumWidth(0)
    shell.browser_runtime_combo.setMinimumWidth(0)
    shell.research_mode_combo.setSizePolicy(
        qtwidgets.QSizePolicy.Policy.Ignored,
        qtwidgets.QSizePolicy.Policy.Fixed,
    )
    shell.browser_runtime_combo.setSizePolicy(
        qtwidgets.QSizePolicy.Policy.Ignored,
        qtwidgets.QSizePolicy.Policy.Fixed,
    )
    shell.attempts_spin.setRange(1, 3)
    shell.listen_seconds_spin.setRange(1, 180)
    shell.headless_checkbox.setToolTip("Обычно оставьте выключенным: браузер будет виден во время проверки сайта.")
    shell.manual_wait_checkbox.setToolTip("Оставьте включенным, если сайт может попросить ручную проверку.")
    shell.research_mode_combo.setToolTip("Режим запуска исследования сайта.")
    shell.browser_runtime_combo.setToolTip("Браузер для следующего исследования сайта.")
    attempts_label = qtwidgets.QLabel("Попытки")
    listen_seconds_label = qtwidgets.QLabel("Секунд ожидания")
    attempts_label.setVisible(False)
    listen_seconds_label.setVisible(False)
    shell.attempts_spin.setVisible(False)
    shell.listen_seconds_spin.setVisible(False)
    layout.addWidget(shell.headless_checkbox, 0, 0)
    layout.addWidget(shell.manual_wait_checkbox, 0, 1)
    layout.addWidget(qtwidgets.QLabel("Как исследовать сайт"), 1, 0)
    layout.addWidget(shell.research_mode_combo, 1, 1)
    layout.addWidget(qtwidgets.QLabel("Браузер"), 2, 0)
    layout.addWidget(shell.browser_runtime_combo, 2, 1)
    layout.addWidget(attempts_label, 3, 0)
    layout.addWidget(shell.attempts_spin, 3, 1)
    layout.addWidget(listen_seconds_label, 4, 0)
    layout.addWidget(shell.listen_seconds_spin, 4, 1)
    layout.setColumnStretch(1, 1)
    box.setMaximumHeight(124)
    return box


def build_status_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the launcher status section."""
    box = qtwidgets.QGroupBox("Статус")
    layout = qtwidgets.QVBoxLayout(box)
    shell.status_label = qtwidgets.QLabel("")
    shell.summary_label = qtwidgets.QLabel("")
    shell.status_label.setWordWrap(True)
    shell.summary_label.setWordWrap(True)
    layout.addWidget(shell.status_label)
    layout.addWidget(shell.summary_label)
    return box


def build_results_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the product/result table section."""
    box = qtwidgets.QGroupBox("Товары")
    layout = qtwidgets.QVBoxLayout(box)
    shell.result_caption_label = qtwidgets.QLabel("")
    shell.result_caption_label.setWordWrap(True)
    shell.result_table = qtwidgets.QTableWidget(0, 5)
    shell.result_table.setObjectName("launcherProductResultTable")
    shell.result_table.itemSelectionChanged.connect(shell._on_result_selection_changed)
    shell.result_table.itemChanged.connect(shell._on_result_selection_changed)
    shell.result_table.setHorizontalHeaderLabels(["Категория", "Товар", "Бренд", "Цена", "Наличие"])
    layout.addWidget(shell.result_caption_label)
    layout.addWidget(_build_product_table_splitter(shell, qtwidgets), stretch=1)
    return box


def _build_product_table_splitter(shell: Any, qtwidgets: Any) -> Any:
    """Build the product table workspace; details live in the route context."""
    table_host = qtwidgets.QWidget()
    table_host.setObjectName("launcherProductTableHost")
    table_layout = qtwidgets.QVBoxLayout(table_host)
    table_layout.setContentsMargins(0, 0, 0, 0)
    control_row = qtwidgets.QWidget()
    control_row.setObjectName("launcherProductWorkspaceControls")
    control_layout = qtwidgets.QGridLayout(control_row)
    control_layout.setContentsMargins(0, 0, 0, 0)
    control_layout.setHorizontalSpacing(8)
    shell.result_workspace_summary_label = qtwidgets.QLabel("")
    shell.result_workspace_summary_label.setObjectName("launcherProductWorkspaceSummary")
    shell.result_workspace_summary_label.setWordWrap(True)
    clear_button = qtwidgets.QPushButton("Снять выбор")
    clear_button.clicked.connect(shell._on_clear_selected_products)
    shell.action_buttons["clear_products"] = clear_button
    control_layout.addWidget(shell.result_workspace_summary_label, 0, 0)
    control_layout.addWidget(clear_button, 0, 1)
    control_layout.setColumnStretch(0, 1)
    table_layout.addWidget(control_row)
    shell.result_select_all_checkbox = qtwidgets.QCheckBox("Выбрать все показанные")
    shell.result_select_all_checkbox.stateChanged.connect(lambda state: _set_all_visible_products(shell, state))
    table_layout.addWidget(shell.result_select_all_checkbox)
    table_layout.addWidget(shell.result_table)
    return table_host

def _set_all_visible_products(shell: Any, _state: int) -> None:
    """Apply the master product checkbox to all visible table rows."""
    if shell.result_table is None or shell.result_select_all_checkbox is None or shell._qt is None:
        return
    checked = shell.result_select_all_checkbox.checkState() != shell._qt.CheckState.Unchecked
    set_all_product_checks(shell.result_table, shell._qt, checked)
    shell._on_result_selection_changed()


def _build_action_row_box(shell: Any, qtwidgets: Any, title: str, actions: tuple[tuple[str, str, Any], ...]) -> Any:
    """Build one compact stage action row."""
    box = qtwidgets.QGroupBox(title)
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.addWidget(_build_button_row(shell, qtwidgets, actions))
    box.setMaximumHeight(72)
    return box


def _build_button_row(shell: Any, qtwidgets: Any, actions: tuple[tuple[str, str, Any], ...]) -> Any:
    """Build one row of registered action buttons."""
    row = qtwidgets.QWidget()
    layout = qtwidgets.QGridLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(8)
    for index, (key, label, handler) in enumerate(actions):
        button = qtwidgets.QPushButton(label)
        button.clicked.connect(handler)
        shell.action_buttons[key] = button
        layout.addWidget(button, 0, index)
        layout.setColumnStretch(index, 1)
    return row
