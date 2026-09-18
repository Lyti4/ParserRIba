"""Copyable launcher diagnostics panel."""

from __future__ import annotations

import re

from models.launcher_state import LauncherAppState


SECRET_MARK = "***"
PROXY_CREDENTIAL_RE = re.compile(r"(?P<scheme>https?://|socks5://)[^/\s:@]+:[^/\s@]+@")
SECRET_QUERY_RE = re.compile(r"([?&][^=\s]*(?:token|password|session|secret|cookie|auth)[^=\s]*=)[^&\s]+", re.IGNORECASE)
SECRET_ASSIGNMENT_RE = re.compile(r"\b(token|password|session|secret|cookie|authorization|auth_header)=\S+", re.IGNORECASE)


def build_error_box(shell: object, qtwidgets: object) -> object:
    """Build a launcher tab with copyable task diagnostics."""
    box = qtwidgets.QGroupBox("\u0414\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430")
    layout = qtwidgets.QVBoxLayout(box)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
    shell.error_log_text = qtwidgets.QPlainTextEdit()
    shell.error_log_text.setObjectName("launcherDiagnosticsText")
    shell.error_log_text.setReadOnly(True)
    shell.error_log_text.setMinimumHeight(240)
    layout.addWidget(shell.error_log_text, stretch=1)
    copy_button = qtwidgets.QPushButton("\u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0443")
    copy_button.clicked.connect(lambda: _copy_and_refresh(shell))
    shell.action_buttons["copy_errors"] = copy_button
    layout.addWidget(copy_button)
    latest_button = qtwidgets.QPushButton("\u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u044e\u044e \u043e\u0448\u0438\u0431\u043a\u0443")
    latest_button.clicked.connect(lambda: _copy_latest_and_refresh(shell))
    shell.action_buttons["copy_latest_error"] = latest_button
    layout.addWidget(latest_button)
    refresh_error_panel(shell)
    return box


def refresh_error_panel(shell: object) -> None:
    """Refresh copyable diagnostics in the launcher error panel."""
    widget = getattr(shell, "error_log_text", None)
    state = getattr(shell, "state", None)
    if widget is None or state is None:
        return
    text = build_error_log_text(state)
    if widget.toPlainText() != text:
        widget.setPlainText(text)


def copy_error_log_to_clipboard(shell: object) -> bool:
    """Copy current diagnostic text into the system clipboard."""
    widget = getattr(shell, "error_log_text", None)
    qtwidgets = getattr(shell, "_qtwidgets", None)
    state = getattr(shell, "state", None)
    if widget is None or qtwidgets is None:
        return False
    app = qtwidgets.QApplication.instance()
    if app is None:
        return False
    app.clipboard().setText(widget.toPlainText())
    if state is not None:
        state.task.message = "\u0414\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0430 \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u0430 \u0432 \u0431\u0443\u0444\u0435\u0440 \u043e\u0431\u043c\u0435\u043d\u0430."
    return True


def copy_latest_error_to_clipboard(shell: object) -> bool:
    """Copy only the latest masked error into the system clipboard."""
    qtwidgets = getattr(shell, "_qtwidgets", None)
    state = getattr(shell, "state", None)
    if qtwidgets is None or state is None:
        return False
    app = qtwidgets.QApplication.instance()
    if app is None:
        return False
    app.clipboard().setText(build_latest_error_text(state))
    state.task.message = "\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u043e\u0448\u0438\u0431\u043a\u0430 \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u0430 \u0432 \u0431\u0443\u0444\u0435\u0440 \u043e\u0431\u043c\u0435\u043d\u0430."
    return True


def _copy_and_refresh(shell: object) -> None:
    copy_error_log_to_clipboard(shell)
    refresh = getattr(shell, "_refresh_ui", None)
    if callable(refresh):
        refresh()


def _copy_latest_and_refresh(shell: object) -> None:
    copy_latest_error_to_clipboard(shell)
    refresh = getattr(shell, "_refresh_ui", None)
    if callable(refresh):
        refresh()


