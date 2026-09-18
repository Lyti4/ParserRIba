"""Launcher visual theme tokens and QSS."""

from __future__ import annotations

from typing import Any, Literal

ThemeMode = Literal["light", "dark"]

DARK_THEME = {
    "bg": "#0F1117",
    "surface": "#171A21",
    "surfaceRaised": "#20242E",
    "paper": "#F2F4F8",
    "paperMuted": "#E4E8F0",
    "ink": "#151922",
    "text": "#F4F6FA",
    "textMuted": "#A8B0BD",
    "accent": "#4C8DFF",
    "selected": "#243B63",
    "warning": "#D99A2B",
    "danger": "#E25A5A",
    "border": "#303744",
    "grid": "#CED4DF",
    "tableBackground": "#F2F4F8",
    "tableText": "#151922",
    "scrollbarTrack": "#171A21",
    "scrollbarHandle": "#3A4354",
}

LIGHT_THEME = {
    "bg": "#F7F8FA",
    "surface": "#FFFFFF",
    "surfaceRaised": "#EEF2F7",
    "paper": "#FFFFFF",
    "paperMuted": "#E9EDF4",
    "ink": "#1D2129",
    "text": "#1D2129",
    "textMuted": "#667085",
    "accent": "#2563EB",
    "selected": "#DCEBFF",
    "warning": "#B7791F",
    "danger": "#C24141",
    "border": "#D6DCE5",
    "grid": "#D6DCE5",
    "tableBackground": "#FFFFFF",
    "tableText": "#1D2129",
    "scrollbarTrack": "#EEF2F7",
    "scrollbarHandle": "#C7D0DE",
}

THEMES: dict[ThemeMode, dict[str, str]] = {"dark": DARK_THEME, "light": LIGHT_THEME}
_ARCHIVE_TOKENS = {
    "bg": "#11160F",
    "surface": "#192119",
    "surfaceRaised": "#222B21",
    "paper": "#EEE6D2",
    "paperMuted": "#D7CCB4",
    "ink": "#14120E",
    "text": "#ECE7DA",
    "textMuted": "#AFA58F",
    "accent": "#B08A45",
    "selected": "#2F4B36",
    "danger": "#9D2E2E",
    "border": "#3B4638",
    "grid": "#C8BFA9",
}
ARCHIVE_THEME = {f"archive.{key}": value for key, value in _ARCHIVE_TOKENS.items()}
ARCHIVE_THEME["archive.brass"] = _ARCHIVE_TOKENS["accent"]
ARCHIVE_THEME["archive.redPencil"] = _ARCHIVE_TOKENS["danger"]


def theme_tokens(mode: str = "dark") -> dict[str, str]:
    """Return stable theme tokens for a launcher mode."""
    return THEMES["light" if mode == "light" else "dark"]


def build_launcher_qss(mode: str = "dark") -> str:
    """Return application stylesheet for the launcher shell."""
    t = theme_tokens(mode)
    return f"""
QMainWindow, QWidget {{
    background: {t["bg"]};
    color: {t["text"]};
    font-family: "Segoe UI";
    font-size: 10pt;
}}
QGroupBox {{
    border: 1px solid {t["border"]};
    border-radius: 6px;
    margin-top: 12px;
    padding: 8px;
    background: {t["surface"]};
}}
QGroupBox::title {{
    color: {t["accent"]};
    padding: 0 4px;
}}
QLineEdit, QSpinBox, QComboBox, QTextEdit, QPlainTextEdit, QListWidget {{
    background: {t["paper"]};
    color: {t["ink"]};
    border: 1px solid {t["grid"]};
    border-radius: 4px;
    padding: 4px;
}}
QPushButton {{
    background: {t["surfaceRaised"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    border-radius: 4px;
    padding: 6px 10px;
}}
QPushButton:hover {{
    border-color: {t["accent"]};
}}
QPushButton:checked {{
    background: {t["selected"]};
    border-color: {t["accent"]};
}}
QPushButton:disabled {{
    color: {t["textMuted"]};
}}
QPushButton[routeAvailability="planned"] {{
    color: {t["textMuted"]};
    font-style: italic;
}}
QPushButton[navigationState="warning"] {{
    border-color: {t["warning"]};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus, QListWidget:focus {{
    border-color: {t["accent"]};
}}
QTableWidget {{
    background: {t["tableBackground"]};
    color: {t["tableText"]};
    gridline-color: {t["grid"]};
    selection-background-color: {t["selected"]};
    selection-color: {t["text"]};
}}
QScrollBar:vertical {{
    background: {t["scrollbarTrack"]};
    border: 1px solid {t["border"]};
    width: 14px;
    margin: 0;
}}
QScrollBar:horizontal {{
    background: {t["scrollbarTrack"]};
    border: 1px solid {t["border"]};
    height: 14px;
    margin: 0;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {t["scrollbarHandle"]};
    border: 1px solid {t["accent"]};
    border-radius: 4px;
    min-height: 28px;
    min-width: 28px;
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: {t["selected"]};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
    border: none;
    background: transparent;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: {t["bg"]};
}}
#launcherNavigationRail {{
    background: {t["surface"]};
    border-right: 1px solid {t["border"]};
}}
#launcherDiagnosticsText {{
    font-family: "Consolas";
    background: {t["paper"]};
    color: {t["ink"]};
}}
"""


def apply_launcher_theme(window: Any, mode: str = "dark") -> None:
    """Apply a launcher stylesheet to a Qt window."""
    if window is not None:
        window.setStyleSheet(build_launcher_qss(mode))
