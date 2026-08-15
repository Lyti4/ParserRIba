"""Deterministic no-network application fixture."""

from __future__ import annotations

from typing import Any


def fixture_data() -> dict[str, Any]:
    products = (
        {"product_id": "fixture-product-001", "name": "Сёмга охлаждённая", "category": "Рыба", "brand": "Северный берег", "country": "Россия", "supplier": "Fixture Supplier A", "price": "199.90", "in_stock": True},
        {"product_id": "fixture-product-002", "name": "Сельдь", "category": "Рыба", "brand": "Ёлочка", "country": "Россия", "supplier": "Fixture Supplier B", "price": "99.50", "in_stock": False},
        {"product_id": "fixture-product-003", "name": "Минтай", "category": "Рыба", "brand": None, "country": "Россия", "supplier": "Fixture Supplier A", "price": None, "in_stock": True},
        {"product_id": "fixture-product-004", "name": "Форель", "category": "Рыба", "brand": "Северный берег", "country": "Россия", "supplier": "Fixture Supplier A", "price": "199.90", "in_stock": True},
    )
    return {
        "research": {"store_name": "Fixture Store", "mode": "deterministic_fixture"},
        "catalog_nodes": ({"catalog_node_id": "fixture-node-fish", "name": "Рыба", "parent_id": None},),
        "products": products,
        "selected_product_ids": ("fixture-product-001", "fixture-product-004"),
    }
