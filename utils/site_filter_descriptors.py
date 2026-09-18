"""Descriptor-level normalization for site-provided filter facets."""

from __future__ import annotations

from typing import Any

FacetDescriptor = dict[str, Any]

FIELD_ALIASES = {
    "brand": "brand",
    "brands": "brand",
    "бренд": "brand",
    "бренды": "brand",
    "Р±СЂРµРЅРґ": "brand",
    "Р±СЂРµРЅРґС‹": "brand",
    "producer": "producer",
    "manufacturer": "producer",
    "vendor": "producer",
    "производитель": "producer",
    "поставщик": "producer",
    "price": "price",
    "цена": "price",
    "цена, ₽": "price",
    "С†РµРЅР°": "price",
    "С†РµРЅР°, в‚Ѕ": "price",
    "special_offers": "special_offers",
    "specialoffers": "special_offers",
    "discount": "special_offers",
    "sale": "special_offers",
    "со скидкой": "special_offers",
    "скидка": "special_offers",
    "СЃРѕ СЃРєРёРґРєРѕР№": "special_offers",
    "СЃРєРёРґРєР°": "special_offers",
    "country": "country",
    "страна": "country",
    "страна происхождения": "country",
    "weight": "weight",
    "вес": "weight",
    "РІРµСЃ": "weight",
    "volume": "volume",
    "объём": "volume",
    "объем": "volume",
    "packaging": "packaging",
    "упаковка": "packaging",
    "СѓРїР°РєРѕРІРєР°": "packaging",
    "fat": "fat",
    "fat_percent": "fat",
    "жирность": "fat",
    "жир": "fat",
    "Р¶РёСЂРЅРѕСЃС‚СЊ": "fat",
    "Р¶РёСЂ": "fat",
}

FIELD_TITLES = {
    "brand": "Бренд",
    "producer": "Производитель",
    "price": "Цена, ₽",
    "special_offers": "Со скидкой",
    "country": "Страна",
    "weight": "Вес",
    "volume": "Объём",
    "packaging": "Упаковка",
    "fat": "Жирность",
}

NOISE_KEYS = {
    "name",
    "title",
    "label",
    "field",
    "field_name",
    "fieldname",
    "filter_type",
    "filtertype",
    "type",
    "kind",
    "range_min_val",
    "rangeminval",
    "range_max_val",
    "rangemaxval",
    "min",
    "max",
    "values",
    "options",
    "items",
    "list_values",
    "listvalues",
}

FACET_CONTAINER_KEYS = ("filters", "facets", "facetFilters", "filterGroups", "aggregations")
TITLE_KEYS = ("name", "title", "label")
FIELD_KEYS = ("field_name", "fieldName", "field", "code", "key", "slug")
TYPE_KEYS = ("filter_type", "filterType", "type", "kind")
OPTION_KEYS = ("list_values", "listValues", "values", "options", "items", "buckets")
MIN_KEYS = ("range_min_val", "rangeMinVal", "min", "minValue", "from")
MAX_KEYS = ("range_max_val", "rangeMaxVal", "max", "maxValue", "to")
YES_OPTION = "Да"


def normalize_filter_descriptors(raw: Any, *, source: str = "site_api") -> list[FacetDescriptor]:
    """Normalize raw DOM/API filter data into structured descriptors."""
    return _merge_descriptors(_descriptors_from_value(raw, source=source))


def extract_filter_descriptors_from_payload(payload: Any) -> list[FacetDescriptor]:
    """Extract common API facet payloads into structured descriptors."""
    descriptors: list[FacetDescriptor] = []
    for item in _iter_dicts(payload):
        for key in FACET_CONTAINER_KEYS:
            descriptors.extend(_descriptors_from_value(item.get(key), source="site_api"))
    return _merge_descriptors(descriptors)


def descriptors_to_option_map(descriptors: list[FacetDescriptor]) -> dict[str, list[str]]:
    """Convert structured descriptors to the launcher-compatible option map."""
    result: dict[str, list[str]] = {}
    for item in descriptors:
        if item.get("kind") == "range":
            continue
        field = str(item.get("field") or "").strip()
        options = [str(option) for option in item.get("options", []) if _clean_text(option)]
        if field and options:
            result[field] = list(dict.fromkeys([*result.get(field, []), *options]))
    return result