def build_latest_error_text(state: LauncherAppState) -> str:
    """Build a short masked latest-error text for support copy."""
    if state.task.status != "failed" or not state.task.last_error:
        return "\u041e\u0448\u0438\u0431\u043e\u043a \u043d\u0435\u0442."
    return _mask_sensitive_text(state.task.last_error)


def build_error_log_text(state: LauncherAppState) -> str:
    """Build plain text diagnostics that the user can copy from the launcher."""
    current_error = state.task.status == "failed"
    has_error_context = any(
        [
            current_error and state.task.last_error,
            current_error,
            state.task.message,
            state.result.json_path,
            state.result.excel_path,
        ]
    )
    if not has_error_context:
        return "\u041e\u0448\u0438\u0431\u043e\u043a \u043d\u0435\u0442."
    lines = [
        f"\u0421\u0442\u0430\u0442\u0443\u0441: {state.task.status}",
        f"\u0417\u0430\u0434\u0430\u0447\u0430: {state.task.task_name or '-'}",
    ]
    if state.task.phase:
        lines.append(f"\u042d\u0442\u0430\u043f: {state.task.phase}")
    if state.task.message:
        lines.append(f"\u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435: {_mask_sensitive_text(state.task.message)}")
    if current_error and state.task.last_error:
        lines.append(f"\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u043e\u0448\u0438\u0431\u043a\u0430: {build_latest_error_text(state)}")
    if state.products.source_categories:
        lines.append(f"\u0420\u0430\u0437\u0434\u0435\u043b\u044b: {', '.join(state.products.source_categories)}")
    lines.append(f"\u0422\u043e\u0432\u0430\u0440\u043e\u0432 \u0432 \u0440\u0430\u0431\u043e\u0447\u0435\u0439 \u043e\u0431\u043b\u0430\u0441\u0442\u0438: {state.products.products_count}")
    if state.result.json_path:
        lines.append(f"JSON: {_mask_sensitive_text(state.result.json_path)}")
    if state.result.excel_path:
        lines.append(f"Excel: {_mask_sensitive_text(state.result.excel_path)}")
    lines.append(f"\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430\u0433: {_next_step_summary(state)}")
    return "\n".join(lines)


def _mask_sensitive_text(text: object) -> str:
    value = str(text or "")
    value = PROXY_CREDENTIAL_RE.sub(lambda match: f"{match.group('scheme')}{SECRET_MARK}:{SECRET_MARK}@", value)
    value = SECRET_QUERY_RE.sub(lambda match: f"{match.group(1)}{SECRET_MARK}", value)
    return SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}={SECRET_MARK}", value)


def _next_step_summary(state: LauncherAppState) -> str:
    if state.task.status != "failed":
        return "\u041e\u0448\u0438\u0431\u043e\u043a \u043d\u0435\u0442."
    error = f"{state.task.last_error} {state.task.message}".lower()
    if "captcha" in error or "challenge" in error:
        return "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0437\u0430\u0449\u0438\u0442\u0443 \u0441\u0430\u0439\u0442\u0430, \u043f\u0440\u043e\u0444\u0438\u043b\u044c \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u0430 \u0438 \u0440\u0443\u0447\u043d\u043e\u0435 \u043f\u0440\u043e\u0445\u043e\u0436\u0434\u0435\u043d\u0438\u0435 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438."
    if "proxy" in error or "407" in error:
        return "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u043f\u0440\u043e\u043a\u0441\u0438, \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044e, \u0431\u0430\u043b\u0430\u043d\u0441 \u0438 \u0440\u043e\u0441\u0441\u0438\u0439\u0441\u043a\u0438\u0439 \u043c\u0430\u0440\u0448\u0440\u0443\u0442."
    if state.task.status == "failed":
        return "\u041e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u043a\u0443, \u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u043f\u0440\u0438\u0447\u0438\u043d\u0443 \u0438 \u043f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 \u0437\u0430\u0434\u0430\u0447\u0443."
    return "\u041e\u0448\u0438\u0431\u043e\u043a \u043d\u0435\u0442."
