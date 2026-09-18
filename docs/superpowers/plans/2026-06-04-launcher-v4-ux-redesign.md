# Launcher V4 UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modern, scalable ParserRIba launcher shell with a restrained archive/counterintelligence visual language, no symbols, clearer workflow navigation and first-class diagnostics.

**Architecture:** Keep the existing Launcher V3 controller/task/data contracts. Add V4 UI structure through focused PySide6 modules: theme tokens, navigation rail, command strip, diagnostics workspace and workspace containers. Do not grow `launcher/desktop_launcher.py`; it should only orchestrate module-level helpers.

**Tech Stack:** Python 3.11, PySide6, pytest, existing `LauncherAppState`, existing `DesktopLauncherController`, local-first Windows desktop runtime.

---

## Source Design Documents

- `docs/design/LAUNCHER_V4_DESIGN_BRIEF.md`
- `docs/TARGET_ARCHITECTURE.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/DATA_FLOW_THREADING_PLAN.md`

## File Structure

Create:
- `launcher/desktop_theme.py` - design tokens and application QSS for the V4 visual system.
- `launcher/desktop_navigation.py` - left workflow navigation rail and state badges.
- `launcher/desktop_command_strip.py` - top task/workspace status strip.
- `launcher/desktop_diagnostics_panel.py` - richer diagnostics workspace with copy actions.
- `launcher/desktop_workspace_shell.py` - three-zone layout builder that composes navigation, command strip, workspace stack and inspector.
- `tests/test_desktop_theme.py` - pure tests for color tokens and QSS content.
- `tests/test_desktop_navigation.py` - UI tests for navigation labels and state mapping.
- `tests/test_desktop_command_strip.py` - pure/UI tests for current workspace summary text.
- `tests/test_desktop_diagnostics_panel.py` - tests for copyable diagnostics content and masked secrets.
- `tests/test_desktop_workspace_shell.py` - smoke tests for V4 shell composition.

Modify:
- `launcher/desktop_launcher.py` - minimal call into `build_workspace_shell()` and `apply_launcher_theme()`.
- `launcher/desktop_workflow_tabs.py` - keep as legacy-compatible workspace builder during migration, or wrap existing tabs inside V4 main workspace for first slice.
- `launcher/desktop_error_panel.py` - reuse formatting logic or delegate to `desktop_diagnostics_panel.py`.
- `launcher/desktop_ui_text.py` - add V4 Russian labels only if shared.
- `tests/test_desktop_launcher.py` - update shell-level expectations after V4 shell is enabled.

Do not modify:
- task runners;
- store adapters;
- product extraction;
- report generation;
- browser/proxy runtime, except for displaying existing state.

## Rollout Strategy

Use a feature flag constant first:

```python
LAUNCHER_V4_SHELL_ENABLED = True
```

If risk appears during implementation, keep the old workflow tabs behind the same builder and migrate visual shell without changing controller behavior.

## Task 1: Add Theme Tokens And QSS

**Files:**
- Create: `launcher/desktop_theme.py`
- Test: `tests/test_desktop_theme.py`

- [ ] **Step 1: Write the failing tests**

```python
from launcher.desktop_theme import ARCHIVE_THEME, build_launcher_qss


def test_archive_theme_exposes_required_tokens() -> None:
    assert ARCHIVE_THEME["archive.bg"] == "#11160F"
    assert ARCHIVE_THEME["archive.paper"] == "#EEE6D2"
    assert ARCHIVE_THEME["archive.brass"] == "#B08A45"
    assert ARCHIVE_THEME["archive.redPencil"] == "#9D2E2E"


def test_launcher_qss_contains_core_widgets_without_symbols() -> None:
    qss = build_launcher_qss()

    assert "QMainWindow" in qss
    assert "QTableWidget" in qss
    assert "#launcherNavigationRail" in qss
    assert "#launcherDiagnosticsText" in qss
    assert "☭" not in qss
    assert "★" not in qss
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_theme.py
```

Expected: import failure for `launcher.desktop_theme`.

- [ ] **Step 3: Implement theme module**

Create `launcher/desktop_theme.py`:

