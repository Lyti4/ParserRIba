from utils.api_discovery import (
    build_discovery_result,
    build_markdown_report,
    extract_product_candidates,
    is_interesting_api_url,
    safe_json_loads,
)


def test_is_interesting_api_url_accepts_only_5ka_catalog_api() -> None:
    assert is_interesting_api_url("https://5d.5ka.ru/api/catalog/v3/stores/35XY/products")
    assert is_interesting_api_url("https://5ka.ru/api/search/v1/products?q=fish")
    assert not is_interesting_api_url("https://api.ipify.org/?format=json")
    assert not is_interesting_api_url("https://fonts.googleapis.com/css2?family=Manrope")


def test_extract_product_candidates_from_nested_payload() -> None:
    payload = {
        "items": [
            {
                "id": "123",
                "name": "Форель охлажденная",
                "price": {"regular": 1000},
                "slug": "forel",
            }
        ]
    }

    products = extract_product_candidates(payload)

    assert products[0]["id"] == "123"
    assert products[0]["name"] == "Форель охлажденная"
    assert products[0]["slug"] == "forel"


def test_extract_product_candidates_handles_pyaterochka_alias_fields() -> None:
    payload = {
        "items": [
            {
                "productId": "123",
                "title": "Forel",
                "current_price": 199,
                "image_link": "img.webp",
                "product_url": "/p/123",
                "inStock": 1,
                "slug": "forel",
            }
        ]
    }

    products = extract_product_candidates(payload)

    assert products[0]["id"] == "123"
    assert products[0]["name"] == "Forel"
    assert products[0]["price"] == 199
    assert products[0]["image"] == "img.webp"
    assert products[0]["link"] == "/p/123"
    assert products[0]["availability"] == 1
    assert products[0]["field_sources"] == {
        "id": "productId",
        "name": "title",
        "price": "current_price",
        "image": "image_link",
        "link": "product_url",
        "availability": "inStock",
    }
    assert products[0]["slug"] == "forel"


def test_safe_json_loads_returns_none_on_bad_json() -> None:
    assert safe_json_loads("{bad") is None
    assert safe_json_loads('{"ok": true}') == {"ok": True}


def test_build_discovery_result_groups_product_and_empty_events() -> None:
    result = build_discovery_result(
        category_name="Рыба",
        category_url="https://5ka.ru/catalog/ryba--251C13077/",
        proxy_url="http://user:pass@example.com:1000",
        geoip_enabled=True,
        listen_seconds=10,
        dom_link_evidence={
            "count": 2,
            "sample_links": [
                {"href": "https://5ka.ru/product/forel--123/", "title": "Forel"},
                {"href": "https://5ka.ru/product/losos--999/", "title": "Losos"},
            ],
            "product_ids": ["123", "999"],
        },
        events=[
            {
                "status": 200,
                "url": "https://5d.5ka.ru/api/catalog/products",
                "route_type": "product_api",
                "candidate_product_count": 1,
                "replay_candidate": True,
                "schema_hints": {"top_keys": ["id", "name", "price"]},
                "sample_products": [{"id": "123", "name": "Forel", "price": 100, "link": ""}],
            },
            {
                "status": 200,
                "url": "https://5d.5ka.ru/api/catalog/products",
                "empty_products_payload": True,
            },
        ],
    )

    assert result["events_count"] == 2
    assert result["product_events_count"] == 1
    assert result["empty_events_count"] == 1
    assert result["proxy"] == "http://***:***@example.com:1000"
    assert result["interception"]["route_counts"] == {"product_api": 1, "unknown": 1}
    assert result["interception"]["replay_candidates"][0]["candidate_product_count"] == 1
    assert result["api_first"]["candidate_count"] == 1
    assert result["api_first"]["ready_count"] == 1
    assert result["api_first"]["samples"][0]["link"] == "https://5ka.ru/product/forel--123/"
    assert result["api_first"]["samples"][0]["field_sources"]["link"] == "dom_product_href"
    assert result["dom_link_evidence"] == {
        "count": 2,
        "sample_links": [
            {"href": "https://5ka.ru/product/forel--123/", "title": "Forel"},
            {"href": "https://5ka.ru/product/losos--999/", "title": "Losos"},
        ],
        "product_ids": ["123", "999"],
        "links_by_id": {
            "123": "https://5ka.ru/product/forel--123/",
            "999": "https://5ka.ru/product/losos--999/",
        },
        "api_source_ids": ["123"],
        "matched_api_source_ids": ["123"],
        "unmatched_dom_product_ids": ["999"],
    }


