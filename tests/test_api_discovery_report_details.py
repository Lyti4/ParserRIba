from utils.api_discovery import build_markdown_report


def test_build_markdown_report_shows_link_and_availability_for_payload_candidates() -> None:
    report = build_markdown_report(
        {
            "product_events": [
                {
                    "status": 200,
                    "url": "https://5d.5ka.ru/api/catalog/products",
                    "sample_products": [
                        {
                            "id": "123",
                            "name": "Forel",
                            "price": "100",
                            "link": "/p/123",
                            "availability": 1,
                            "field_sources": {"id": "productId", "link": "product_url"},
                        }
                    ],
                }
            ],
            "empty_events": [],
        }
    )

    assert "/p/123" in report
    assert "available=1" in report
    assert "sources={'id': 'productId', 'link': 'product_url'}" in report


def test_build_markdown_report_shows_schema_candidate_sources() -> None:
    report = build_markdown_report(
        {
            "interception": {
                "route_counts": {"product_api": 1},
                "replay_candidates": [
                    {
                        "status": 200,
                        "candidate_product_count": 1,
                        "url": "https://5d.5ka.ru/api/catalog/products",
                        "sample_products": [{"field_sources": {"id": "productId", "price": "current_price"}}],
                    }
                ],
                "schema_candidates": [
                    {
                        "candidate_product_count": 1,
                        "schema_hints": {"top_keys": ["productId", "title", "current_price"]},
                        "sample_products": [{"field_sources": {"id": "productId", "price": "current_price"}}],
                    }
                ],
            }
        }
    )

    assert "sources={'id': 'productId', 'price': 'current_price'}" in report


def test_build_markdown_report_shows_api_first_source_filter() -> None:
    report = build_markdown_report(
        {
            "api_first": {
                "candidate_count": 1,
                "ready_count": 0,
                "missing_field_counts": {"link": 1},
                "source_filter": {
                    "mode": "products_only",
                    "eligible_events_count": 1,
                    "excluded_events_count": 3,
                    "excluded_urls": [
                        "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
                        "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories/251C13077/ancestors",
                    ],
                },
                "field_coverage": {"source_id": 1, "name": 1, "price": 1, "image": 1, "link": 0, "availability": 1},
                "mapper_readiness": {"ready": False, "missing_fields": ["link"]},
                "link_evidence": {
                    "products_have_link_key": False,
                    "eligible_product_events_with_link_key": 0,
                    "eligible_product_events_without_link_key": 1,
                    "non_product_link_urls": [
                        "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
                    ],
                    "non_product_link_keys": ["deeplink", "info_link"],
                },
                "samples": [],
            }
        }
    )

    assert "Source filter: mode=products_only, eligible=1, excluded=3" in report
    assert "Link evidence: products_have_link_key=False, eligible_with_link=0, eligible_without_link=1" in report
    assert "Non-product link keys: ['deeplink', 'info_link']" in report
    assert "Excluded URLs:" in report
    assert "/categories" in report
