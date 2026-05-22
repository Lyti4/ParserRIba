from pathlib import Path

from scripts.export_store_catalog import build_store_export_payload, get_store_export_backend
from utils.pyaterochka_export import (
    ALCOHOL_FREE,
    ALCOHOL_REGULAR,
    WINE_STYLE_SANGRIA,
    WINE_STYLE_SPARKLING,
    WINE_STYLE_VERMOUTH,
)
from utils.store_export_runtime import write_store_export


def test_write_store_export_writes_wine_breakdown_into_manifest(tmp_path: Path) -> None:
    payload = {
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "category": "wine",
        "categories": ["still-wine", "sparkling-wine"],
        "attempts_requested": 1,
        "attempts_used": 1,
        "attempt": {"status": "ok", "reason": "product_payload_captured"},
        "products_count": 2,
        "products": [
            {
                "id": "4225897",
                "name": "Sparkling OddBird Spumante Veneto 750ml",
                "brand": "OddBird",
                "price": {"current": 699.99},
                "image_url": "https://img.example/4225897.webp",
                "product_link": "https://example.test/product/wine--4225897/",
                "category": "sparkling-wine",
                "subcategory": WINE_STYLE_SPARKLING,
                "in_stock": True,
                "raw_data": {"alcohol_type": ALCOHOL_FREE},
            },
            {
                "id": "4225898",
                "name": "Martini Bianco 1L",
                "brand": "Martini",
                "price": {"current": 899.99},
                "image_url": "https://img.example/4225898.webp",
                "product_link": "https://example.test/product/wine--4225898/",
                "category": "still-wine",
                "subcategory": WINE_STYLE_VERMOUTH,
                "in_stock": True,
                "raw_data": {"alcohol_type": ALCOHOL_REGULAR},
            },
        ],
        "exported_at": "2026-05-20T13:10:00",
    }

    write_store_export(payload, tmp_path)

    summary = payload["run_manifest"]["summary"]
    assert summary["wine_breakdown"]["style_counts"] == {
        WINE_STYLE_SPARKLING: 1,
        WINE_STYLE_VERMOUTH: 1,
    }
    assert summary["wine_breakdown"]["alcohol_type_counts"] == {
        ALCOHOL_FREE: 1,
        ALCOHOL_REGULAR: 1,
    }
    assert isinstance(summary["wine_breakdown"]["sugar_class_counts"], dict)
    assert isinstance(summary["wine_breakdown"]["color_counts"], dict)


async def test_build_store_export_payload_filters_non_wine_products_for_wine_intent() -> None:
    custom_category = "mixed-parent"

    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": "https://example.test/mixed-parent",
            "raw_product_items": [
                {
                    "plu": 4225897,
                    "name": "Sparkling OddBird Spumante Veneto 750ml",
                    "brand": "OddBird",
                    "prices": {"regular": "699.99"},
                    "image_links": [{"url": "https://img.example/4225897.webp"}],
                    "is_available": True,
                },
                {
                    "plu": 4306102,
                    "name": "Aziano Energy Power 350ml",
                    "brand": "Aziano",
                    "prices": {"regular": "61.99"},
                    "image_links": [{"url": "https://img.example/4306102.webp"}],
                    "is_available": True,
                },
            ],
            "dom_link_evidence": {
                "links_by_id": {
                    "4225897": "https://example.test/product/wine--4225897/",
                    "4306102": "https://example.test/product/energy--4306102/",
                }
            },
            "attempt": {"status": "ok", "reason": "product_payload_captured"},
        }

    backend = get_store_export_backend("pyaterochka", "wine_catalog")
    payload = await build_store_export_payload(
        backend=backend,
        category_name=custom_category,
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={
            custom_category: "https://example.test/mixed-parent",
        },
        discover_func=fake_discover,
    )

    assert payload["intent"] == "wine_catalog"
    assert payload["products_count"] == 1
    assert payload["products"][0]["name"] == "Sparkling OddBird Spumante Veneto 750ml"
    assert payload["products"][0]["brand"] == "OddBird"
    assert payload["products"][0]["subcategory"] == WINE_STYLE_SPARKLING
    assert payload["products"][0]["raw_data"]["alcohol_type"] == ALCOHOL_REGULAR


