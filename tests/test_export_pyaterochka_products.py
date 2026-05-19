from models.schemas import Product
from scripts.export_pyaterochka_products import (
    build_products_from_discovery_result,
    build_products_from_product_items,
    extract_product_items_from_payload,
    export_pyaterochka_products,
)


def test_build_products_from_discovery_result_maps_ready_api_first_samples() -> None:
    result = {
        "shop": "pyaterochka",
        "category": "Рыба",
        "category_url": "https://5ka.ru/catalog/ryba--251C13077/",
        "api_first": {
            "samples": [
                {
                    "source_id": "4023639",
                    "name": "Треска",
                    "price": 999.99,
                    "image": "https://img.example/4023639.webp",
                    "link": "https://5ka.ru/product/treska--4023639/",
                    "availability": True,
                    "missing_fields": [],
                    "field_sources": {
                        "source_id": "plu",
                        "price": "prices",
                        "link": "dom_product_href",
                    },
                },
                {
                    "source_id": "broken",
                    "name": "Без ссылки",
                    "price": 100,
                    "link": "",
                    "missing_fields": ["link"],
                },
            ]
        },
    }

    products = build_products_from_discovery_result(result)

    assert len(products) == 1
    product = products[0]
    assert isinstance(product, Product)
    assert product.id == "4023639"
    assert product.name == "Треска"
    assert product.price.current == 999.99
    assert str(product.product_link) == "https://5ka.ru/product/treska--4023639/"
    assert str(product.image_url) == "https://img.example/4023639.webp"
    assert product.in_stock is True
    assert product.category == "Рыба"
    assert product.raw_data == {
        "source_id": "4023639",
        "field_sources": {
            "source_id": "plu",
            "price": "prices",
            "link": "dom_product_href",
        },
    }


def test_extract_product_items_from_payload_keeps_all_items() -> None:
    payload = {
        "products": [
            {"plu": idx, "name": f"Fish {idx}", "prices": {"regular": idx * 10}, "is_available": True}
            for idx in range(1, 13)
        ]
    }

    items = extract_product_items_from_payload(payload)

    assert len(items) == 12
    assert items[0]["plu"] == 1
    assert items[-1]["plu"] == 12


def test_build_products_from_product_items_uses_dom_link_map() -> None:
    products = build_products_from_product_items(
        [
            {
                "plu": 4023639,
                "name": "Треска",
                "prices": {"regular": "999.99"},
                "image_links": [{"url": "https://img.example/4023639.webp"}],
                "is_available": True,
            }
        ],
        category="Рыба",
        dom_links_by_id={"4023639": "https://5ka.ru/product/treska--4023639/"},
    )

    assert len(products) == 1
    assert isinstance(products[0], Product)
    assert products[0].id == "4023639"
    assert products[0].price.current == 999.99
    assert str(products[0].product_link) == "https://5ka.ru/product/treska--4023639/"
    assert products[0].raw_data == {
        "source_id": "4023639",
        "field_sources": {
            "source_id": "plu",
            "name": "name",
            "price": "prices",
            "image": "image_links",
            "availability": "is_available",
            "link": "dom_product_href",
        },
    }


async def test_export_pyaterochka_products_retries_until_success() -> None:
    calls: list[str] = []

    async def fake_discover(*, category_name: str, listen_seconds: int, headless: bool | str | None, manual_wait: bool):
        calls.append(category_name)
        if len(calls) < 3:
            return {
                "shop": "pyaterochka",
                "category": category_name,
                "category_url": "https://5ka.ru/catalog/ryba--251C13077/",
                "api_first": {"ready_count": 0, "samples": []},
                "attempt": {"status": "empty", "reason": "no_product_payload"},
            }
        return {
            "shop": "pyaterochka",
            "category": category_name,
            "category_url": "https://5ka.ru/catalog/ryba--251C13077/",
            "api_first": {
                "ready_count": 1,
                "samples": [
                    {
                        "source_id": "4023639",
                        "name": "Треска",
                        "price": 999.99,
                        "link": "https://5ka.ru/product/treska--4023639/",
                        "availability": True,
                        "missing_fields": [],
                    }
                ],
            },
            "attempt": {"status": "ok", "reason": "product_payload_captured"},
        }

    payload = await export_pyaterochka_products(
        attempts=3,
        listen_seconds=15,
        manual_wait=False,
        discover_func=fake_discover,
    )

    assert calls == ["Рыба", "Морепродукты", "Икра и закуски", "Котлеты и фарш"]
    assert payload["attempts_used"] == 1
    assert payload["products_count"] == 1
    assert payload["attempt"]["status"] == "ok"
    assert payload["products"][0]["id"] == "4023639"
async def test_export_pyaterochka_products_combines_fish_and_seafood_categories() -> None:
    calls: list[str] = []

    async def fake_discover(*, category_name: str, listen_seconds: int, headless: bool | str | None, manual_wait: bool):
        calls.append(category_name)
        shared_item = {
            "plu": 4023639,
            "name": "Треска",
            "prices": {"regular": "999.99"},
            "image_links": [{"url": "https://img.example/4023639.webp"}],
            "is_available": True,
        }
        if category_name == "Рыба":
            return {
                "shop": "pyaterochka",
                "category": "Рыба",
                "category_url": "https://5ka.ru/catalog/ryba--251C13077/",
                "raw_product_items": [shared_item],
                "dom_link_evidence": {
                    "links_by_id": {
                        "4023639": "https://5ka.ru/product/treska--4023639/",
                    }
                },
                "attempt": {"status": "ok", "reason": "product_payload_captured"},
            }
        return {
            "shop": "pyaterochka",
            "category": "Морепродукты",
            "category_url": "https://5ka.ru/catalog/moreprodukty--251C13078/",
            "raw_product_items": [
                shared_item,
                {
                    "plu": 5000001,
                    "name": "Креветки",
                    "prices": {"regular": "799.99"},
                    "image_links": [{"url": "https://img.example/5000001.webp"}],
                    "is_available": True,
                },
            ],
            "dom_link_evidence": {
                "links_by_id": {
                    "4023639": "https://5ka.ru/product/treska--4023639/",
                    "5000001": "https://5ka.ru/product/krevetki--5000001/",
                }
            },
            "attempt": {"status": "ok", "reason": "product_payload_captured"},
        }

    payload = await export_pyaterochka_products(
        category_name="Рыба",
        attempts=1,
        listen_seconds=1,
        manual_wait=False,
        discover_func=fake_discover,
    )

    assert calls == ["Рыба", "Морепродукты", "Икра и закуски", "Котлеты и фарш"]
    assert payload["products_count"] == 2
    assert payload["categories"] == ["Рыба", "Морепродукты", "Икра и закуски", "Котлеты и фарш"]
    assert sorted(item["id"] for item in payload["products"]) == ["4023639", "5000001"]


def test_write_products_export_persists_sqlite_snapshot(tmp_path) -> None:
    from scripts.export_pyaterochka_products import write_products_export

    payload = {
        "shop": "pyaterochka",
        "products_count": 1,
        "products": [
            Product(
                id="4023639",
                name="Треска",
                price=999.99,
                product_link="https://5ka.ru/product/treska--4023639/",
                image_url="https://img.example/4023639.webp",
                in_stock=True,
            ).model_dump(mode="json")
        ],
    }

    export_path, db_path = write_products_export(payload, tmp_path)

    assert export_path.exists()
    assert db_path.exists()
    assert payload["db_path"] == str(db_path)
    assert payload["stored_products_count"] == 1
