"""Shared fail-closed checks for sensitive or ambiguously encoded URL material."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

_MAX_DECODE_ROUNDS = 4
_MALFORMED_PERCENT_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(?:"
    r"password|passwd|secret|token|api[_-]?key|access[_-]?token|authorization|bearer|"
    r"credentials?|cookies?|cookie[_-]?jar|proxy(?:[_-].*)?|proxies|"
    r"profile(?:[_-](?:dir|path))?|browser[_-]?profile|captcha(?:[_-].*)?|"
    r"session(?:[_-].*)?|(?:request|response)[_-]?headers?|headers?"
    r")\b\s*[:=]"
)
_SENSITIVE_QUERY_KEY = re.compile(
    r"(?i)^(?:"
    r"password|passwd|secret|token|api[_-]?key|access[_-]?token|authorization|bearer|"
    r"credentials?|cookies?|cookie[_-]?jar|proxy(?:[_-].*)?|proxies|"
    r"profile(?:[_-](?:dir|path))?|browser[_-]?profile|captcha(?:[_-].*)?|"
    r"session(?:[_-].*)?|(?:request|response)[_-]?headers?|headers?"
    r")$"
)
_RESTRICTED_ARTIFACT_PATH = re.compile(
    r"(?i)(?:^|/)(?:browser[-_]profile|profile|cookies?(?:\.[^/]*)?|cookie[-_]jar|"
    r"storage[-_]state|session[-_](?:state|data))(?:/|$)"
)


def contains_sensitive_url_material(value: str) -> bool:
    """Return whether text contains sensitive, credentialed, or ambiguous URL material."""
    if not isinstance(value, str):
        return True

    current = value
    seen = {current}
    for _ in range(_MAX_DECODE_ROUNDS + 1):
        if _SENSITIVE_ASSIGNMENT.search(current):
            return True
        if _looks_like_url_material(current):
            if _MALFORMED_PERCENT_ESCAPE.search(current):
                return True
            return _url_level_is_unsafe(current)
        if "%" not in current:
            return False

        decoded = unquote(current)
        if decoded == current:
            return False
        if decoded in seen:
            return True
        seen.add(decoded)
        current = decoded

    if _SENSITIVE_ASSIGNMENT.search(current):
        return True
    if _looks_like_url_material(current):
        if _MALFORMED_PERCENT_ESCAPE.search(current):
            return True
        return _url_level_is_unsafe(current)
    return unquote(current) != current


def decode_url_component_bounded(value: str) -> str | None:
    """Decode one URL component within the shared limit, or return None if unresolved."""
    if not isinstance(value, str):
        return None
    current = value
    seen = {current}
    for _ in range(_MAX_DECODE_ROUNDS + 1):
        if _MALFORMED_PERCENT_ESCAPE.search(current):
            return None
        decoded = unquote(current)
        if decoded == current:
            return current
        if decoded in seen:
            return None
        seen.add(decoded)
        current = decoded
    if _MALFORMED_PERCENT_ESCAPE.search(current):
        return None
    return None if unquote(current) != current else current


def contains_restricted_artifact_reference(value: str) -> bool:
    """Return whether an artifact/evidence reference exposes operational state."""
    if not isinstance(value, str) or not value.strip():
        return True
    if contains_sensitive_url_material(value):
        return True
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        return True
    components = (parsed.path, parsed.query, parsed.fragment) if parsed.scheme else (value,)
    for raw_component in components:
        decoded_component = decode_url_component_bounded(raw_component)
        if decoded_component is None or _RESTRICTED_ARTIFACT_PATH.search(
            decoded_component.replace("\\", "/")
        ) is not None:
            return True
    return False


def is_explicit_http_url(value: str, *, require_https: bool = False) -> bool:
    """Return whether value is an absolute non-credentialed HTTP(S) URL."""
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.strip()
    if any(character.isspace() or ord(character) < 32 for character in normalized):
        return False
    if _MALFORMED_PERCENT_ESCAPE.search(normalized):
        return False
    if contains_sensitive_url_material(normalized):
        return False
    try:
        parsed = urlsplit(normalized)
        parsed.port
    except ValueError:
        return False
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    return (
        parsed.scheme.lower() in allowed_schemes
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
    )


def _url_level_is_unsafe(value: str, *, depth: int = 0) -> bool:
    if any(character.isspace() or ord(character) < 32 for character in value):
        return True
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError:
        return _looks_like_url_material(value)
    if parsed.scheme.casefold() in {"http", "https"} and not parsed.hostname:
        return True
    if parsed.username is not None or parsed.password is not None:
        return True
    if _MALFORMED_PERCENT_ESCAPE.search(parsed.path):
        return True
    if _encoded_component_is_unsafe(parsed.path, depth=depth):
        return True
    for component in (parsed.query, parsed.fragment):
        for pair in component.split("&"):
            raw_key, separator, raw_value = pair.partition("=")
            if _MALFORMED_PERCENT_ESCAPE.search(raw_key) or _MALFORMED_PERCENT_ESCAPE.search(
                raw_value
            ):
                return True
            if _decoded_query_key_is_unsafe(raw_key):
                return True
            if separator and _encoded_component_is_unsafe(raw_value, depth=depth):
                return True
    return False


def _decoded_query_key_is_unsafe(raw_key: str) -> bool:
    current = raw_key
    seen = {current}
    for _ in range(_MAX_DECODE_ROUNDS + 1):
        if _MALFORMED_PERCENT_ESCAPE.search(current):
            return True
        if _SENSITIVE_QUERY_KEY.fullmatch(current.strip()):
            return True
        if "%" not in current:
            return False
        decoded = unquote(current)
        if decoded == current:
            return False
        if decoded in seen:
            return True
        seen.add(decoded)
        current = decoded
    if _MALFORMED_PERCENT_ESCAPE.search(current):
        return True
    if _SENSITIVE_QUERY_KEY.fullmatch(current.strip()):
        return True
    return unquote(current) != current


def _encoded_component_is_unsafe(raw_value: str, *, depth: int) -> bool:
    current = raw_value
    seen = {current}
    for _ in range(_MAX_DECODE_ROUNDS + 1):
        if _MALFORMED_PERCENT_ESCAPE.search(current):
            if current.endswith("%") and not _MALFORMED_PERCENT_ESCAPE.search(current[:-1]):
                return False
            return True
        if _SENSITIVE_ASSIGNMENT.search(current):
            return True
        if _looks_like_url_material(current):
            if depth >= _MAX_DECODE_ROUNDS:
                return True
            return _url_level_is_unsafe(current, depth=depth + 1)
        if "%" not in current:
            return False
        decoded = unquote(current)
        if decoded == current:
            return False
        if decoded in seen:
            return True
        seen.add(decoded)
        current = decoded
    if _MALFORMED_PERCENT_ESCAPE.search(current) or _SENSITIVE_ASSIGNMENT.search(current):
        return True
    if _looks_like_url_material(current):
        if depth >= _MAX_DECODE_ROUNDS:
            return True
        return _url_level_is_unsafe(current, depth=depth + 1)
    return unquote(current) != current


def _looks_like_url_material(value: str) -> bool:
    lowered = value.lstrip().casefold()
    return "://" in value or lowered.startswith(("http:", "https:", "file:"))
