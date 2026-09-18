"""Proxy management panel for the desktop launcher."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from utils.env import read_dotenv_values, update_dotenv_values
from utils.proxy import load_proxy_config_from_env, mask_proxy_url, parse_proxy_url, split_proxy_urls

PROXY_KEYS = ("PARSER_PROXY_ENABLED", "PARSER_PROXY_SCHEME", "PARSER_PROXY", "PARSER_PROXIES")
CHECK_IP_URL = "https://api.ipify.org?format=json"


def build_proxy_box(shell: Any, qtwidgets: Any) -> Any:
    """Build a local proxy settings panel."""
    widget = qtwidgets.QWidget()
    layout = qtwidgets.QVBoxLayout(widget)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    settings_box = qtwidgets.QGroupBox("Прокси для защищённых магазинов")
    form = qtwidgets.QGridLayout(settings_box)
    shell.proxy_enabled_checkbox = qtwidgets.QCheckBox("Использовать прокси")
    shell.proxy_scheme_combo = qtwidgets.QComboBox()
    shell.proxy_scheme_combo.addItem("HTTP", "http")
    shell.proxy_scheme_combo.addItem("SOCKS5", "socks5")
    shell.proxy_input = qtwidgets.QPlainTextEdit()
    shell.proxy_input.setObjectName("launcherProxyInput")
    shell.proxy_input.setPlaceholderText("Вставьте новые прокси, по одному на строку: host:port:login:password")
    shell.proxy_input.setMinimumHeight(150)
    shell.proxy_input.setMaximumHeight(260)
    form.addWidget(shell.proxy_enabled_checkbox, 0, 0)
    form.addWidget(qtwidgets.QLabel("Протокол"), 0, 1)
    form.addWidget(shell.proxy_scheme_combo, 0, 2)
    form.addWidget(qtwidgets.QLabel("Новый список"), 1, 0, 1, 3)
    form.addWidget(shell.proxy_input, 2, 0, 1, 3)

    shell.proxy_status_label = qtwidgets.QLabel("")
    shell.proxy_status_label.setObjectName("launcherProxyStatusLabel")
    shell.proxy_status_label.setWordWrap(True)
    shell.proxy_diagnostics_label = qtwidgets.QLabel("")
    shell.proxy_diagnostics_label.setObjectName("launcherProxyDiagnosticsLabel")
    shell.proxy_diagnostics_label.setWordWrap(True)

    button_row = qtwidgets.QWidget()
    button_layout = qtwidgets.QHBoxLayout(button_row)
    button_layout.setContentsMargins(0, 0, 0, 0)
    save_button = qtwidgets.QPushButton("Сохранить прокси")
    save_button.clicked.connect(lambda: save_proxy_settings_from_widgets(shell))
    check_button = qtwidgets.QPushButton("Проверить первый")
    check_button.clicked.connect(lambda: check_first_proxy_from_panel(shell))
    button_layout.addWidget(save_button)
    button_layout.addWidget(check_button)
    button_layout.addStretch(1)

    layout.addWidget(settings_box)
    layout.addWidget(shell.proxy_status_label)
    layout.addWidget(shell.proxy_diagnostics_label)
    layout.addWidget(button_row)
    layout.addStretch(1)
    refresh_proxy_panel(shell)
    return widget


def refresh_proxy_panel(shell: Any) -> None:
    """Refresh proxy controls from the local .env file."""
    values = read_dotenv_values(_env_path(shell))
    config = load_proxy_config_from_env(values)
    if getattr(shell, "proxy_enabled_checkbox", None) is not None:
        shell.proxy_enabled_checkbox.setChecked(config.enabled)
    if getattr(shell, "proxy_scheme_combo", None) is not None:
        index = shell.proxy_scheme_combo.findData(config.scheme)
        shell.proxy_scheme_combo.setCurrentIndex(index if index >= 0 else 0)
    if getattr(shell, "proxy_input", None) is not None:
        shell.proxy_input.clear()
    if getattr(shell, "proxy_status_label", None) is not None:
        shell.proxy_status_label.setText(_proxy_summary(values))
    if getattr(shell, "proxy_diagnostics_label", None) is not None:
        shell.proxy_diagnostics_label.setText(_latest_proxy_diagnostic_hint(Path(shell.root_dir)))


def save_proxy_settings_from_widgets(shell: Any) -> Path:
    """Persist proxy settings from the panel to .env and current process env."""
    env_path = _env_path(shell)
    current = read_dotenv_values(env_path)
    pasted_urls = split_proxy_urls(shell.proxy_input.toPlainText()) if getattr(shell, "proxy_input", None) else []
    enabled = bool(shell.proxy_enabled_checkbox.isChecked()) if getattr(shell, "proxy_enabled_checkbox", None) else True
    scheme = str(shell.proxy_scheme_combo.currentData()) if getattr(shell, "proxy_scheme_combo", None) else "http"
    updates = {
        "PARSER_PROXY_ENABLED": "1" if enabled else "0",
        "PARSER_PROXY_SCHEME": scheme,
        "PARSER_PROXY": pasted_urls[0] if pasted_urls else current.get("PARSER_PROXY", ""),
        "PARSER_PROXIES": ";".join(pasted_urls[1:]) if pasted_urls else current.get("PARSER_PROXIES", ""),
    }
    saved_path = update_dotenv_values(env_path, updates)
    for key, value in updates.items():
        os.environ[key] = value
    if getattr(shell, "proxy_input", None) is not None:
        shell.proxy_input.clear()
    if getattr(shell, "proxy_status_label", None) is not None:
        shell.proxy_status_label.setText(_proxy_summary({**current, **updates}) + "\nСохранено в локальный .env.")
    return saved_path


def check_first_proxy_from_panel(shell: Any) -> bool:
    """Run a small synchronous first-proxy connectivity check for the panel."""
    if getattr(shell, "proxy_input", None) is not None and shell.proxy_input.toPlainText().strip():
        save_proxy_settings_from_widgets(shell)
    values = read_dotenv_values(_env_path(shell))
    config = load_proxy_config_from_env(values)
    if not config.enabled:
        _set_proxy_diagnostics(shell, "Прокси выключен. Включите proxy и сохраните настройки.")
        return False
    if not config.urls:
        _set_proxy_diagnostics(shell, "Прокси не задан. Вставьте российский endpoint и сохраните настройки.")
        return False
    proxy_url = config.urls[0]
    opener = build_opener(ProxyHandler({"http": proxy_url, "https": proxy_url}))
    try:
        with opener.open(CHECK_IP_URL, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError) as exc:
        safe_error = _safe_proxy_error(str(exc), proxy_url)
        _set_proxy_diagnostics(
            shell,
            "Первый proxy не прошёл проверку. Проверьте RU endpoint, пароль, баланс и протокол. "
            f"{_lteboost_hint(proxy_url)}Ошибка: {safe_error}",
        )
        return False
    ip = str(payload.get("ip") or "неизвестно")
    _set_proxy_diagnostics(shell, f"Первый proxy отвечает. Внешний IP: {ip}. Теперь можно запускать smoke/сбор.")
    return True


def _env_path(shell: Any) -> Path:
    return Path(shell.root_dir) / ".env"


def _proxy_summary(values: dict[str, str]) -> str:
    config = load_proxy_config_from_env(values)
    if not config.enabled:
        return "Прокси выключен. Сбор пойдёт напрямую; для защищённых магазинов это часто приводит к 403 или сбросу соединения."
    if not config.urls:
        return "Прокси не задан. Для защищённых магазинов обычно нужен российский HTTP/SOCKS5 proxy."
    masked = [mask_proxy_url(proxy_url) for proxy_url in config.urls[:5]]
    more = f"\nЕщё: {len(config.urls) - len(masked)}" if len(config.urls) > len(masked) else ""
    return f"Прокси включён. Найдено: {len(config.urls)}. Первые маршруты:\n" + "\n".join(masked) + more


def _latest_proxy_diagnostic_hint(root_dir: Path) -> str:
    report_path = _latest_smoke_report_path(root_dir)
    if not report_path.exists():
        return "Последняя диагностика proxy ещё не запускалась."
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "Последняя диагностика proxy повреждена: запустите smoke заново."
    diagnostics = payload.get("proxy_diagnostics") or {}
    health = diagnostics.get("health") or {}
    preflight = diagnostics.get("preflight") or {}
    status = str(health.get("status") or "")
    risk = str(health.get("traffic_risk") or "")
    if status == "preflight_failed":
        action = "Проверьте RU endpoint, логин/пароль, баланс и протокол; сайт ещё не открывался."
    elif status == "proxy_auth_failed":
        action = "Проверьте авторизацию proxy или доступ аккаунта."
    elif status == "rate_limited":
        action = "Уменьшите частоту сборов или смените sticky session."
    elif status in {"ok", "network_failures", "upstream_errors"}:
        action = "Можно повторить smoke и смотреть уже site/challenge сигналы."
    else:
        action = "Запустите smoke после сохранения proxy."
    duration = preflight.get("duration_ms")
    duration_text = f", preflight {duration} мс" if isinstance(duration, int) else ""
    return f"Последняя диагностика: {status or 'нет статуса'}, риск: {risk or 'неизвестно'}{duration_text}. {action}"


def _latest_smoke_report_path(root_dir: Path) -> Path:
    data_dir = root_dir / "data"
    candidates = sorted(data_dir.glob("*_camoufox_smoke.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else data_dir / "camoufox_smoke.json"


def _set_proxy_diagnostics(shell: Any, message: str) -> None:
    if getattr(shell, "proxy_diagnostics_label", None) is not None:
        shell.proxy_diagnostics_label.setText(message)


def _safe_proxy_error(error: str, proxy_url: str) -> str:
    parsed = parse_proxy_url(proxy_url)
    safe = error.replace(proxy_url, mask_proxy_url(proxy_url))
    if parsed.username:
        safe = safe.replace(parsed.username, "***")
    if parsed.password:
        safe = safe.replace(parsed.password, "***")
    return safe[:220]


def _lteboost_hint(proxy_url: str) -> str:
    parsed = parse_proxy_url(proxy_url)
    server = parsed.server.lower()
    if "res.lteboost.com:1000" in server:
        return "Для LTEBoost это residential endpoint; если traffic у Residential не активен, используйте Mobile/Core HTTP host mob.lteboost.com:3000. "
    if "mob.lteboost.com:3002" in server:
        return "Для mob.lteboost.com:3002 выберите протокол SOCKS5; для HTTP обычно нужен mob.lteboost.com:3000. "
    return ""
