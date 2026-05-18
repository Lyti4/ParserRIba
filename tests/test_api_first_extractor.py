from utils.api_first_extractor import (
    build_api_product_candidate,
    extract_api_product_candidates,
    summarize_api_first_candidates,
)


def test_build_api_product_candidate_marks_ready_sample() -> None:
    candidate = build_api_product_candidate(
        {
            "id": "123",
            "name": "Forel",
            "price": {"current": "199.90"},
            "link": "https://5ka.ru/product/123",
            "image": {"url": "https://img.example/123.webp"},
            "availability": True,
            "keys": ["id", "name", "price"],
        },
        source_url="https://5d.5ka.ru/api/catalog/products",
    )

    assert candidate.source_id == "123"
    assert candidate.price == 199.90
    assert candidate.image == "https://img.example/123.webp"
    assert candidate.availability is True
    assert candidate.ready_for_product_model is True
    assert candidate.missing_fields == ()


def test_build_api_product_candidate_reads_pyaterochka_alias_fields() -> None:
    candidate = build_api_product_candidate(
        {
            "productId": "123",
            "title": "Forel",
            "current_price": 199,
            "product_url": "https://5ka.ru/product/123",
            "image_link": "https://img.example/123.webp",
            "inStock": 1,
        },
        source_url="https://5d.5ka.ru/api/catalog/products",
    )

    assert candidate.source_id == "123"
    assert candidate.name == "Forel"
    assert candidate.price == 199.0
    assert candidate.image == "https://img.example/123.webp"
    assert candidate.link == "https://5ka.ru/product/123"
    assert candidate.availability is True
    assert candidate.field_sources == {
        "source_id": "productId",
        "name": "title",
        "price": "current_price",
        "image": "image_link",
        "link": "product_url",
        "availability": "inStock",
    }
    assert candidate.ready_for_product_model is True


def test_build_api_product_candidate_reads_confirmed_live_payload_fields() -> None:
    candidate = build_api_product_candidate(
        {
            "plu": 4023639,
            "name": "Forel",
            "prices": {"regular": "999.99"},
            "image_links": [{"url": "https://img.example/4023639.webp"}],
            "is_available": True,
        },
        source_url="https://5d.5ka.ru/api/catalog/v2/stores/35XY/categories/251C13077/products",
    )

    assert candidate.source_id == "4023639"
    assert candidate.name == "Forel"
    assert candidate.price == 999.99
    assert candidate.image == "https://img.example/4023639.webp"
    assert candidate.availability is True
    assert candidate.missing_fields == ("link",)
    assert candidate.field_sources == {
        "source_id": "plu",
        "name": "name",
        "price": "prices",
        "image": "image_links",
        "availability": "is_available",
    }


def test_build_api_product_candidate_preserves_raw_field_sources_from_normalized_sample() -> None:
    candidate = build_api_product_candidate(
        {
            "id": 4023639,
            "name": "Forel",
            "price": 999.99,
            "image": "https://img.example/4023639.webp",
            "link": "",
            "availability": True,
            "field_sources": {
                "id": "plu",
                "name": "name",
                "price": "prices",
                "image": "image_links",
                "availability": "is_available",
            },
            "keys": ["plu", "name", "prices", "image_links", "is_available"],
        },
        source_url="https://5d.5ka.ru/api/catalog/v2/stores/35XY/categories/251C13077/products",
    )

    assert candidate.source_id == "4023639"
    assert candidate.missing_fields == ("link",)
    assert candidate.field_sources == {
        "source_id": "plu",
        "name": "name",
        "price": "prices",
        "image": "image_links",
        "availability": "is_available",
    }


def test_extract_api_product_candidates_deduplicates_samples() -> None:
    events = [
        {
            "url": "https://5d.5ka.ru/api/catalog/products",
            "sample_products": [
                {"id": "123", "name": "Forel", "price": 100, "link": "https://5ka.ru/p/123"},
                {"id": "123", "name": "Forel", "price": 100, "link": "https://5ka.ru/p/123"},
                {"id": "456", "name": "Losos", "price": "250 rub", "link": "https://5ka.ru/p/456"},
            ],
        }
    ]

    products = extract_api_product_candidates(events)

    assert [product.source_id for product in products] == ["123", "456"]


def test_extract_api_product_candidates_accepts_products_endpoint_only() -> None:
    events = [
        {
            "url": "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
            "sample_products": [{"id": "cat-1", "name": "Category"}],
        },
        {
            "url": "https://5d.5ka.ru/api/catalog/v2/stores/35XY/categories/251C13077/products",
            "sample_products": [{"plu": 4023639, "name": "Forel", "prices": {"regular": "999.99"}}],
        },
        {
            "url": "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories/251C13077/ancestors",
            "sample_products": [{"id": "251C13077", "name": "Fish"}],
        },
    ]

    products = extract_api_product_candidates(events)

    assert [product.source_id for product in products] == ["4023639"]


def test_summarize_api_first_candidates_reports_missing_fields() -> None:
    summary = summarize_api_first_candidates(
        [
            {
                "url": "https://5d.5ka.ru/api/catalog/products",
                "sample_products": [
                    {"id": "123", "name": "Forel", "price": 100, "link": "https://5ka.ru/p/123"},
                    {"id": "456", "name": "Losos", "price": None},
                ],
            }
        ]
    )

    assert summary["candidate_count"] == 2
    assert summary["ready_count"] == 1
    assert summary["missing_field_counts"] == {"price": 1, "link": 1}
    assert summary["field_coverage"] == {
        "source_id": 2,
        "name": 2,
        "price": 1,
        "image": 0,
        "link": 1,
        "availability": 0,
    }
    assert summary["mapper_readiness"] == {
        "ready": False,
        "required_fields": ["source_id", "name", "price", "link", "image", "availability"],
        "missing_fields": ["image", "availability"],
    }