async def test_build_store_export_payload_includes_launcher_facing_export_summary() -> None:
    custom_category = "mixed-parent"

    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": "https://example.test/mixed-parent",
            "raw_product_items": [
                {
                    "plu": 4225897,
                    "name": "Sparkling OddBird Spumante Veneto 750ml",
                    "brand": "OddBird",
                    "prices": {"regular": "699.99"},
                    "image_links": [{"url": "https://img.example/4225897.webp"}],
                    "is_available": True,
                },
                {
                    "plu": 4225898,
                    "name": "Martini Bianco 1L",
                    "brand": "Martini",
                    "prices": {"regular": "899.99"},
                    "image_links": [{"url": "https://img.example/4225898.webp"}],
                    "is_available": True,
                },
            ],
            "dom_link_evidence": {
                "links_by_id": {
                    "4225897": "https://example.test/product/wine--4225897/",
                    "4225898": "https://example.test/product/wine--4225898/",
                }
            },
            "attempt": {"status": "ok", "reason": "product_payload_captured"},
        }

    backend = get_store_export_backend("pyaterochka", "wine_catalog")
    payload = await build_store_export_payload(
        backend=backend,
        category_name=custom_category,
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={
            custom_category: "https://example.test/mixed-parent",
        },
        discover_func=fake_discover,
    )

    assert payload["export_summary"]["products_count"] == 2
    assert payload["export_summary"]["categories"] == [custom_category]
    assert payload["export_summary"]["wine_breakdown"]["style_counts"] == {
        WINE_STYLE_SPARKLING: 1,
        WINE_STYLE_VERMOUTH: 1,
    }


async def test_build_store_export_payload_keeps_wine_edge_cases_with_subtypes() -> None:
    custom_category = "mixed-parent"

    async def fake_discover(
        *,
        category_name: str,
        listen_seconds: int,
        headless: bool | str | None,
        manual_wait: bool,
    ):
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": "https://example.test/mixed-parent",
            "raw_product_items": [
                {
                    "plu": 1,
                    "name": "Martini Bianco 1L",
                    "brand": "Martini",
                    "prices": {"regular": "999.99"},
                    "image_links": [{"url": "https://img.example/1.webp"}],
                    "is_available": True,
                },
                {
                    "plu": 2,
                    "name": "Sparkling Sangria Senorio De Oran Red 0.75L",
                    "brand": "Sangria Senorio De",
                    "prices": {"regular": "499.99"},
                    "image_links": [{"url": "https://img.example/2.webp"}],
                    "is_available": True,
                },
                {
                    "plu": 3,
                    "name": "Apple Juice 0.45L",
                    "brand": "Juice House",
                    "prices": {"regular": "129.99"},
                    "image_links": [{"url": "https://img.example/3.webp"}],
                    "is_available": True,
                },
            ],
            "dom_link_evidence": {
                "links_by_id": {
                    "1": "https://example.test/product/vermouth--1/",
                    "2": "https://example.test/product/sangria--2/",
                    "3": "https://example.test/product/cider--3/",
                }
            },
            "attempt": {"status": "ok", "reason": "product_payload_captured"},
        }

    backend = get_store_export_backend("pyaterochka", "wine_catalog")
    payload = await build_store_export_payload(
        backend=backend,
        category_name=custom_category,
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        headless=True,
        kb_categories={
            custom_category: "https://example.test/mixed-parent",
        },
        discover_func=fake_discover,
    )

    assert payload["products_count"] == 2
    assert [item["name"] for item in payload["products"]] == [
        "Martini Bianco 1L",
        "Sparkling Sangria Senorio De Oran Red 0.75L",
    ]
    assert [item["subcategory"] for item in payload["products"]] == [
        WINE_STYLE_VERMOUTH,
        WINE_STYLE_SANGRIA,
    ]
    assert [item["brand"] for item in payload["products"]] == ["Martini", "Sangria Senorio De"]
