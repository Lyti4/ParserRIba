"""Section builders for the desktop launcher window."""

from __future__ import annotations

from typing import Any

from launcher.desktop_ui_text import RESEARCH_MODE_LABELS


def build_research_actions_box(shell: Any, qtwidgets: Any) -> Any:
    """Build compact research-stage action controls."""
    return _build_action_row_box(
        shell,
        qtwidgets,
        "Действия",
        (
            ("onboarding", "Исследование", shell._on_run_onboarding),
            ("save_settings", "Сохранить настройки", shell._on_save_settings),
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


def build_filter_actions_box(shell: Any, qtwidgets: Any) -> Any:
    """Build filter-stage loading controls."""
    return _build_action_row_box(
        shell,
        qtwidgets,
        "Фильтры",
        (("load_filters", "Обновить фильтры из товаров", shell._on_load_filters),),
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
    box = qtwidgets.QGroupBox("Настройки")
    layout = qtwidgets.QGridLayout(box)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    shell.headless_checkbox = qtwidgets.QCheckBox("Headless режим")
    shell.manual_wait_checkbox = qtwidgets.QCheckBox("Ручное ожидание")
    shell.research_mode_combo = qtwidgets.QComboBox()
    shell.attempts_spin = qtwidgets.QSpinBox()
    shell.listen_seconds_spin = qtwidgets.QSpinBox()
    for value, label in RESEARCH_MODE_LABELS.items():
        shell.research_mode_combo.addItem(label, value)
    shell.attempts_spin.setRange(1, 3)
    shell.listen_seconds_spin.setRange(1, 180)
    layout.addWidget(shell.headless_checkbox, 0, 0)
    layout.addWidget(shell.manual_wait_checkbox, 0, 1)
    layout.addWidget(qtwidgets.QLabel("Режим исследования"), 0, 2)
    layout.addWidget(shell.research_mode_combo, 0, 3)
    layout.addWidget(qtwidgets.QLabel("Попытки"), 1, 0)
    layout.addWidget(shell.attempts_spin, 1, 1)
    layout.addWidget(qtwidgets.QLabel("Секунд ожидания"), 1, 2)
    layout.addWidget(shell.listen_seconds_spin, 1, 3)
    layout.setColumnStretch(4, 1)
    box.setMaximumHeight(96)
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
    shell.result_table.itemSelectionChanged.connect(shell._on_result_selection_changed)
    shell.result_table.setHorizontalHeaderLabels(["Категория", "Товар", "Бренд", "Цена", "Наличие"])
    shell.product_detail_text = qtwidgets.QTextEdit()
    shell.product_detail_text.setReadOnly(True)
    shell.product_detail_text.setMinimumHeight(140)
    layout.addWidget(shell.result_caption_label)
    layout.addWidget(shell.result_table)
    layout.addWidget(shell.product_detail_text)
    layout.addWidget(
        _build_button_row(
            shell,
            qtwidgets,
            (
                ("select_products", "Выбрать показанные", shell._on_select_all_results),
                ("clear_products", "Снять выбор", shell._on_clear_selected_products),
            ),
        )
    )
    return box


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