```python
"""Launcher V4 visual theme tokens and QSS."""

from __future__ import annotations

from typing import Any

ARCHIVE_THEME = {
    "archive.bg": "#11160F",
    "archive.surface": "#192119",
    "archive.surfaceRaised": "#222B21",
    "archive.paper": "#EEE6D2",
    "archive.paperMuted": "#D7CCB4",
    "archive.ink": "#14120E",
    "archive.text": "#ECE7DA",
    "archive.textMuted": "#AFA58F",
    "archive.brass": "#B08A45",
    "archive.green": "#2F4B36",
    "archive.redPencil": "#9D2E2E",
    "archive.border": "#3B4638",
    "archive.grid": "#C8BFA9",
}


def build_launcher_qss() -> str:
    """Return application stylesheet for the V4 launcher shell."""
    t = ARCHIVE_THEME
    return f"""
QMainWindow, QWidget {{
    background: {t["archive.bg"]};
    color: {t["archive.text"]};
    font-family: "Segoe UI";
    font-size: 10pt;
}}
QGroupBox {{
    border: 1px solid {t["archive.border"]};
    border-radius: 6px;
    margin-top: 12px;
    padding: 8px;
    background: {t["archive.surface"]};
}}
QGroupBox::title {{
    color: {t["archive.brass"]};
    padding: 0 4px;
}}
QLineEdit, QSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {t["archive.paper"]};
    color: {t["archive.ink"]};
    border: 1px solid {t["archive.grid"]};
    border-radius: 4px;
    padding: 4px;
}}
QPushButton {{
    background: {t["archive.surfaceRaised"]};
    color: {t["archive.text"]};
    border: 1px solid {t["archive.border"]};
    border-radius: 4px;
    padding: 6px 10px;
}}
QPushButton:hover {{
    border-color: {t["archive.brass"]};
}}
QPushButton:disabled {{
    color: {t["archive.textMuted"]};
}}
QTableWidget {{
    background: {t["archive.paper"]};
    color: {t["archive.ink"]};
    gridline-color: {t["archive.grid"]};
    selection-background-color: {t["archive.green"]};
    selection-color: {t["archive.text"]};
}}
#launcherNavigationRail {{
    background: {t["archive.surface"]};
    border-right: 1px solid {t["archive.border"]};
}}
#launcherDiagnosticsText {{
    font-family: "Consolas";
    background: {t["archive.paper"]};
    color: {t["archive.ink"]};
}}
"""


def apply_launcher_theme(window: Any) -> None:
    """Apply the launcher V4 stylesheet to a Qt window."""
    if window is not None:
        window.setStyleSheet(build_launcher_qss())
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_theme.py
```

Expected: pass.

## Task 2: Build Navigation Rail

**Files:**
- Create: `launcher/desktop_navigation.py`
- Test: `tests/test_desktop_navigation.py`

- [ ] **Step 1: Write the failing tests**

```python
from launcher.desktop_navigation import NAV_ITEMS, navigation_state_for_tab


def test_navigation_items_match_launcher_v4_flow() -> None:
    assert [item.key for item in NAV_ITEMS] == [
        "research",
        "catalog",
        "products",
        "report",
        "profile",
        "diagnostics",
        "proxy",
        "price_history",
        "scheduler",
        "stores",
    ]
    assert NAV_ITEMS[0].label == "Исследование"
    assert NAV_ITEMS[7].enabled is False


def test_navigation_state_for_tab_marks_active_item() -> None:
    states = navigation_state_for_tab("products")

    assert states["products"] == "active"
    assert states["research"] in {"idle", "completed"}
    assert states["price_history"] == "disabled"
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_navigation.py
```

Expected: import failure for `launcher.desktop_navigation`.

- [ ] **Step 3: Implement data model and pure state helper**

Create `launcher/desktop_navigation.py`:

