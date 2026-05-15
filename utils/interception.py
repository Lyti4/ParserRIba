"""Store-neutral helpers for safe API/network interception diagnostics."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from utils.interception_profiles import GENERIC_INTERCEPTION_PROFILE, InterceptionProfile

PRODUCT_NAME_KEYS = {"name", "title"}
PRODUCT_ID_KEYS = {"id", "plu", "product_id", "productId", "sku", "slug"}
PRODUCT_PRICE_KEYS = {"price", "regular_price", "current_price", "price_current", "prices"}
PRODUCT_IMAGE_KEYS = {"image", "image_url", "imageUrl", "images", "picture", "pictures"}
PRODUCT_LINK_KEYS = {"url", "link", "href", "productUrl", "webUrl"}
PRODUCT_AVAILABILITY_KEYS = {"available", "availability", "in_stock", "inStock", "isAvailable", "stock"}
JSON_CONTENT_MARKERS = ("json", "javascript")
SENSITIVE_QUERY_KEYS = tuple(
    "access auth authorization captcha cookie email hcheck key oirut password phone refresh request_ secret session sid token".split()
)


@dataclass
class InterceptionEvent:
    """Safe structured network interception event."""

    method: str = ""
    status: int | None = None
    url: str = ""
    route_type: str = "unknown"
    content_type: str = ""
    response_size: int = 0
    payload_kind: str = "unknown"
    empty_products_payload: bool | None = None
    candidate_product_count: int = 0
    sample_products: list[dict[str, Any]] = field(default_factory=list)
    schema_hints: dict[str, Any] = field(default_factory=dict)
    payload_preview: str = ""
    replay_candidate: bool = False
    error: str = ""

    def as_report_dict(self) -> dict[str, Any]:
        """Return compact report-safe dictionary."""
        return asdict(self)


def classify_route(
    url: str,
    content_type: str = "",
    profile: InterceptionProfile | None = None,
) -> str:
    """Classify a sanitized URL into a broad interception route type."""
    route_profile = profile or GENERIC_INTERCEPTION_PROFILE
    return route_profile.classify_route(url, content_type)


def build_interception_event(
    *,
    method: str,
    status: int | None,
    url: str,
    content_type: str = "",
    payload_text: str = "",
    error: str = "",
    profile: InterceptionProfile | None = None,
) -> InterceptionEvent:
    """Build one safe structured interception event from response data."""
    safe_url = sanitize_diagnostic_url(url, max_length=420)
    event = InterceptionEvent(
        method=method,
        status=status,
        url=safe_url,
        route_type=classify_route(safe_url, content_type, profile),
        content_type=content_type.split(";")[0] if content_type else "",
        response_size=len(payload_text.encode("utf-8", errors="ignore")) if payload_text else 0,
        error=error[:200],
    )
    if payload_text:
        event.payload_preview = payload_preview(payload_text, max_length=700)
        event.empty_products_payload = payload_has_empty_products(payload_text)
        payload = safe_json_loads(payload_text)
        if payload is None:
            event.payload_kind = "text"
        else:
            event.payload_kind = "json"
            event.sample_products = extract_product_candidates(payload)
            event.candidate_product_count = len(event.sample_products)
            event.schema_hints = infer_schema_hints(payload)
    event.replay_candidate = _is_replay_candidate(event)
    return event


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


def iter_dicts(value: Any) -> list[dict[str, Any]]:
    """Collect nested dictionaries from a JSON-like payload."""
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for item in value.values():
            found.extend(iter_dicts(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(iter_dicts(item))
    return found


def extract_product_candidates(payload: Any, limit: int = 10) -> list[dict[str, Any]]:
    """Extract likely product records from arbitrary catalog JSON."""
    candidates: list[dict[str, Any]] = []
    for item in iter_dicts(payload):
        keys = set(item)
        has_name = bool(keys & PRODUCT_NAME_KEYS)
        has_identity = bool(keys & PRODUCT_ID_KEYS)
        has_price = bool(keys & PRODUCT_PRICE_KEYS)
        if not has_name or not (has_identity or has_price):
            continue
        candidates.append(
            {
                "id": _first_value(item, PRODUCT_ID_KEYS),
                "name": _first_value(item, PRODUCT_NAME_KEYS),
                "price": _first_value(item, PRODUCT_PRICE_KEYS),
                "image": _first_value(item, PRODUCT_IMAGE_KEYS),
                "link": _first_value(item, PRODUCT_LINK_KEYS),
                "availability": _first_value(item, PRODUCT_AVAILABILITY_KEYS),
                "keys": sorted(str(key) for key in keys)[:25],
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def infer_schema_hints(payload: Any, limit: int = 20) -> dict[str, Any]:
    """Infer product-related keys found in a JSON payload."""
    key_counts: dict[str, int] = {}
    product_like = 0
    for item in iter_dicts(payload):
        keys = set(str(key) for key in item)
        for key in keys:
            key_counts[key] = key_counts.get(key, 0) + 1
        if keys & PRODUCT_NAME_KEYS and (keys & PRODUCT_ID_KEYS or keys & PRODUCT_PRICE_KEYS):
            product_like += 1
    return {
        "product_like_objects": product_like,
        "top_keys": sorted(key_counts, key=key_counts.get, reverse=True)[:limit],
        "has_name_key": any(key in key_counts for key in PRODUCT_NAME_KEYS),
        "has_price_key": any(key in key_counts for key in PRODUCT_PRICE_KEYS),
        "has_image_key": any(key in key_counts for key in PRODUCT_IMAGE_KEYS),
        "has_link_key": any(key in key_counts for key in PRODUCT_LINK_KEYS),
        "has_availability_key": any(key in key_counts for key in PRODUCT_AVAILABILITY_KEYS),
    }


def summarize_interception_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a compact interception summary for reports."""
    route_counts: dict[str, int] = {}
    replay_candidates: list[dict[str, Any]] = []
    schema_candidates: list[dict[str, Any]] = []
    for event in events:
        route = str(event.get("route_type") or "unknown")
        route_counts[route] = route_counts.get(route, 0) + 1
        if event.get("replay_candidate") and len(replay_candidates) < 10:
            replay_candidates.append(_event_sample(event))
        if event.get("candidate_product_count", 0) > 0 and len(schema_candidates) < 10:
            schema_candidates.append(_event_sample(event))
    return {
        "route_counts": route_counts,
        "replay_candidates": replay_candidates,
        "schema_candidates": schema_candidates,
    }


def _first_value(item: dict[str, Any], keys: set[str]) -> Any:
    for key in keys:
        if key in item:
            return item[key]
    return ""


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


def _is_replay_candidate(event: InterceptionEvent) -> bool:
    return (
        event.method.upper() in {"GET", ""}
        and event.status == 200
        and event.route_type == "product_api"
        and event.payload_kind == "json"
        and not event.error
    )


def _event_sample(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": event.get("method", ""),
        "status": event.get("status"),
        "url": event.get("url", ""),
        "candidate_product_count": event.get("candidate_product_count", 0),
        "schema_hints": event.get("schema_hints", {}),
    }
