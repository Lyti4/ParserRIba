"""Embedded JSON and hydration extractors for catalog research."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from models.catalog_discovery import ApiEvidence, CategoryEvidence
from utils.catalog_tree_discovery.payload_classifiers import classify_payload

EMBEDDED_JSON_MARKERS = ("__next_data__", "__apollo_state__", "dehydratedstate", "catalog", "category", "children")
CATALOG_URL_PATTERN = re.compile(r'["\'](/(?:catalog|category|categories)/[^"\']+)["\']', re.IGNORECASE)
JSON_SCRIPT_HINTS = ("__NEXT_DATA__", "__APOLLO_STATE__", "application/json")
LABEL_KEYS = ("name", "title", "label", "caption")
URL_KEYS = ("url", "href", "path")


def extract_embedded_category_evidence(base_url: str, html: str) -> list[CategoryEvidence]:
    """Extract category-like URLs from hydration scripts and embedded blobs."""
    result: list[CategoryEvidence] = []
    seen: set[str] = set()
    for item in _extract_structured_category_evidence(base_url, html):
        if item.url in seen:
            continue
        seen.add(item.url)
        result.append(item)
    for match in CATALOG_URL_PATTERN.findall(str(html or "")):
        url = urljoin(base_url, match)
        if url in seen:
            continue
        seen.add(url)
        result.append(CategoryEvidence(name=_derive_category_label(url), url=url, source="embedded_json"))
    return result


def extract_embedded_api_hints(html: str) -> list[ApiEvidence]:
    """Extract lightweight hydration/api hints from rendered HTML."""
    lowered = str(html or "").casefold()
    hints: list[ApiEvidence] = []
    seen: set[tuple[str, str]] = set()
    for marker in EMBEDDED_JSON_MARKERS:
        if marker not in lowered:
            continue
        key = ("embedded_marker", marker)
        if key in seen:
            continue
        seen.add(key)
        hints.append(ApiEvidence(kind="embedded_marker", value=marker, source="embedded_json"))
    if "__next_data__" in lowered:
        hints.append(ApiEvidence(kind="framework", value="nextjs_hydration", source="embedded_json"))
    return hints


def _extract_structured_category_evidence(base_url: str, html: str) -> list[CategoryEvidence]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    result: list[CategoryEvidence] = []
    seen: set[str] = set()
    for script in soup.find_all("script"):
        script_type = str(script.get("type") or "")
        script_id = str(script.get("id") or "")
        script_text = script.get_text(" ", strip=True)
        if not script_text or not _looks_like_json_script(script_type, script_id, script_text):
            continue
        classification = classify_payload(base_url=base_url, content_type=script_type, body_text=script_text)
        for item in classification.categories:
            if item.url in seen:
                continue
            seen.add(item.url)
            result.append(CategoryEvidence(name=item.name, url=item.url, source="embedded_json"))
    return result


def _looks_like_json_script(script_type: str, script_id: str, script_text: str) -> bool:
    if any(hint.casefold() in f"{script_type} {script_id}".casefold() for hint in JSON_SCRIPT_HINTS):
        return True
    lowered = script_text.casefold()
    return lowered.startswith("{") and ("/catalog/" in lowered or '"children"' in lowered)


def _try_load_json(script_text: str) -> Any | None:
    try:
        return json.loads(script_text)
    except json.JSONDecodeError:
        return None


def _walk_category_objects(payload: Any, base_url: str) -> list[CategoryEvidence]:
    result: list[CategoryEvidence] = []
    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            url = _extract_category_url(current, base_url)
            if url:
                result.append(
                    CategoryEvidence(
                        name=_extract_label(current, url),
                        url=url,
                        source="embedded_json",
                    )
                )
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return result


def _extract_category_url(payload: dict[str, Any], base_url: str) -> str:
    for key in URL_KEYS:
        value = payload.get(key)
        if not isinstance(value, str):
            continue
        url = urljoin(base_url, value)
        lowered = url.casefold()
        if "/catalog/" in lowered or "/category/" in lowered or "/categories/" in lowered:
            return url
    return ""


def _extract_label(payload: dict[str, Any], url: str) -> str:
    for key in LABEL_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _derive_category_label(url)


def _derive_category_label(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else ""
    if not slug:
        return "Каталог"
    slug = re.sub(r"--?[0-9a-z]+$", "", slug, flags=re.IGNORECASE)
    slug = slug.replace("-", " ").replace("_", " ").strip()
    if not slug:
        return "Каталог"
    return slug[:1].upper() + slug[1:]