```python
"""Launcher V4 navigation rail."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NavigationItem:
    key: str
    label: str
    enabled: bool = True


NAV_ITEMS = (
    NavigationItem("research", "Исследование"),
    NavigationItem("catalog", "Каталог"),
    NavigationItem("products", "Товары"),
    NavigationItem("report", "Отчёт"),
    NavigationItem("profile", "Профиль"),
    NavigationItem("diagnostics", "Диагностика"),
    NavigationItem("proxy", "Прокси"),
    NavigationItem("price_history", "История цен", enabled=False),
    NavigationItem("scheduler", "Планировщик", enabled=False),
    NavigationItem("stores", "Магазины", enabled=False),
)


def navigation_state_for_tab(active_key: str) -> dict[str, str]:
    """Return visual state for every navigation item."""
    states: dict[str, str] = {}
    for item in NAV_ITEMS:
        if not item.enabled:
            states[item.key] = "disabled"
        elif item.key == active_key:
            states[item.key] = "active"
        else:
            states[item.key] = "idle"
    return states


def build_navigation_rail(shell: Any, qtwidgets: Any) -> Any:
    """Build the left V4 navigation rail."""
    rail = qtwidgets.QFrame()
    rail.setObjectName("launcherNavigationRail")
    rail.setMinimumWidth(190)
    rail.setMaximumWidth(220)
    layout = qtwidgets.QVBoxLayout(rail)
    layout.setContentsMargins(10, 12, 10, 12)
    layout.setSpacing(6)
    title = qtwidgets.QLabel("ParserRIba")
    title.setObjectName("launcherNavigationTitle")
    layout.addWidget(title)
    shell.navigation_buttons = {}
    for item in NAV_ITEMS:
        button = qtwidgets.QPushButton(item.label)
        button.setObjectName(f"launcherNavigation_{item.key}")
        button.setEnabled(item.enabled)
        button.setCheckable(item.enabled)
        shell.navigation_buttons[item.key] = button
        layout.addWidget(button)
    layout.addStretch(1)
    return rail
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_navigation.py
```

Expected: pass.

## Task 3: Add Command Strip Text Builder

**Files:**
- Create: `launcher/desktop_command_strip.py`
- Test: `tests/test_desktop_command_strip.py`

- [ ] **Step 1: Write the failing tests**

```python
from launcher.desktop_command_strip import build_command_strip_text
from models.launcher_state import LauncherAppState


def test_command_strip_text_summarizes_current_workspace() -> None:
    state = LauncherAppState()
    state.profile.profile_id = "pyaterochka:https---5ka-ru"
    state.task.task_name = "pyaterochka_catalog_export"
    state.task.status = "running"
    state.task.progress_current = 2
    state.task.progress_total = 4
    state.products.products_count = 60
    state.selection.selected_product_ids = ["1", "2"]

    text = build_command_strip_text(state)

    assert "Профиль: pyaterochka:https---5ka-ru" in text
    assert "Статус: running" in text
    assert "Прогресс: 2/4" in text
    assert "Товары: 60" in text
    assert "Выбрано: 2" in text
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_command_strip.py
```

Expected: import failure for `launcher.desktop_command_strip`.

- [ ] **Step 3: Implement command strip module**

Create `launcher/desktop_command_strip.py`:

```python
"""Launcher V4 top command strip."""

from __future__ import annotations

from typing import Any

from models.launcher_state import LauncherAppState


def build_command_strip_text(state: LauncherAppState) -> str:
    """Build one compact current-workspace status line."""
    profile = state.profile.profile_id or state.profile.display_name or "-"
    progress = f"{state.task.progress_current}/{state.task.progress_total}" if state.task.progress_total else "-"
    return (
        f"Профиль: {profile} | "
        f"Статус: {state.task.status} | "
        f"Прогресс: {progress} | "
        f"Товары: {state.products.products_count} | "
        f"Выбрано: {len(state.selection.selected_product_ids)}"
    )


def build_command_strip(shell: Any, qtwidgets: Any) -> Any:
    """Build the top V4 command strip."""
    host = qtwidgets.QFrame()
    host.setObjectName("launcherCommandStrip")
    layout = qtwidgets.QHBoxLayout(host)
    layout.setContentsMargins(10, 8, 10, 8)
    shell.command_strip_label = qtwidgets.QLabel(build_command_strip_text(shell.state))
    shell.command_strip_label.setWordWrap(True)
    layout.addWidget(shell.command_strip_label, stretch=1)
    return host


def refresh_command_strip(shell: Any) -> None:
    """Refresh command strip from current launcher state."""
    label = getattr(shell, "command_strip_label", None)
    if label is not None:
        label.setText(build_command_strip_text(shell.state))
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_command_strip.py
```