def test_build_markdown_report_mentions_product_candidates() -> None:
    report = build_markdown_report(
        {
            "category": "Рыба",
            "category_url": "https://5ka.ru/catalog/ryba--251C13077/",
            "listen_seconds": 10,
            "proxy_enabled": True,
            "proxy": "http://***:***@example.com:1000",
            "geoip_enabled": True,
            "events_count": 1,
            "status_counts": {"200": 1},
            "product_events_count": 1,
            "empty_events_count": 0,
            "product_events": [
                {
                    "status": 200,
                    "url": "https://5d.5ka.ru/api/catalog/products",
                    "sample_products": [{"id": "123", "name": "Форель", "price": "100"}],
                }
            ],
            "empty_events": [],
            "interception": {
                "route_counts": {"product_api": 1},
                "replay_candidates": [
                    {
                        "status": 200,
                        "url": "https://5d.5ka.ru/api/catalog/products",
                        "candidate_product_count": 1,
                    }
                ],
                "schema_candidates": [
                    {
                        "candidate_product_count": 1,
                        "schema_hints": {"top_keys": ["id", "name", "price"]},
                    }
                ],
            },
            "api_first": {
                "candidate_count": 1,
                "ready_count": 1,
                "missing_field_counts": {},
                "source_filter": {
                    "mode": "products_only",
                    "eligible_events_count": 1,
                    "excluded_events_count": 2,
                    "excluded_urls": [
                        "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
                        "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories/251C13077/ancestors",
                    ],
                },
                "field_coverage": {
                    "source_id": 1,
                    "name": 1,
                    "price": 1,
                    "image": 1,
                    "link": 1,
                    "availability": 1,
                },
                "mapper_readiness": {
                    "ready": True,
                    "required_fields": ["source_id", "name", "price", "link", "image", "availability"],
                    "missing_fields": [],
                },
                "link_evidence": {
                    "products_have_link_key": True,
                    "eligible_product_events_with_link_key": 1,
                    "eligible_product_events_without_link_key": 0,
                    "non_product_link_urls": [],
                    "non_product_link_keys": [],
                },
                "samples": [
                    {
                        "source_id": "123",
                        "name": "Р¤РѕСЂРµР»СЊ",
                        "price": 100.0,
                        "availability": True,
                        "field_sources": {"source_id": "productId", "price": "current_price"},
                        "missing_fields": [],
                    }
                ],
            },
            "dom_link_evidence": {
                "count": 2,
                "sample_links": [
                    {"href": "https://5ka.ru/product/forel--123/", "title": "Forel"},
                    {"href": "https://5ka.ru/product/losos--999/", "title": "Losos"},
                ],
                "product_ids": ["123", "999"],
                "api_source_ids": ["123"],
                "matched_api_source_ids": ["123"],
                "unmatched_dom_product_ids": ["999"],
            },
            "site_errors": {
                "total": 1,
                "severity_counts": {"warning": 1},
                "source_counts": {"discovery": 1},
                "events": [
                    {
                        "severity": "warning",
                        "source": "discovery",
                        "code": "api_discovery_no_product_payload",
                        "message": "No product payload candidates were captured.",
                        "count": 1,
                    }
                ],
            },
        }
    )

    assert "Product Payload Candidates" in report
    assert "API-first Extraction" in report
    assert "DOM Link Evidence" in report
    assert "Matched API ids: ['123']" in report
    assert "Unmatched DOM ids: ['999']" in report
    assert "Field coverage" in report
    assert "Source filter: mode=products_only, eligible=1, excluded=2" in report
    assert "Link evidence: products_have_link_key=True, eligible_with_link=1, eligible_without_link=0" in report
    assert "availability=1" in report
    assert "Mapper readiness: ready=True" in report
    assert "sources={'source_id': 'productId', 'price': 'current_price'}" in report
    assert "Site Error Tracking" in report
    assert "available=True" in report
    assert "123 | Форель | 100" in report