def _descriptors_from_value(value: Any, *, source: str) -> list[FacetDescriptor]:
    if isinstance(value, list):
        result: list[FacetDescriptor] = []
        for item in value:
            result.extend(_descriptors_from_value(item, source=source))
        return result
    if not isinstance(value, dict):
        return []
    descriptor = _descriptor_from_facet_dict(value, source=source)
    if descriptor is not None:
        return [descriptor]
    result = []
    for raw_title, raw_options in value.items():
        title = _clean_text(raw_title)
        if not title or _is_noise_key(title):
            continue
        options = _option_values(raw_options)
        if options:
            field = _field_key(title)
            result.append(_descriptor(field, _field_title(field, title), "list", options, source))
        else:
            result.extend(_descriptors_from_value(raw_options, source=source))
    return result


def _descriptor_from_facet_dict(item: dict[str, Any], *, source: str) -> FacetDescriptor | None:
    title = _first_text(item, TITLE_KEYS)
    field = _field_key(_first_text(item, FIELD_KEYS) or title)
    kind = _filter_kind(_first_text(item, TYPE_KEYS), item, field)
    options = _structured_options(item)
    min_value = _first_number(item, MIN_KEYS)
    max_value = _first_number(item, MAX_KEYS)
    if kind == "toggle" and not options:
        options = [YES_OPTION]
    if kind == "range" and (min_value is not None or max_value is not None):
        return _descriptor(field, _field_title(field, title), kind, [], source, min_value, max_value)
    if options:
        return _descriptor(field, _field_title(field, title), kind, options, source, min_value, max_value)
    return None


def _descriptor(
    field: str,
    title: str,
    kind: str,
    options: list[str],
    source: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> FacetDescriptor:
    return {
        "field": field,
        "title": title,
        "kind": kind,
        "options": list(dict.fromkeys(options)),
        "min": min_value,
        "max": max_value,
        "source": source,
        "mapped": bool(field and not _is_noise_key(field)),
    }


def _structured_options(item: dict[str, Any]) -> list[str]:
    for key in OPTION_KEYS:
        options = _option_values(item.get(key))
        if options:
            return options
    return []


def _option_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        label = _first_text(value, ("name", "title", "label", "value"))
        if label:
            return [label]
        result: list[str] = []
        for nested in value.values():
            result.extend(_option_values(nested))
        return list(dict.fromkeys(result))
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_option_values(item))
        return list(dict.fromkeys(result))
    label = _clean_text(value)
    return [label] if label else []


def _merge_descriptors(descriptors: list[FacetDescriptor]) -> list[FacetDescriptor]:
    merged: dict[tuple[str, str], FacetDescriptor] = {}
    for item in descriptors:
        field = str(item.get("field") or "").strip()
        kind = str(item.get("kind") or "list").strip()
        if not field or _is_noise_key(field):
            continue
        target = merged.setdefault((field, kind), dict(item))
        target["options"] = list(dict.fromkeys([*target.get("options", []), *item.get("options", [])]))
        target["min"] = _min_number(target.get("min"), item.get("min"))
        target["max"] = _max_number(target.get("max"), item.get("max"))
    return list(merged.values())


def _iter_dicts(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if isinstance(value, dict):
        result.append(value)
        for nested in value.values():
            result.extend(_iter_dicts(nested))
    elif isinstance(value, list):
        for nested in value:
            result.extend(_iter_dicts(nested))
    return result


def _first_text(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _clean_text(item.get(key))
        if text:
            return text
    return ""


def _first_number(item: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = _number_value(item.get(key))
        if value is not None:
            return value
    return None


def _number_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _min_number(left: Any, right: Any) -> float | None:
    values = [value for value in (_number_value(left), _number_value(right)) if value is not None]
    return min(values) if values else None


def _max_number(left: Any, right: Any) -> float | None:
    values = [value for value in (_number_value(left), _number_value(right)) if value is not None]
    return max(values) if values else None


def _filter_kind(raw_kind: str, item: dict[str, Any], field: str) -> str:
    normalized = raw_kind.casefold().replace("-", "_").replace(" ", "_")
    if "range" in normalized or _first_number(item, MIN_KEYS) is not None or _first_number(item, MAX_KEYS) is not None:
        return "range"
    if "toggle" in normalized or field == "special_offers":
        return "toggle"
    return "list"


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    return " ".join(text.split()) if text and len(text) <= 80 else ""


def _field_key(title: str) -> str:
    text = _clean_text(title)
    return FIELD_ALIASES.get(text.casefold(), text)


def _field_title(field: str, fallback: str) -> str:
    return FIELD_TITLES.get(field) or _clean_text(fallback) or field


def _is_noise_key(value: str) -> bool:
    return value.casefold().replace("-", "_").replace(" ", "_") in NOISE_KEYS
