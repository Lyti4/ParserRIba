"""Allowlisted product evidence extracted from rendered JSON-LD scripts."""

from __future__ import annotations

import json
import math
import re
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from utils.interception_payload_helpers import SENSITIVE_QUERY_KEYS, sanitize_diagnostic_url

_MAX_EVIDENCE_ITEMS = 10
_MAX_RENDERED_HTML_CHARS = 2_000_000
_MAX_JSON_LD_SCRIPT_CHARS = 256_000
_MAX_JSON_LD_SCRIPTS = 64
_MAX_VISITED_NODES = 10_000
_SENSITIVE_ASSIGNMENT_RE = re.compile(
    rf"(?:^|[?&#;\s])[^?&#;=:\s]*(?:{'|'.join(re.escape(item) for item in SENSITIVE_QUERY_KEYS)})"
    r"[^?&#;=:\s]*\s*(?:=|:)",
    re.IGNORECASE,
)


def extract_structured_product_evidence(
    page_html: str,
    *,
    base_url: str,
    limit: int = _MAX_EVIDENCE_ITEMS,
) -> list[dict[str, str]]:
    """Return compact, report-safe JSON-LD Product evidence.

    This helper reads already-rendered HTML. It does not navigate, mutate the page,
    or promote evidence into canonical products. Only explicitly allowlisted product
    fields are retained; malformed scripts and unsafe URLs are ignored.
    """

    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return []
    evidence_limit = min(limit, _MAX_EVIDENCE_ITEMS)
    rendered_html = str(page_html or "")
    if len(rendered_html) > _MAX_RENDERED_HTML_CHARS:
        return []
    soup = BeautifulSoup(rendered_html, "html.parser")
    evidence: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    json_ld_scripts_seen = 0
    for script in soup.find_all("script"):
        script_type = str(script.get("type") or "").split(";", 1)[0].strip().casefold()
        if script_type != "application/ld+json":
            continue
        json_ld_scripts_seen += 1
        if json_ld_scripts_seen > _MAX_JSON_LD_SCRIPTS:
            break
        script_text = script.string if script.string is not None else script.get_text("", strip=True)
        serialized = str(script_text or "").strip()
        if len(serialized) > _MAX_JSON_LD_SCRIPT_CHARS:
            continue
        try:
            payload = json.loads(serialized)
        except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
            continue
        for product in _iter_product_objects(payload):
            item = _build_product_evidence(product, base_url)
            if not item:
                continue
            identity = (item.get("sku", ""), item.get("url", ""), item.get("name", ""))
            if identity in seen:
                continue
            seen.add(identity)
            evidence.append(item)
            if len(evidence) >= evidence_limit:
                return evidence
    return evidence


def structured_product_evidence_for_result(
    page_html: str,
    *,
    base_url: str,
    blocked: bool,
) -> list[dict[str, str]]:
    """Keep structured evidence empty on blocked/manual-challenge results."""

    if blocked:
        return []
    return extract_structured_product_evidence(page_html, base_url=base_url)


def _iter_product_objects(payload: Any):
    stack: list[Any] = [payload]
    visited = 0
    while stack and visited < _MAX_VISITED_NODES:
        current = stack.pop()
        visited += 1
        if isinstance(current, dict):
            if _has_product_type(current.get("@type")):
                yield current
            stack.extend(reversed(list(current.values())))
        elif isinstance(current, list):
            stack.extend(reversed(current))


def _has_product_type(value: Any) -> bool:
    if isinstance(value, str):
        return value.casefold() == "product" or value.casefold().endswith("/product")
    if isinstance(value, list):
        return any(
            item.casefold() == "product" or item.casefold().endswith("/product")
            for item in value
            if isinstance(item, str)
        )
    return False


def _build_product_evidence(product: dict[str, Any], base_url: str) -> dict[str, str]:
    name = _clean_evidence_text(product.get("name"), 300)
    if not name:
        return {}
    item: dict[str, str] = {"name": name}
    _add_if_present(item, "sku", _clean_evidence_text(product.get("sku"), 120))
    _add_if_present(item, "brand", _brand_name(product.get("brand")))

    offer = _first_offer(product.get("offers"))
    if offer:
        _add_if_present(item, "price", _price_text(offer.get("price")))
        _add_if_present(item, "price_currency", _clean_evidence_text(offer.get("priceCurrency"), 12))
        _add_if_present(item, "availability", _availability_text(offer.get("availability")))
        raw_url = offer.get("url") or product.get("url")
    else:
        raw_url = product.get("url")
    _add_if_present(item, "url", _safe_product_url(raw_url, base_url))
    item["source"] = "json_ld"
    return item


def _first_offer(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), None)
    return None


def _brand_name(value: Any) -> str:
    if isinstance(value, dict):
        return _clean_evidence_text(value.get("name"), 200)
    return _clean_evidence_text(value, 200)


def _price_text(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    if isinstance(value, (int, float, str)):
        return _clean_evidence_text(str(value), 80)
    return ""


def _availability_text(value: Any) -> str:
    text = _clean_evidence_text(value, 160)
    if not text:
        return ""
    return text.rstrip("/").rsplit("/", 1)[-1][:80]


def _safe_product_url(value: Any, base_url: str) -> str:
    text = _clean_text(value, 2_000)
    if not text:
        return ""
    try:
        joined = urljoin(base_url, text)
        parsed = urlsplit(joined)
    except ValueError:
        return ""
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return ""
    if parsed.username is not None or parsed.password is not None:
        return ""
    safe_query: list[tuple[str, str]] = []
    for key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
        decoded_key = key
        for _ in range(4):
            next_key = unquote(decoded_key)
            if next_key == decoded_key:
                break
            decoded_key = next_key
        lowered_key = decoded_key.casefold()
        unresolved_key_encoding = "%" in decoded_key or "%25" in key.casefold()
        nested_value_encoding = "%25" in query_value.casefold()
        decoded_value = query_value
        for _ in range(4):
            next_value = unquote(decoded_value)
            if next_value == decoded_value:
                break
            decoded_value = next_value
        if (
            unresolved_key_encoding
            or nested_value_encoding
            or any(marker in lowered_key for marker in SENSITIVE_QUERY_KEYS)
            or _SENSITIVE_ASSIGNMENT_RE.search(decoded_value)
        ):
            safe_query.append((key, "***"))
        else:
            safe_query.append((key, query_value))
    sanitized = sanitize_diagnostic_url(
        urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(safe_query), "")),
        max_length=420,
    )
    try:
        sanitized_parts = urlsplit(sanitized)
    except ValueError:
        return ""
    return urlunsplit(
        (
            sanitized_parts.scheme,
            sanitized_parts.netloc,
            sanitized_parts.path,
            sanitized_parts.query,
            "",
        )
    )


def _clean_text(value: Any, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return ""
    return " ".join(value.split())[:max_length]


def _clean_evidence_text(value: Any, max_length: int) -> str:
    text = _clean_text(value, max_length)
    if not text:
        return ""
    if "%25" in text.casefold():
        return ""
    decoded = text
    for _ in range(4):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    if _SENSITIVE_ASSIGNMENT_RE.search(decoded):
        return ""
    return text


def _add_if_present(item: dict[str, str], key: str, value: str) -> None:
    if value:
        item[key] = value
