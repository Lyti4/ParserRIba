"""Build API-first product candidates from safe interception events."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from utils.api_first_value_helpers import (
    API_FIRST_FILTER_MODE,
    LINK_EVIDENCE_KEYS,
    PRODUCT_AVAILABILITY_KEYS,
    PRODUCT_ID_KEYS,
    PRODUCT_IMAGE_KEYS,
    PRODUCT_LINK_KEYS,
    PRODUCT_MAPPER_REQUIRED_FIELDS,
    PRODUCT_NAME_KEYS,
    PRODUCT_PRICE_KEYS,
    dedupe_key as build_dedupe_key,
    first_availability,
    first_present_key,
    first_price,
    first_string,
)


@dataclass(frozen=True)
class ApiProductCandidate:
    """A normalized product candidate extracted from intercepted API samples."""

    source_id: str
    name: str
    price: float | None
    image: str
    link: str
    availability: bool | None
    source_url: str
    dedupe_key: str
    ready_for_product_model: bool
    missing_fields: tuple[str, ...]
    raw_keys: tuple[str, ...]
    field_sources: dict[str, str]

    def as_report_dict(self) -> dict[str, Any]:
        """Return a JSON-safe report shape."""
        data = asdict(self)
        data["missing_fields"] = list(self.missing_fields)
        data["raw_keys"] = list(self.raw_keys)
        return data


def extract_api_product_candidates(
    events: list[dict[str, Any]],
    *,
    limit: int = 50,
) -> list[ApiProductCandidate]:
    """Extract deduplicated product candidates from interception events."""
    products: list[ApiProductCandidate] = []
    seen: set[str] = set()
    for event in events:
        source_url = str(event.get("url") or "")
        if not _is_product_event(source_url):
            continue
        for sample in event.get("sample_products") or []:
            if not isinstance(sample, dict):
                continue
            candidate = build_api_product_candidate(sample, source_url=source_url)
            if candidate.dedupe_key in seen:
                continue
            seen.add(candidate.dedupe_key)
            products.append(candidate)
            if len(products) >= limit:
                return products
    return products


def summarize_api_first_candidates(
    events: list[dict[str, Any]],
    dom_links_by_id: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Summarize API-first extraction readiness for reports."""
    candidates = extract_api_product_candidates(events)
    candidates = _apply_dom_link_enrichment(candidates, dom_links_by_id or {})
    source_filter = _source_filter_summary(events)
    ready = [item for item in candidates if item.ready_for_product_model]
    missing_counts: dict[str, int] = {}
    for item in candidates:
        for field in item.missing_fields:
            missing_counts[field] = missing_counts.get(field, 0) + 1
    return {
        "candidate_count": len(candidates),
        "ready_count": len(ready),
        "missing_field_counts": missing_counts,
        "source_filter": source_filter,
        "field_coverage": _field_coverage(candidates),
        "mapper_readiness": _mapper_readiness(candidates),
        "link_evidence": _link_evidence_summary(events),
        "samples": [item.as_report_dict() for item in candidates[:10]],
    }


def build_api_product_candidate(sample: dict[str, Any], *, source_url: str) -> ApiProductCandidate:
    """Normalize one intercepted sample into a stable candidate shape."""
    source_id = first_string(sample, PRODUCT_ID_KEYS)
    name = first_string(sample, PRODUCT_NAME_KEYS)
    image = first_string(sample, PRODUCT_IMAGE_KEYS)
    link = first_string(sample, PRODUCT_LINK_KEYS)
    price = first_price(sample, PRODUCT_PRICE_KEYS)
    availability = first_availability(sample, PRODUCT_AVAILABILITY_KEYS)
    field_sources = _candidate_field_sources(sample)
    missing = _missing_fields(name=name, price=price, link=link)
    candidate_dedupe_key = build_dedupe_key(source_id=source_id, name=name, link=link)
    raw_keys = tuple(str(key) for key in sample.get("keys") or sorted(sample))
    return ApiProductCandidate(
        source_id=source_id,
        name=name,
        price=price,
        image=image,
        link=link,
        availability=availability,
        source_url=source_url,
        dedupe_key=candidate_dedupe_key,
        ready_for_product_model=not missing,
        missing_fields=missing,
        raw_keys=raw_keys[:30],
        field_sources=field_sources,
    )


def _candidate_field_sources(sample: dict[str, Any]) -> dict[str, str]:
    preserved = _preserve_raw_field_sources(sample)
    if preserved:
        return preserved
    field_sources = {
        "source_id": first_present_key(sample, PRODUCT_ID_KEYS),
        "name": first_present_key(sample, PRODUCT_NAME_KEYS),
        "price": first_present_key(sample, PRODUCT_PRICE_KEYS),
        "image": first_present_key(sample, PRODUCT_IMAGE_KEYS),
        "link": first_present_key(sample, PRODUCT_LINK_KEYS),
        "availability": first_present_key(sample, PRODUCT_AVAILABILITY_KEYS),
    }
    return {key: value for key, value in field_sources.items() if value}