Expected: pass.

## Task 4: Build Diagnostics Workspace

**Files:**
- Create: `launcher/desktop_diagnostics_panel.py`
- Modify: `launcher/desktop_error_panel.py`
- Test: `tests/test_desktop_diagnostics_panel.py`

- [ ] **Step 1: Write the failing tests**

```python
from launcher.desktop_diagnostics_panel import build_diagnostics_text, mask_sensitive_text
from models.launcher_state import LauncherAppState


def test_mask_sensitive_text_hides_proxy_password() -> None:
    value = "http://user_abc:secret_password@res.lteboost.com:1000"

    assert mask_sensitive_text(value) == "http://user_abc:***@res.lteboost.com:1000"


def test_diagnostics_text_includes_next_step_for_captcha() -> None:
    state = LauncherAppState()
    state.task.status = "failed"
    state.task.last_error = "pyaterochka_rotate_image_captcha"
    state.task.message = "Сбор остановлен защитой сайта."

    text = build_diagnostics_text(state)

    assert "Последняя ошибка: pyaterochka_rotate_image_captcha" in text
    assert "Что делать: откройте браузер, решите капчу вручную и повторите сбор." in text
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_diagnostics_panel.py
```

Expected: import failure for `launcher.desktop_diagnostics_panel`.

- [ ] **Step 3: Implement diagnostics module**

Create `launcher/desktop_diagnostics_panel.py`:

```python
"""Launcher V4 diagnostics workspace."""

from __future__ import annotations

import re
from typing import Any

from launcher.desktop_error_panel import build_error_log_text
from models.launcher_state import LauncherAppState

_CREDENTIAL_RE = re.compile(r"(https?://[^:/\\s]+:)([^@\\s]+)(@)")


def mask_sensitive_text(value: str) -> str:
    """Mask proxy passwords and tokens in copyable diagnostics."""
    return _CREDENTIAL_RE.sub(r"\1***\3", str(value or ""))


def build_diagnostics_text(state: LauncherAppState) -> str:
    """Build copyable diagnostics with a user-facing next step."""
    text = build_error_log_text(state)
    hint = _next_step_hint(state.task.last_error)
    if hint:
        text = f"{text}\nЧто делать: {hint}"
    return mask_sensitive_text(text)


def _next_step_hint(last_error: str) -> str:
    normalized = str(last_error or "").casefold()
    if "captcha" in normalized:
        return "откройте браузер, решите капчу вручную и повторите сбор."
    if "proxy" in normalized or "timed out" in normalized:
        return "проверьте российский proxy, баланс, протокол и доступность endpoint."
    if "403" in normalized:
        return "проверьте профиль браузера, proxy и не запускайте частые повторные запросы подряд."
    return ""


def build_diagnostics_box(shell: Any, qtwidgets: Any) -> Any:
    """Build a copyable diagnostics workspace."""
    box = qtwidgets.QGroupBox("Диагностика")
    layout = qtwidgets.QVBoxLayout(box)
    shell.diagnostics_text = qtwidgets.QPlainTextEdit()
    shell.diagnostics_text.setObjectName("launcherDiagnosticsText")
    shell.diagnostics_text.setReadOnly(True)
    shell.diagnostics_text.setPlainText(build_diagnostics_text(shell.state))
    layout.addWidget(shell.diagnostics_text, stretch=1)
    return box
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_diagnostics_panel.py
```

Expected: pass.

## Task 5: Compose V4 Workspace Shell

**Files:**
- Create: `launcher/desktop_workspace_shell.py`
- Modify: `launcher/desktop_launcher.py`
- Test: `tests/test_desktop_workspace_shell.py`, `tests/test_desktop_launcher.py`

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path

from launcher.desktop_launcher import DesktopLauncherShell