def test_summarize_api_first_candidates_reports_availability_coverage() -> None:
    summary = summarize_api_first_candidates(
        [
            {
                "url": "https://5d.5ka.ru/api/catalog/products",
                "sample_products": [
                    {
                        "id": "123",
                        "name": "Forel",
                        "price": 100,
                        "link": "https://5ka.ru/p/123",
                        "availability": False,
                    }
                ],
            }
        ]
    )

    assert summary["field_coverage"]["availability"] == 1
    assert summary["samples"][0]["availability"] is False


def test_summarize_api_first_candidates_enriches_link_from_exact_dom_id_match() -> None:
    summary = summarize_api_first_candidates(
        [
            {
                "url": "https://5d.5ka.ru/api/catalog/v2/stores/35XY/categories/251C13077/products",
                "sample_products": [
                    {
                        "plu": 4023639,
                        "name": "Forel",
                        "prices": {"regular": "999.99"},
                        "image_links": [{"url": "https://img.example/4023639.webp"}],
                        "is_available": True,
                    }
                ],
            }
        ],
        dom_links_by_id={
            "4023639": "https://5ka.ru/product/forel--4023639/",
        },
    )

    assert summary["ready_count"] == 1
    assert summary["missing_field_counts"] == {}
    assert summary["field_coverage"]["link"] == 1
    assert summary["mapper_readiness"]["ready"] is True
    assert summary["samples"][0]["link"] == "https://5ka.ru/product/forel--4023639/"
    assert summary["samples"][0]["field_sources"]["link"] == "dom_product_href"


def test_summarize_api_first_candidates_marks_mapper_ready_when_all_fields_exist() -> None:
    summary = summarize_api_first_candidates(
        [
            {
                "url": "https://5d.5ka.ru/api/catalog/products",
                "sample_products": [
                    {
                        "id": "123",
                        "name": "Forel",
                        "price": 100,
                        "link": "https://5ka.ru/p/123",
                        "image": "https://img.example/123.webp",
                        "availability": True,
                    }
                ],
            }
        ]
    )

    assert summary["mapper_readiness"]["ready"] is True
    assert summary["mapper_readiness"]["missing_fields"] == []


def test_summarize_api_first_candidates_reports_products_only_filter() -> None:
    summary = summarize_api_first_candidates(
        [
            {
                "url": "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
                "has_link_key": True,
                "schema_hints": {"top_keys": ["id", "name", "deeplink", "info_link"]},
                "sample_products": [{"id": "251C17045", "name": "Promo category"}],
            },
            {
                "url": "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories/251C13077/ancestors",
                "sample_products": [{"id": "251C13077", "name": "Fish"}],
            },
            {
                "url": "https://5d.5ka.ru/api/catalog/v2/stores/35XY/categories/251C13077/products",
                "has_link_key": False,
                "schema_hints": {"top_keys": ["plu", "name", "prices", "image_links", "is_available"]},
                "sample_products": [
                    {
                        "plu": 4023639,
                        "name": "Forel",
                        "prices": {"regular": "999.99"},
                        "image_links": [{"url": "https://img.example/4023639.webp"}],
                        "is_available": True,
                    }
                ],
            },
            {
                "url": "https://5d.5ka.ru/api/catalog/v2/stores/35XY/categories/251C13077/extended",
                "sample_products": [{"id": "251C13077", "name": "Fish"}],
            },
        ]
    )

    assert summary["candidate_count"] == 1
    assert summary["field_coverage"] == {
        "source_id": 1,
        "name": 1,
        "price": 1,
        "image": 1,
        "link": 0,
        "availability": 1,
    }
    assert summary["mapper_readiness"]["missing_fields"] == ["link"]
    assert summary["source_filter"] == {
        "mode": "products_only",
        "eligible_events_count": 1,
        "excluded_events_count": 3,
        "excluded_urls": [
            "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
            "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories/251C13077/ancestors",
            "https://5d.5ka.ru/api/catalog/v2/stores/35XY/categories/251C13077/extended",
        ],
    }
    assert summary["link_evidence"] == {
        "products_have_link_key": False,
        "eligible_product_events_with_link_key": 0,
        "eligible_product_events_without_link_key": 1,
        "non_product_link_urls": [
            "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
        ],
        "non_product_link_keys": ["deeplink", "info_link"],
    }
    assert summary["samples"][0]["field_sources"] == {
        "source_id": "plu",
        "name": "name",
        "price": "prices",
        "image": "image_links",
        "availability": "is_available",
    }


def test_summarize_api_first_candidates_infers_non_product_link_evidence_from_schema_keys() -> None:
    summary = summarize_api_first_candidates(
        [
            {
                "url": "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
                "schema_hints": {"top_keys": ["id", "name", "deeplink", "info_link"]},
                "sample_products": [{"id": "251C17045", "name": "Promo category"}],
            },
            {
                "url": "https://5d.5ka.ru/api/catalog/v2/stores/35XY/categories/251C13077/products",
                "schema_hints": {"top_keys": ["plu", "name", "prices", "image_links", "is_available"]},
                "sample_products": [{"plu": 4023639, "name": "Forel", "prices": {"regular": "999.99"}}],
            },
        ]
    )

    assert summary["link_evidence"]["products_have_link_key"] is False
    assert summary["link_evidence"]["non_product_link_urls"] == [
        "https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories",
    ]
    assert summary["link_evidence"]["non_product_link_keys"] == ["deeplink", "info_link"]
