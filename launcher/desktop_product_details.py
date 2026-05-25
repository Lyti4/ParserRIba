"""Product detail rendering for the desktop launcher."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_product_detail_text(json_path: str, selected_product_ids: list[str]) -> str:
    """Build one readable detail block for the first selected product."""
    product_id = _first_selected_product_id(selected_product_ids)
    if not product_id:
        return "Выберите товар в таблице, чтобы увидеть полную карточку."
    product = _find_product_by_id(json_path, product_id)
    if not product:
        return "Карточка выбранного товара не найдена в текущем JSON."
    lines = _product_header_lines(product)
    raw_data = product.get("raw_data")
    if isinstance(raw_data, dict) and raw_data:
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
        current_id = str(item.get("id") or item.get("product_id") or "").strip()
        if current_id == product_id:
            return item
    return None


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
