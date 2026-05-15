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
            "keys": ["id", "name", "price"],
        },
        source_url="https://5d.5ka.ru/api/catalog/products",
    )

    assert candidate.source_id == "123"
    assert candidate.price == 199.90
    assert candidate.image == "https://img.example/123.webp"
    assert candidate.ready_for_product_model is True
    assert candidate.missing_fields == ()


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
