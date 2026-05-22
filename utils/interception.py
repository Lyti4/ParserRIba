"""Store-neutral helpers for safe API/network interception diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from utils.interception_payload_helpers import (
    payload_has_empty_products,
    payload_preview,
    safe_json_loads,
    sanitize_diagnostic_url,
)
from utils.interception_profiles import GENERIC_INTERCEPTION_PROFILE, InterceptionProfile
from utils.interception_product_helpers import (
    PRODUCT_AVAILABILITY_KEYS,
    PRODUCT_ID_KEYS,
    PRODUCT_IMAGE_KEYS,
    PRODUCT_LINK_KEYS,
    PRODUCT_NAME_KEYS,
    PRODUCT_PRICE_KEYS,
    build_product_candidate,
    extract_product_candidates,
    field_sources as _field_sources,
    first_nested_text as _first_nested_text,
    first_nested_value as _first_nested_value,
    first_present_key as _first_present_key,
    first_value as _first_value,
    has_any as _has_any,
    infer_schema_hints,
    iter_dicts,
)
JSON_CONTENT_MARKERS = ("json", "javascript")


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


def _is_replay_candidate(event: InterceptionEvent) -> bool:
    return (
        event.method.upper() in {"GET", ""}
        and event.status == 200
        and event.route_type == "product_api"
        and event.payload_kind == "json"
        and not event.error
    )


def _event_sample(event: dict[str, Any]) -> dict[str, Any]:
    sample_products = event.get("sample_products") or []
    return {
        "method": event.get("method", ""),
        "status": event.get("status"),
        "url": event.get("url", ""),
        "candidate_product_count": event.get("candidate_product_count", 0),
        "schema_hints": event.get("schema_hints", {}),
        "sample_products": [compact_sample_product(item) for item in sample_products[:2] if isinstance(item, dict)],
    }


def compact_sample_product(sample: dict[str, Any]) -> dict[str, Any]:
    """Return a report-safe compact product sample."""
    compact = {
        "id": sample.get("id", ""),
        "name": sample.get("name", ""),
        "price": sample.get("price"),
        "image": sample.get("image", ""),
        "link": sample.get("link", ""),
        "availability": sample.get("availability"),
        "field_sources": sample.get("field_sources", {}),
        "keys": sample.get("keys", []),
    }
    return {key: value for key, value in compact.items() if value not in ("", None, [], {})}