def test_launcher_v4_shell_has_navigation_and_command_strip(tmp_path: Path) -> None:
    shell = DesktopLauncherShell(root_dir=tmp_path)
    window = shell.create_window()

    assert window.findChild(shell._qtwidgets.QFrame, "launcherNavigationRail") is not None
    assert window.findChild(shell._qtwidgets.QFrame, "launcherCommandStrip") is not None
    assert hasattr(shell, "navigation_buttons")
    assert shell.navigation_buttons["products"].text() == "Товары"
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_workspace_shell.py
```

Expected: no V4 rail/command strip.

- [ ] **Step 3: Implement shell composition**

Create `launcher/desktop_workspace_shell.py`:

```python
"""Launcher V4 workspace shell composition."""

from __future__ import annotations

from typing import Any

from launcher.desktop_command_strip import build_command_strip
from launcher.desktop_navigation import build_navigation_rail
from launcher.desktop_workflow_tabs import build_workflow_tabs


def build_workspace_shell(shell: Any, qtwidgets: Any) -> Any:
    """Build three-zone V4 launcher shell around existing workspaces."""
    container = qtwidgets.QWidget()
    root = qtwidgets.QHBoxLayout(container)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(build_navigation_rail(shell, qtwidgets), stretch=0)

    main = qtwidgets.QWidget()
    main_layout = qtwidgets.QVBoxLayout(main)
    main_layout.setContentsMargins(10, 10, 10, 10)
    main_layout.setSpacing(8)
    main_layout.addWidget(build_command_strip(shell, qtwidgets), stretch=0)
    main_layout.addWidget(build_workflow_tabs(shell, qtwidgets), stretch=1)
    root.addWidget(main, stretch=1)
    return container
```

Modify `launcher/desktop_launcher.py` minimally:

```python
from launcher.desktop_theme import apply_launcher_theme
from launcher.desktop_workspace_shell import build_workspace_shell

# in _create_application(), after setCentralWidget:
apply_launcher_theme(self.window)

# in _build_central_widget():
return build_workspace_shell(self, qtwidgets)
```

- [ ] **Step 4: Run the tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_workspace_shell.py tests\test_desktop_launcher.py
```

Expected: pass.

## Task 6: Preserve Existing Product Workflow

**Files:**
- Modify: only files touched in Tasks 1-5 if tests reveal a regression.
- Test: existing focused workflow tests.

- [ ] **Step 1: Run focused launcher workflow tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_desktop_launcher.py tests\test_desktop_result_table.py tests\test_desktop_filter_panel.py tests\test_desktop_product_export_live_state.py tests\test_desktop_error_panel.py tests\test_desktop_workflow_error_tab.py
```

Expected: pass.

- [ ] **Step 2: If a test fails, fix only the V4 shell boundary**

Allowed fixes:
- object names missing from new widgets;
- labels not refreshed;
- stylesheet applied too early;
- navigation buttons not initialized.

Not allowed in this task:
- changing product extraction;
- changing report output;
- changing proxy runtime.

## Task 7: Full Validation Gate

**Files:**
- No code changes unless validation finds a bug.

- [ ] **Step 1: Run full tests**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass or existing skips only.

- [ ] **Step 2: Compile**

```powershell
.\.venv\Scripts\python.exe -m compileall -q models utils scripts tests stores launcher
```

Expected: exit code 0.

- [ ] **Step 3: Architecture check**

```powershell
.\.venv\Scripts\python.exe scripts\architecture_check.py
```

Expected: exit code 0. Existing warning for `tests/test_desktop_filter_panel.py` may remain until a separate test-split slice.

- [ ] **Step 4: Launcher smoke**

```powershell
.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py --smoke
```

Expected: `Desktop launcher smoke passed.`

## Acceptance Checklist

- [ ] Launcher opens with dark archive theme.
- [ ] No Soviet symbols or direct state/military insignia are present.
- [ ] Left navigation rail shows current and future workflow items.
- [ ] Current workflow tabs still work.
- [ ] Product collection and live refresh still work.
- [ ] Product table remains readable.
- [ ] Fixed product filters remain supplier-only plus price/stock/filled-fields.
- [ ] Diagnostics/error text is copyable.
- [ ] `desktop_launcher.py` does not exceed the file budget.

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-06-04-launcher-v4-ux-redesign.md`.

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using checkpoints.
