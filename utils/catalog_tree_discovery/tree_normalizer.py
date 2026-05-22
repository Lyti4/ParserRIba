"""Label cleanup helpers for launcher-facing discovery trees."""

from __future__ import annotations

import re
from urllib.parse import urlparse


_SEPARATOR_RE = re.compile(r"[\s\-_–—|/]+")
_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_LATIN_OR_DIGIT_RE = re.compile(r"[A-Za-z0-9]")


def normalize_label_for_launcher(original: str, fallback_url: str = "") -> str:
    """Return a readable launcher label with a stable fallback."""
    cleaned = _clean_text(original)
    if _has_readable_signal(cleaned):
        return cleaned
    fallback = _label_from_url(fallback_url)
    if fallback:
        return fallback
    return "Раздел"


def _clean_text(value: str) -> str:
    text = str(value or "").strip()
    text = _SEPARATOR_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" .,:;|")
    return text


def _has_readable_signal(value: str) -> bool:
    if _CYRILLIC_RE.search(value):
        return True
    return bool(_LATIN_OR_DIGIT_RE.search(value))


def _label_from_url(url: str) -> str:
    path = urlparse(str(url or "")).path.strip("/")
    if not path:
        return ""
    slug = path.split("/")[-1]
    slug = re.sub(r"--\d+$", "", slug)
    slug = slug.replace("%20", " ")
    slug = _clean_text(slug)
    if not slug:
        return ""
    if _CYRILLIC_RE.search(slug):
        return slug
    return slug.replace(" ", " ").title()
