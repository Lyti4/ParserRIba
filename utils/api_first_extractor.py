"""Build API-first product candidates from safe interception events."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ApiProductCandidate:
    """A normalized product candidate extracted from intercepted API samples."""

    source_id: str
    name: str
    price: float | None
    image: str
    link: str
    source_url: str
    dedupe_key: str
    ready_for_product_model: bool
    missing_fields: tuple[str, ...]
    raw_keys: tuple[str, ...]

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


def summarize_api_first_candidates(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize API-first extraction readiness for reports."""
    candidates = extract_api_product_candidates(events)
    ready = [item for item in candidates if item.ready_for_product_model]
    missing_counts: dict[str, int] = {}
    for item in candidates:
        for field in item.missing_fields:
            missing_counts[field] = missing_counts.get(field, 0) + 1
    return {
        "candidate_count": len(candidates),
        "ready_count": len(ready),
        "missing_field_counts": missing_counts,
        "samples": [item.as_report_dict() for item in candidates[:10]],
    }


def build_api_product_candidate(sample: dict[str, Any], *, source_url: str) -> ApiProductCandidate:
    """Normalize one intercepted sample into a stable candidate shape."""
    source_id = _string_value(sample, "id")
    name = _string_value(sample, "name")
    image = _first_string(sample, ("image", "image_url", "imageUrl"))
    link = _first_string(sample, ("link", "url", "href", "productUrl", "webUrl"))
    price = _extract_price(sample.get("price"))
    missing = _missing_fields(name=name, price=price, link=link)
    dedupe_key = _dedupe_key(source_id=source_id, name=name, link=link)
    raw_keys = tuple(str(key) for key in sample.get("keys") or sorted(sample))
    return ApiProductCandidate(
        source_id=source_id,
        name=name,
        price=price,
        image=image,
        link=link,
        source_url=source_url,
        dedupe_key=dedupe_key,
        ready_for_product_model=not missing,
        missing_fields=missing,
        raw_keys=raw_keys[:30],
    )


def _missing_fields(*, name: str, price: float | None, link: str) -> tuple[str, ...]:
    missing: list[str] = []
    if not name:
        missing.append("name")
    if price is None:
        missing.append("price")
    if not link:
        missing.append("link")
    return tuple(missing)


def _dedupe_key(*, source_id: str, name: str, link: str) -> str:
    stable = source_id or link or _normalize_name(name)
    if not stable:
        stable = "unknown"
    digest = hashlib.sha1(stable.encode("utf-8", errors="ignore")).hexdigest()
    return digest[:16]


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _string_value(sample: dict[str, Any], key: str) -> str:
    value = sample.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _first_string(sample: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = sample.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value:
            nested = _first_nested_url(value)
            if nested:
                return nested
        if isinstance(value, dict):
            nested = _first_nested_url(value)
            if nested:
                return nested
    return ""


def _first_nested_url(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for nested in value.values():
            found = _first_nested_url(nested)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _first_nested_url(item)
            if found:
                return found
    return ""


def _extract_price(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", normalized)
        if match:
            return float(match.group(0))
        return None
    if isinstance(value, dict):
        for key in ("current", "regular", "value", "price", "amount"):
            if key in value:
                price = _extract_price(value[key])
                if price is not None:
                    return price
        for nested in value.values():
            price = _extract_price(nested)
            if price is not None:
                return price
    if isinstance(value, list):
        for item in value:
            price = _extract_price(item)
            if price is not None:
                return price
    return None
