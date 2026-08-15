"""Bounded passive page-runtime diagnostics for browser research."""

from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import unquote

from utils.interception_payload_helpers import SENSITIVE_QUERY_KEYS, sanitize_diagnostic_url

_MAX_EVENTS_PER_KIND = 8
_MAX_MESSAGE_CHARS = 240
_MAX_URL_CHARS = 260
_SENSITIVE_ASSIGNMENT_RE = re.compile(
    rf"(?:^|[?&#;\s])[^?&#;=:\s]*(?:{'|'.join(re.escape(item) for item in SENSITIVE_QUERY_KEYS)})"
    r"[^?&#;=:\s]*\s*(?:=|:)",
    re.IGNORECASE,
)


class BrowserRuntimeDiagnostics:
    """Collect bounded, redacted native page events without driving the page."""

    def __init__(self, page: Any, *, max_events_per_kind: int = _MAX_EVENTS_PER_KIND) -> None:
        self._page = page
        self._max_events_per_kind = max(1, int(max_events_per_kind))
        self._detached = False
        self._callbacks: dict[str, Callable[[Any], None]] = {
            "console": self._record_console,
            "pageerror": self._record_page_error,
            "requestfailed": self._record_request_failure,
        }
        self._observations: dict[str, list[dict[str, str]]] = {
            "console_messages": [],
            "page_errors": [],
            "network_requests": [],
        }

    @classmethod
    def attach(cls, page: Any, *, max_events_per_kind: int = _MAX_EVENTS_PER_KIND) -> "BrowserRuntimeDiagnostics":
        """Attach only passive listeners to one existing page."""
        diagnostics = cls(page, max_events_per_kind=max_events_per_kind)
        for event_name, callback in diagnostics._callbacks.items():
            page.on(event_name, callback)
        return diagnostics

    def snapshot(self) -> dict[str, list[dict[str, str]]]:
        """Return a JSON-safe copy of bounded, sanitized observations."""
        return {
            kind: [dict(item) for item in observations]
            for kind, observations in self._observations.items()
        }

    def detach(self) -> None:
        """Remove only this observer's listeners when the page exposes removal."""
        if self._detached:
            return
        self._detached = True
        remove_listener = getattr(self._page, "remove_listener", None)
        if not callable(remove_listener):
            return
        for event_name, callback in self._callbacks.items():
            try:
                remove_listener(event_name, callback)
            except Exception:
                continue

    def _record_console(self, message: Any) -> None:
        level = _normalized_level(_event_value(message, "type"))
        text = _safe_message(_event_value(message, "text"))
        location = _safe_url(_location_url(_event_value(message, "location")))
        self._append(
            "console_messages",
            {
                "level": level,
                "location": location,
                "source": "playwright_console",
                "text": text,
            },
        )

    def _record_page_error(self, error: Any) -> None:
        self._append(
            "page_errors",
            {
                "message": _safe_message(error),
                "source": "playwright_pageerror",
            },
        )

    def _record_request_failure(self, request: Any) -> None:
        self._append(
            "network_requests",
            {
                "failure": _safe_message(_event_value(request, "failure")),
                "source": "playwright_network",
                "url": _safe_url(_event_value(request, "url")),
            },
        )

    def _append(self, kind: str, observation: dict[str, str]) -> None:
        events = self._observations[kind]
        if len(events) < self._max_events_per_kind:
            events.append(observation)


def _event_value(event: Any, name: str) -> Any:
    value = getattr(event, name, "")
    if callable(value):
        try:
            return value()
        except Exception:
            return ""
    return value


def _location_url(location: Any) -> Any:
    if isinstance(location, dict):
        return location.get("url", "")
    return _event_value(location, "url")


def _normalized_level(value: Any) -> str:
    level = _safe_message(value).casefold()
    if level == "warn":
        return "warning"
    if level in {"debug", "error", "info", "log", "warning"}:
        return level
    return "info"


def _safe_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return sanitize_diagnostic_url(value, max_length=_MAX_URL_CHARS)


def _safe_message(value: Any) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).split())[:_MAX_MESSAGE_CHARS]
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return ""
    if "%25" in text.casefold():
        return "[redacted]"
    decoded = text
    for _ in range(4):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    if _SENSITIVE_ASSIGNMENT_RE.search(decoded):
        return "[redacted]"
    return text