def _preserve_raw_field_sources(sample: dict[str, Any]) -> dict[str, str]:
    raw_sources = sample.get("field_sources")
    if not isinstance(raw_sources, dict):
        return {}
    preserved: dict[str, str] = {}
    source_id = raw_sources.get("source_id") or raw_sources.get("id")
    if isinstance(source_id, str) and source_id:
        preserved["source_id"] = source_id
    for field in ("name", "price", "image", "link", "availability"):
        value = raw_sources.get(field)
        if isinstance(value, str) and value:
            preserved[field] = value
    return preserved


def _missing_fields(*, name: str, price: float | None, link: str) -> tuple[str, ...]:
    missing: list[str] = []
    if not name:
        missing.append("name")
    if price is None:
        missing.append("price")
    if not link:
        missing.append("link")
    return tuple(missing)


def _field_coverage(candidates: list[ApiProductCandidate]) -> dict[str, int]:
    return {
        "source_id": sum(1 for item in candidates if item.source_id),
        "name": sum(1 for item in candidates if item.name),
        "price": sum(1 for item in candidates if item.price is not None),
        "image": sum(1 for item in candidates if item.image),
        "link": sum(1 for item in candidates if item.link),
        "availability": sum(1 for item in candidates if item.availability is not None),
    }


def _mapper_readiness(candidates: list[ApiProductCandidate]) -> dict[str, Any]:
    coverage = _field_coverage(candidates)
    missing = [field for field in PRODUCT_MAPPER_REQUIRED_FIELDS if coverage.get(field, 0) == 0]
    return {
        "ready": bool(candidates) and not missing,
        "required_fields": list(PRODUCT_MAPPER_REQUIRED_FIELDS),
        "missing_fields": missing,
    }


def _source_filter_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    eligible_events = 0
    excluded_urls: list[str] = []
    excluded_events = 0
    for event in events:
        sample_products = event.get("sample_products") or []
        if not sample_products:
            continue
        source_url = str(event.get("url") or "")
        if _is_product_event(source_url):
            eligible_events += 1
            continue
        excluded_events += 1
        if source_url and len(excluded_urls) < 5:
            excluded_urls.append(source_url)
    return {
        "mode": API_FIRST_FILTER_MODE,
        "eligible_events_count": eligible_events,
        "excluded_events_count": excluded_events,
        "excluded_urls": excluded_urls,
    }


def _link_evidence_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    eligible_with_link = 0
    eligible_without_link = 0
    non_product_link_urls: list[str] = []
    non_product_link_keys: set[str] = set()
    for event in events:
        sample_products = event.get("sample_products") or []
        if not sample_products:
            continue
        source_url = str(event.get("url") or "")
        observed_link_keys = _observed_link_keys(event)
        has_link_key = bool(event.get("has_link_key")) or bool(observed_link_keys)
        if _is_product_event(source_url):
            if has_link_key:
                eligible_with_link += 1
            else:
                eligible_without_link += 1
            continue
        if not has_link_key:
            continue
        if source_url and len(non_product_link_urls) < 5:
            non_product_link_urls.append(source_url)
        non_product_link_keys.update(observed_link_keys)
    return {
        "products_have_link_key": eligible_with_link > 0,
        "eligible_product_events_with_link_key": eligible_with_link,
        "eligible_product_events_without_link_key": eligible_without_link,
        "non_product_link_urls": non_product_link_urls,
        "non_product_link_keys": sorted(non_product_link_keys),
    }


def _apply_dom_link_enrichment(
    candidates: list[ApiProductCandidate],
    dom_links_by_id: dict[str, str],
) -> list[ApiProductCandidate]:
    if not dom_links_by_id:
        return candidates
    enriched: list[ApiProductCandidate] = []
    for item in candidates:
        dom_link = dom_links_by_id.get(item.source_id, "").strip()
        if not dom_link or item.link:
            enriched.append(item)
            continue
        field_sources = dict(item.field_sources)
        field_sources["link"] = "dom_product_href"
        missing = tuple(field for field in item.missing_fields if field != "link")
        enriched.append(
            ApiProductCandidate(
                source_id=item.source_id,
                name=item.name,
                price=item.price,
                image=item.image,
                link=dom_link,
                availability=item.availability,
                source_url=item.source_url,
                dedupe_key=item.dedupe_key,
                ready_for_product_model=not missing,
                missing_fields=missing,
                raw_keys=item.raw_keys,
                field_sources=field_sources,
            )
        )
    return enriched


def _is_product_event(source_url: str) -> bool:
    return "/products" in source_url.lower()


def _observed_link_keys(event: dict[str, Any]) -> list[str]:
    observed: set[str] = set()
    top_keys = event.get("schema_hints", {}).get("top_keys") or []
    for key in top_keys:
        key_str = str(key)
        if key_str in LINK_EVIDENCE_KEYS:
            observed.add(key_str)
    for product in event.get("sample_products") or []:
        if not isinstance(product, dict):
            continue
        for key in product.get("keys") or []:
            key_str = str(key)
            if key_str in LINK_EVIDENCE_KEYS:
                observed.add(key_str)
    return sorted(observed)


