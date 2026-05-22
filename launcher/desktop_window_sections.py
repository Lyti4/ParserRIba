"""Section builders for the desktop launcher window."""

from __future__ import annotations

from typing import Any

from launcher.desktop_ui_text import RESEARCH_MODE_LABELS


def build_actions_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the main launcher actions section."""
    box = qtwidgets.QGroupBox("Действия")
    layout = qtwidgets.QGridLayout(box)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setHorizontalSpacing(8)
    layout.setVerticalSpacing(6)
    actions = (
        ("onboarding", "Исследование", shell._on_run_onboarding, 0),
        ("run_export", "Запустить выгрузку", shell._on_run_export, 1),
        ("load_filters", "Загрузить фильтры", shell._on_load_filters, 2),
        ("build_report", "Собрать Excel", shell._on_build_report, 3),
        ("save_settings", "Сохранить настройки", shell._on_save_settings, 4),
    )
    for key, label, handler, column in actions:
        button = qtwidgets.QPushButton(label)
        button.clicked.connect(handler)
        shell.action_buttons[key] = button
        layout.addWidget(button, 0, column)
    for column in range(5):
        layout.setColumnStretch(column, 1)
    return box


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
    return box


def build_status_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the launcher status section."""
    box = qtwidgets.QGroupBox("Статус")
    layout = qtwidgets.QVBoxLayout(box)
    shell.status_label = qtwidgets.QLabel("")
    shell.summary_label = qtwidgets.QLabel("")
    shell.status_label.setWordWrap(True)
    shell.summary_label.setWordWrap(True)
    box.setMaximumHeight(170)
    layout.addWidget(shell.status_label)
    layout.addWidget(shell.summary_label)
    return box


def build_results_box(shell: Any, qtwidgets: Any) -> Any:
    """Build the launcher results section."""
    box = qtwidgets.QGroupBox("Результаты")
    layout = qtwidgets.QVBoxLayout(box)
    shell.result_caption_label = qtwidgets.QLabel("")
    shell.result_caption_label.setWordWrap(True)
    shell.result_table = qtwidgets.QTableWidget(0, 5)
    shell.result_table.itemSelectionChanged.connect(shell._on_result_selection_changed)
    shell.result_table.setHorizontalHeaderLabels(["Категория", "Товар", "Бренд", "Цена", "Наличие"])
    layout.addWidget(shell.result_caption_label)
    layout.addWidget(shell.result_table)
    button_grid = qtwidgets.QGridLayout()
    button_grid.setContentsMargins(0, 0, 0, 0)
    button_grid.setHorizontalSpacing(8)
    for index, (key, label, handler) in enumerate(
        (
            ("open_excel", "Открыть Excel", shell._on_open_excel),
            ("open_folder", "Открыть папку", shell._on_open_report_dir),
            ("open_json", "Открыть JSON", shell._on_open_json),
        )
    ):
        button = qtwidgets.QPushButton(label)
        button.clicked.connect(handler)
        shell.action_buttons[key] = button
        button_grid.addWidget(button, 0, index)
    for column in range(3):
        button_grid.setColumnStretch(column, 1)
    layout.addLayout(button_grid)
    return box
