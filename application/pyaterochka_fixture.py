"""Deterministic Pyaterochka store adapter for local product-workflow slices."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from application.contracts import ApplicationContractError


_CATALOG_NODES: tuple[Mapping[str, str | None], ...] = (
    MappingProxyType(
        {
            "catalog_node_id": "pyaterochka-fish",
            "name": "Рыба",
            "parent_id": None,
            "url": "https://fixture.pyaterochka.local/catalog/fish",
        }
    ),
    MappingProxyType(
        {
            "catalog_node_id": "pyaterochka-wine",
            "name": "Вино",
            "parent_id": None,
            "url": "https://fixture.pyaterochka.local/catalog/wine",
        }
    ),
)
_PRODUCTS_BY_NODE: Mapping[str, tuple[Mapping[str, Any], ...]] = MappingProxyType(
    {
        "pyaterochka-fish": (
            MappingProxyType(
                {
                    "product_id": "pyaterochka-fish-001",
                    "name": "Форель радужная",
                    "category": "Рыба",
                    "brand": "Пятёрочка",
                    "country": "Россия",
                    "supplier": "Fixture North",
                    "price": "349.90",
                    "in_stock": True,
                    "source_catalog_node_id": "pyaterochka-fish",
                }
            ),
            MappingProxyType(
                {
                    "product_id": "pyaterochka-fish-002",
                    "name": "Минтай",
                    "category": "Рыба",
                    "brand": "Красная цена",
                    "country": "Россия",
                    "supplier": "Fixture Sea",
                    "price": "179.50",
                    "in_stock": True,
                    "source_catalog_node_id": "pyaterochka-fish",
                }
            ),
        ),
        "pyaterochka-wine": (
            MappingProxyType(
                {
                    "product_id": "pyaterochka-wine-001",
                    "name": "Вино красное сухое",
                    "category": "Вино",
                    "brand": "Красная цена",
                    "country": "Россия",
                    "supplier": "Fixture Vine",
                    "price": "499.90",
                    "in_stock": True,
                    "source_catalog_node_id": "pyaterochka-wine",
                }
            ),
            MappingProxyType(
                {
                    "product_id": "pyaterochka-wine-002",
                    "name": "Вино белое сухое",
                    "category": "Вино",
                    "brand": "Пятёрочка",
                    "country": "Россия",
                    "supplier": "Fixture Vine",
                    "price": "429.90",
                    "in_stock": False,
                    "source_catalog_node_id": "pyaterochka-wine",
                }
            ),
        ),
    }
)
_NODES_BY_ID = MappingProxyType({str(node["catalog_node_id"]): node for node in _CATALOG_NODES})


class PyaterochkaFixtureAdapter:
    """Collect deterministic cards only for explicit Pyaterochka catalog selections."""

    def collect(self, catalog_node_ids: tuple[str, ...]) -> dict[str, Any]:
        selected_ids = tuple(dict.fromkeys(str(node_id) for node_id in catalog_node_ids if str(node_id)))
        if not selected_ids:
            raise ApplicationContractError(
                "CATALOG_SELECTION_REQUIRED",
                "At least one catalog node must be selected before product collection.",
            )
        unknown_ids = tuple(node_id for node_id in selected_ids if node_id not in _NODES_BY_ID)
        if unknown_ids:
            raise ApplicationContractError(
                "CATALOG_NODE_UNAVAILABLE",
                f"Catalog node is unavailable: {unknown_ids[0]}.",
            )
        catalog_nodes = tuple(dict(_NODES_BY_ID[node_id]) for node_id in selected_ids)
        products = tuple(
            dict(product)
            for node_id in selected_ids
            for product in _PRODUCTS_BY_NODE[node_id]
        )
        return {
            "research": {
                "store_name": "Пятёрочка",
                "store_key": "pyaterochka",
                "mode": "deterministic_fixture",
            },
            "catalog_nodes": catalog_nodes,
            "products": products,
            "selected_product_ids": tuple(product["product_id"] for product in products),
            "source_catalog_node_ids": selected_ids,
        }
