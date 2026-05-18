import json

from utils.interception_archive import build_interception_archive, write_interception_archive


def test_build_interception_archive_keeps_only_safe_compact_fields() -> None:
    archive = build_interception_archive(
        {
            "shop": "pyaterochka",
            "category": "Fish",
            "api_first": {
                "candidate_count": 1,
                "ready_count": 0,
                "missing_field_counts": {"link": 1},
                "field_coverage": {"name": 1, "price": 1, "link": 0},
                "mapper_readiness": {
                    "ready": False,
                    "required_fields": ["source_id", "name", "price", "link", "image", "availability"],
                    "missing_fields": ["source_id", "link", "image", "availability"],
                },
                "samples": [{"name": "Fish", "price": 100, "field_sources": {"name": "title"}, "token": "secret"}],
            },
            "events": [
                {
                    "method": "GET",
                    "status": 200,
                    "url": "https://5ka.ru/api/catalog?token=%2A%2A%2A",
                    "route_type": "product_api",
                    "sample_products": [{"name": "Fish"}, {"name": "Other"}],
                    "extra_raw_headers": {"cookie": "secret"},
                }
            ],
        }
    )

    assert archive["events"][0]["route_type"] == "product_api"
    assert archive["api_first"]["candidate_count"] == 1
    assert archive["api_first"]["mapper_readiness"]["missing_fields"] == [
        "source_id",
        "link",
        "image",
        "availability",
    ]
    assert archive["api_first"]["samples"] == [{"name": "Fish", "price": 100, "field_sources": {"name": "title"}}]
    assert "extra_raw_headers" not in archive["events"][0]
    assert "secret" not in str(archive)


def test_write_interception_archive_writes_json(tmp_path) -> None:
    path = write_interception_archive(
        {"shop": "pyaterochka", "category": "Fish & Seafood", "events": []},
        tmp_path,
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.name == "pyaterochka_fish_seafood_interception.json"
    assert payload["category"] == "Fish & Seafood"
