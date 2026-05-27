"""Product detail rendering for the desktop launcher."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_product_detail_text(
    json_path: str,
    selected_product_ids: list[str],
    products: list[dict[str, Any]] | None = None,
) -> str:
    """Build one readable detail block for the first selected product."""
    product_id = _first_selected_product_id(selected_product_ids)
    if not product_id:
        return "Выберите товар в таблице, чтобы увидеть полную карточку."
    product = _find_product_in_items(products or [], product_id) or _find_product_by_id(json_path, product_id)
    if not product:
        return "Карточка выбранного товара не найдена в текущем JSON."
    lines = _product_header_lines(product)
    raw_data = product.get("raw_data")
    if isinstance(raw_data, dict) and raw_data:
        lines.append("")
        lines.append("\u0420\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u043d\u044b\u0435 \u043f\u043e\u043b\u044f:")
        lines.extend(_flatten_raw_field_lines(raw_data))
        lines.append("")
        lines.append("Все найденные поля:")
        lines.append(json.dumps(raw_data, ensure_ascii=False, indent=2, sort_keys=True))
    return "\n".join(lines)


def _first_selected_product_id(selected_product_ids: list[str]) -> str:
    for item in selected_product_ids:
        product_id = str(item).strip()
        if product_id:
            return product_id
    return ""


def _find_product_by_id(json_path: str, product_id: str) -> dict[str, Any] | None:
    path = Path(str(json_path or ""))
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    products = payload.get("products")
    if not isinstance(products, list):
        return None
    for item in products:
        if not isinstance(item, dict):
            continue
        if _product_id(item) == product_id:
            return item
    return None


def _find_product_in_items(products: list[dict[str, Any]], product_id: str) -> dict[str, Any] | None:
    for item in products:
        if _product_id(item) == product_id:
            return item
    return None


def _product_id(product: dict[str, Any]) -> str:
    return str(product.get("id") or product.get("product_id") or "").strip()


def _product_header_lines(product: dict[str, Any]) -> list[str]:
    raw_data = product.get("raw_data")
    raw = raw_data if isinstance(raw_data, dict) else {}
    price = product.get("price")
    price_text = ""
    if isinstance(price, dict):
        price_text = str(price.get("current") or "")
    return [
        f"Товар: {product.get('name') or ''}",
        f"ID: {product.get('id') or product.get('product_id') or ''}",
        f"Категория: {product.get('category') or ''}",
        f"Бренд: {product.get('brand') or ''}",
        f"Поставщик/производитель: {raw.get('supplier') or raw.get('producer') or raw.get('vendor') or ''}",
        f"Цена: {price_text}",
        f"Наличие: {'да' if product.get('in_stock') else 'нет'}",
        f"Ссылка: {product.get('product_link') or ''}",
    ]


def _flatten_raw_field_lines(raw_data: dict[str, Any]) -> list[str]:
    """Render raw scalar and list fields before the diagnostic JSON dump."""
    lines: list[str] = []
    for key, value in sorted(raw_data.items()):
        if key == "field_sources":
            continue
        rendered = _render_raw_value(value)
        if rendered:
            lines.append(f"- {_field_label(key)}: {rendered}")
    return lines or ["- \u041d\u0435\u0442 \u0434\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0445 \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u043d\u043d\u044b\u0445 \u043f\u043e\u043b\u0435\u0439."]


def _render_raw_value(value: Any) -> str:
    if isinstance(value, bool):
        return "\u0434\u0430" if value else "\u043d\u0435\u0442"
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    if isinstance(value, list):
        rendered = [_render_raw_value(item) for item in value]
        return ", ".join(item for item in rendered if item)
    return ""


def _field_label(key: str) -> str:
    labels = {
        "source_id": "ID \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u0430",
        "categories": "\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438",
        "supplier": "\u041f\u043e\u0441\u0442\u0430\u0432\u0449\u0438\u043a",
        "producer": "\u041f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c",
        "manufacturer": "\u0418\u0437\u0433\u043e\u0442\u043e\u0432\u0438\u0442\u0435\u043b\u044c",
        "vendor": "\u041f\u0440\u043e\u0434\u0430\u0432\u0435\u0446",
        "alcohol_type": "\u0410\u043b\u043a\u043e\u0433\u043e\u043b\u044c\u043d\u044b\u0439 \u0442\u0438\u043f",
        "sugar_class": "\u0421\u0430\u0445\u0430\u0440",
        "color": "\u0426\u0432\u0435\u0442",
    }
    return labels.get(key, key.replace("_", " "))

