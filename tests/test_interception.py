from utils.interception import (
    build_interception_event,
    classify_route,
    infer_schema_hints,
    payload_preview,
    sanitize_diagnostic_url,
    summarize_interception_events,
)


def test_build_interception_event_extracts_product_schema() -> None:
    event = build_interception_event(
        method="GET",
        status=200,
        url="https://5d.5ka.ru/api/catalog/v3/products?token=abc",
        content_type="application/json; charset=utf-8",
        payload_text='{"items":[{"id":"1","name":"Fish","price":100,"image":"img.webp","url":"/p/1","available":true}]}',
    )
    payload = event.as_report_dict()

    assert payload["route_type"] == "product_api"
    assert payload["payload_kind"] == "json"
    assert payload["candidate_product_count"] == 1
    assert payload["sample_products"][0]["name"] == "Fish"
    assert payload["sample_products"][0]["availability"] is True
    assert payload["schema_hints"]["has_price_key"] is True
    assert payload["schema_hints"]["has_availability_key"] is True
    assert payload["replay_candidate"] is True
    assert "abc" not in payload["url"]


def test_classify_route_detects_challenge_and_assets() -> None:
    assert classify_route("https://5ka.ru/xpvnsulc/") == "challenge"
    assert classify_route("https://5ka.ru/api/orders/v1/cart") == "product_api"
    assert classify_route("https://5ka.ru/static/app.js", "application/javascript") == "asset_script"
    assert classify_route("https://5ka.ru/image/product.webp") == "asset_image"


def test_interception_summary_collects_replay_candidates() -> None:
    event = build_interception_event(
        method="GET",
        status=200,
        url="https://5ka.ru/api/search/products",
        content_type="application/json",
        payload_text='{"products":[{"plu":"10","title":"Salmon","prices":{"regular":200}}]}',
    ).as_report_dict()

    summary = summarize_interception_events([event])

    assert summary["route_counts"] == {"product_api": 1}
    assert summary["replay_candidates"][0]["candidate_product_count"] == 1
    assert summary["schema_candidates"][0]["schema_hints"]["has_price_key"] is True


def test_schema_hints_handles_non_product_json() -> None:
    hints = infer_schema_hints({"meta": {"total": 0}, "items": []})

    assert hints["product_like_objects"] == 0
    assert "meta" in hints["top_keys"]


def test_sanitize_diagnostic_url_masks_sensitive_query_values() -> None:
    sanitized = sanitize_diagnostic_url("https://5ka.ru/api?session=secret&city=moscow")

    assert "secret" not in sanitized
    assert "city=moscow" in sanitized


def test_sanitize_diagnostic_url_masks_challenge_query_values() -> None:
    sanitized = sanitize_diagnostic_url(
        "https://5ka.ru/xpvnsulc/?hcheck=abc&request_id=rid&oirutpspca=token&city=moscow"
    )

    assert "abc" not in sanitized
    assert "rid" not in sanitized
    assert "token" not in sanitized
    assert "city=moscow" in sanitized


def test_payload_preview_redacts_sensitive_json_fields() -> None:
    preview = payload_preview(
        '{"products":[{"id":"1","name":"Fish","price":100}],"accessToken":"secret","cookie":"raw"}'
    )

    assert "Fish" in preview
    assert "secret" not in preview
    assert "raw" not in preview
    assert '"accessToken": "***"' in preview
