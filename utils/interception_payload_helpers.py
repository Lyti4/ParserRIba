"""Payload parsing and redaction helpers for interception diagnostics."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SENSITIVE_QUERY_KEYS = tuple(
    "access auth authorization captcha cookie email hcheck key oirut password phone refresh request_ secret session sid token".split()
)


def safe_json_loads(payload: str) -> Any:
    """Parse JSON payloads and return None on malformed content."""
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def sanitize_diagnostic_url(url: str, max_length: int = 260) -> str:
    """Mask sensitive query values before writing diagnostic URLs."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url[:max_length]
    safe_query: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_QUERY_KEYS):
            safe_query.append((key, "***"))
        else:
            safe_query.append((key, value))
    sanitized = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_query), parts.fragment))
    return sanitized[:max_length]


def payload_has_empty_products(payload: str) -> bool:
    """Detect product API payloads that explicitly contain empty product lists."""
    compact = re.sub(r"\s+", "", payload)
    empty_markers = (
        '"products":[]',
        '"productsList":[]',
        '"items":[]',
        '"results":[]',
        '"data":[]',
        '"productsResponse":null',
    )
    return compact == "[]" or any(marker in compact for marker in empty_markers)


def payload_preview(payload: str, max_length: int = 500) -> str:
    """Return a compact response preview for diagnostics."""
    parsed = safe_json_loads(payload)
    if parsed is not None:
        redacted, changed = _redact_sensitive_payload_value(parsed)
        if changed:
            safe_payload = json.dumps(redacted, ensure_ascii=False)
            return safe_payload[:max_length]
    compact = re.sub(r"\s+", " ", payload).strip()
    compact = _redact_sensitive_text_fields(compact)
    return compact[:max_length]


def _is_sensitive_key(key: Any) -> bool:
    lowered = str(key).lower()
    return any(marker in lowered for marker in SENSITIVE_QUERY_KEYS)


def _redact_sensitive_payload_value(value: Any) -> tuple[Any, bool]:
    if isinstance(value, dict):
        changed = False
        result: dict[str, Any] = {}
        for key, nested in value.items():
            if _is_sensitive_key(key):
                result[str(key)] = "***"
                changed = True
                continue
            redacted, nested_changed = _redact_sensitive_payload_value(nested)
            result[str(key)] = redacted
            changed = changed or nested_changed
        return result, changed
    if isinstance(value, list):
        changed = False
        result: list[Any] = []
        for item in value:
            redacted, nested_changed = _redact_sensitive_payload_value(item)
            result.append(redacted)
            changed = changed or nested_changed
        return result, changed
    return value, False


def _redact_sensitive_text_fields(value: str) -> str:
    redacted = value
    for marker in SENSITIVE_QUERY_KEYS:
        pattern = re.compile(rf'("{re.escape(marker)}[^"]*"\s*:\s*)"[^"]*"', re.IGNORECASE)
        redacted = pattern.sub(r'\1"***"', redacted)
    return redacted
