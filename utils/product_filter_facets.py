"""Build product-derived filter facets without depending on launcher UI."""

from __future__ import annotations

from typing import Any

from utils.product_display_fields import product_alcohol_type_name
from utils.product_raw_fields import derive_fields_from_product_name

IGNORED_DYNAMIC_FILTER_FIELDS = {
    "field_name",
    "fieldname",
    "filter_type",
    "filtertype",
    "list_values",
    "listvalues",
    "range_min_val",
    "rangeminval",
    "range_max_val",
    "rangemaxval",
    "name",
    "title",
    "label",
    "type",
    "kind",
}


def build_found_filter_counts(products: list[Any]) -> dict[str, dict[str, int]]:
    """Build dynamic facets from extra raw product fields."""
    ignored = {
        "id",
        "image",
        "images",
        "link",
        "url",
        "product_link",
        "source_id",
        "field_sources",
        "categories",
        "description",
        "composition",
        "ingredients",
        "storage_conditions",
        "shelf_life",
        "supplier",
        "producer",
        "manufacturer",
        "vendor",
        "brand",
        "sugar_class",
        "color",
    }
    values_by_field: dict[str, list[str]] = {}
    for item in products:
        if not isinstance(item, dict):
            continue
        for field_name, value in raw_filter_data(item).items():
            key = str(field_name or "").strip()
            if not key or key in ignored:
                continue
            for target_key, text in iter_named_filter_values(key, value):
                if target_key in ignored:
                    continue
                values_by_field.setdefault(target_key, []).append(text)
    return {
        field_name: counts
        for field_name, values in sorted(values_by_field.items())
        if (counts := counted_values(values))
    }


def merge_filter_option_maps(*sources: Any) -> dict[str, Any]:
    """Merge dynamic filter option maps while preserving count maps when possible."""
    merged: dict[str, dict[str, int | None]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        for raw_field, raw_options in source.items():
            field = text_value(raw_field)
            if not field or is_ignored_dynamic_filter_field(field):
                continue
            target = merged.setdefault(field, {})
            for option, count in option_pairs(raw_options):
                target.setdefault(option, count)
    result: dict[str, Any] = {}
    for field, options in merged.items():
        if all(count is not None for count in options.values()):
            result[field] = {option: int(count or 0) for option, count in options.items()}
        else:
            result[field] = list(options)
    return result


def counted_values(values: Any) -> dict[str, int]:
    """Return sorted non-empty value counts."""
    counts: dict[str, int] = {}
    for value in values:
        rendered = text_value(value)
        if not rendered:
            continue
        counts[rendered] = counts.get(rendered, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def is_ignored_dynamic_filter_field(field_name: str) -> bool:
    """Return whether a site-provided facet key is UI metadata, not a filter."""
    normalized = field_name.casefold().replace("-", "_").replace(" ", "_")
    return normalized in IGNORED_DYNAMIC_FILTER_FIELDS


def option_pairs(raw_options: Any) -> list[tuple[str, int | None]]:
    """Normalize dynamic option payloads into label/count pairs."""
    if isinstance(raw_options, dict):
        result: list[tuple[str, int | None]] = []
        for raw_label, raw_count in raw_options.items():
            label = text_value(raw_label)
            if label:
                result.append((label, raw_count if isinstance(raw_count, int) else None))
        return result
    if isinstance(raw_options, list):
        return [(text_value(item), None) for item in raw_options if text_value(item)]
    label = text_value(raw_options)
    return [(label, None)] if label else []


def raw_filter_data(item: dict[str, Any]) -> dict[str, Any]:
    """Return raw fields plus safe fields derived from product display fields."""
    raw_data = item.get("raw_data")
    raw_dict = dict(raw_data) if isinstance(raw_data, dict) else {}
    for key, value in derive_fields_from_product_name(item.get("name")).items():
        raw_dict.setdefault(key, value)
    alcohol_type = product_alcohol_type_name(item)
    if alcohol_type:
        raw_dict["alcohol_type"] = alcohol_type
    return raw_dict


def iter_named_filter_values(field_name: str, value: Any) -> list[tuple[str, str]]:
    """Return filter field/value pairs, flattening attribute maps when useful."""
    if isinstance(value, dict):
        direct_values = iter_filter_values(value)
        nested_values = iter_nested_filter_values(value)
        if nested_values and not direct_values:
            return nested_values
        if is_attribute_container(field_name) and nested_values:
            return nested_values
        return [(field_name, text) for text in direct_values]
    return [(field_name, text) for text in iter_filter_values(value)]


def iter_filter_values(value: Any) -> list[str]:
    """Normalize scalar, list, or dict raw values into short filter labels."""
    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = filter_text_value(value)
        return [text] if text else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(iter_filter_values(item))
        return result
    if isinstance(value, dict):
        for key in ("name", "title", "value", "label"):
            rendered = filter_text_value(value.get(key))
            if rendered:
                return [rendered]
        result = []
        for item in value.values():
            result.extend(iter_filter_values(item))
        return list(dict.fromkeys(result))
    return []


def iter_nested_filter_values(value: dict[str, Any]) -> list[tuple[str, str]]:
    """Flatten useful nested attribute maps into field/value pairs."""
    result: list[tuple[str, str]] = []
    for raw_key, raw_value in value.items():
        key = str(raw_key or "").strip()
        if not key or is_ignored_dynamic_filter_field(key):
            continue
        for text in iter_filter_values(raw_value):
            result.append((key, text))
    return result


def is_attribute_container(field_name: str) -> bool:
    """Return whether a raw field likely contains named attributes."""
    normalized = field_name.casefold().replace("-", "_").replace(" ", "_")
    return normalized in {
        "attributes",
        "characteristics",
        "properties",
        "parameters",
        "features",
        "specs",
        "product_properties",
        "productproperties",
    }


def filter_text_value(value: Any) -> str:
    """Return one short non-URL filter label."""
    text = text_value(value)
    if not text or len(text) > 80:
        return ""
    if text.startswith(("http://", "https://")):
        return ""
    return text


def text_value(value: Any) -> str:
    """Render one optional value to text."""
    return str(value or "").strip()
