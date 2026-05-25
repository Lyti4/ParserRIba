"""Payload decoding and classification for catalog discovery intelligence."""

from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.parse import urljoin

from pydantic import BaseModel, Field

from models.catalog_discovery import CategoryEvidence, PayloadType, RouteHint

PROTECTION_MARKERS = ("captcha", "cloudflare", "datadome", "perimeterx", "servicepipe", "turnstile")
CATALOG_ROUTE_MARKERS = ("/catalog", "/category", "/categories")
LABEL_KEYS = ("name", "title", "label", "caption")
URL_KEYS = ("url", "href", "path", "slug")
PRODUCT_KEYS = ("sku", "plu", "productid", "product_id", "price")
PAGINATION_KEYS = ("hasnextpage", "endcursor", "nextpage", "offset", "limit", "page")
GRAPHQL_HINT_KEYS = ("edges", "nodes", "node", "children")


class PayloadClassification(BaseModel):
    """Typed result of one decoded response or embedded payload."""

    payload_type: PayloadType
    confidence: float = 0.0
    categories: list[CategoryEvidence] = Field(default_factory=list)
    route_hints: list[RouteHint] = Field(default_factory=list)
    protection_signals: list[str] = Field(default_factory=list)
    decoded_variants: int = 0


def classify_payload(*, base_url: str, content_type: str = "", body_text: str = "") -> PayloadClassification:
    """Decode safe payload forms and classify catalog/listing/protection signals."""
    body = str(body_text or "")
    lowered_meta = f"{base_url} {content_type}".casefold()
    lowered_body = body.casefold()
    protection = _detect_protection(lowered_body)
    if protection:
        return PayloadClassification(
            payload_type="protection_payload",
            confidence=0.95,
            protection_signals=protection,
            route_hints=[RouteHint(kind="protection_payload", value=base_url, source="protection_signal")],
            decoded_variants=1,
        )

    decoded = _decode_payload_variants(body)
    categories: list[CategoryEvidence] = []
    route_hints: list[RouteHint] = []
    product_score = 0
    listing_score = 0
    pagination_score = 0
    graph_score = 0
    for payload in decoded:
        categories.extend(_extract_categories(payload, base_url))
        product_score += _count_keys(payload, PRODUCT_KEYS)
        pagination_score += _count_keys(payload, PAGINATION_KEYS)
        graph_score += _count_keys(payload, GRAPHQL_HINT_KEYS)
        listing_score += _count_product_like_lists(payload)

    categories = _dedup_categories(categories)
    if categories:
        if graph_score:
            route_hints.append(RouteHint(kind="graphql_tree", value=base_url, source="network_response"))
        return PayloadClassification(
            payload_type="catalog_tree_payload",
            confidence=min(0.98, 0.6 + len(categories) * 0.04 + graph_score * 0.03),
            categories=categories,
            route_hints=route_hints or [RouteHint(kind="category_payload", value=base_url, source="network_response")],
            decoded_variants=len(decoded),
        )
    if listing_score or ("listing" in lowered_meta and product_score):
        return PayloadClassification(
            payload_type="listing_payload",
            confidence=0.75,
            route_hints=[RouteHint(kind="listing_payload", value=base_url, source="network_response")],
            decoded_variants=len(decoded),
        )
    if product_score:
        return PayloadClassification(
            payload_type="product_payload",
            confidence=0.7,
            route_hints=[RouteHint(kind="product_payload", value=base_url, source="network_response")],
            decoded_variants=len(decoded),
        )
    if pagination_score:
        return PayloadClassification(
            payload_type="pagination_payload",
            confidence=0.65,
            route_hints=[RouteHint(kind="pagination_payload", value=base_url, source="network_response")],
            decoded_variants=len(decoded),
        )
    return PayloadClassification(payload_type="noise_payload", confidence=0.1, decoded_variants=len(decoded))


def _decode_payload_variants(body_text: str) -> list[Any]:
    variants: list[Any] = []
    for candidate in _candidate_strings(body_text):
        payload = _loads_json(candidate)
        if payload is not None:
            variants.append(payload)
        for encoded in _extract_encoded_segments(candidate):
            decoded = _loads_json(encoded)
            if decoded is not None:
                variants.append(decoded)
    return variants


def _candidate_strings(body_text: str) -> list[str]:
    text = str(body_text or "").strip()
    candidates = [text]
    if text.startswith('"') and text.endswith('"'):
        unescaped = _loads_json(text)
        if isinstance(unescaped, str):
            candidates.append(unescaped)
    candidates.extend(re.findall(r"<script[^>]*>(.*?)</script>", text, flags=re.IGNORECASE | re.DOTALL))
    candidates.extend(re.findall(r"({[^{}]*(?:catalog|category|children|edges|nodes)[\s\S]*?})", text, flags=re.IGNORECASE))
    return [item.strip() for item in candidates if item and item.strip()]


def _extract_encoded_segments(text: str) -> list[str]:
    decoded: list[str] = []
    for token in re.findall(r"[A-Za-z0-9_-]{16,}(?:\.[A-Za-z0-9_-]{16,}){0,2}", text):
        parts = token.split(".")
        for part in parts[1:2] if len(parts) == 3 else parts:
            value = _base64url_decode(part)
            if value:
                decoded.append(value)
    return decoded


def _loads_json(text: str) -> Any | None:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _base64url_decode(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        return ""
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError:
        return ""
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return stripped
    return ""


def _extract_categories(payload: Any, base_url: str) -> list[CategoryEvidence]:
    result: list[CategoryEvidence] = []
    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            url = _category_url(current, base_url)
            if url:
                result.append(CategoryEvidence(name=_category_label(current, url), url=url, source="network_response"))
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return result


def _category_url(payload: dict[str, Any], base_url: str) -> str:
    for key in URL_KEYS:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        url = urljoin(base_url, value.strip())
        if any(marker in url.casefold() for marker in CATALOG_ROUTE_MARKERS):
            return url
    return ""


def _category_label(payload: dict[str, Any], url: str) -> str:
    for key in LABEL_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return url.rstrip("/").split("/")[-1].replace("-", " ").title() or "Каталог"


def _count_keys(payload: Any, keys: tuple[str, ...]) -> int:
    count = 0
    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            lowered_keys = {str(key).casefold() for key in current}
            count += sum(1 for key in keys if key in lowered_keys)
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return count


def _count_product_like_lists(payload: Any) -> int:
    count = 0
    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, list) and len(current) >= 2:
            product_like = 0
            for item in current[:8]:
                if isinstance(item, dict) and _count_keys(item, PRODUCT_KEYS) >= 2:
                    product_like += 1
            if product_like >= 2:
                count += product_like
        if isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return count


def _detect_protection(lowered_body: str) -> list[str]:
    return [f"protection:{marker}" for marker in PROTECTION_MARKERS if marker in lowered_body]


def _dedup_categories(items: list[CategoryEvidence]) -> list[CategoryEvidence]:
    seen: set[str] = set()
    result: list[CategoryEvidence] = []
    for item in items:
        if item.url in seen:
            continue
        seen.add(item.url)
        result.append(item)
    return result
