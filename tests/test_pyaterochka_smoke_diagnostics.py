from scripts.smoke_pyaterochka_camoufox import (
    _build_network_summary,
    _extract_page_context,
    _payload_has_empty_products,
    _sanitize_diagnostic_url,
)


def test_sanitize_diagnostic_url_masks_sensitive_query_values() -> None:
    url = "https://5ka.ru/api/catalog?token=abc&city=moscow&session=secret"

    sanitized = _sanitize_diagnostic_url(url)

    assert "token=%2A%2A%2A" in sanitized
    assert "session=%2A%2A%2A" in sanitized
    assert "city=moscow" in sanitized
    assert "abc" not in sanitized
    assert "secret" not in sanitized


def test_payload_has_empty_products_detects_common_shapes() -> None:
    assert _payload_has_empty_products('{"products": []}')
    assert _payload_has_empty_products('{"productsList": [], "productsResponse": null}')
    assert not _payload_has_empty_products('{"products": [{"name": "Fish"}]}')


def test_extract_page_context_detects_store_region_and_empty_products() -> None:
    html = """
    <script id="__NEXT_DATA__">
    {"catalogStore":{"selectedStore":{"id":"1"},"address":"Москва","productsList":[],"products":[],"productsResponse":null}}
    </script>
    """

    context = _extract_page_context(html)

    assert context["next_data_present"] is True
    assert context["catalog_store_present"] is True
    assert context["selected_store_detected"] is True
    assert context["address_detected"] is True
    assert context["region_hint_detected"] is True
    assert context["products_list_empty"] is True
    assert context["products_empty"] is True
    assert context["products_response_null"] is True


def test_build_network_summary_groups_product_api_samples() -> None:
    summary = _build_network_summary(
        [
            {"status": 200, "url": "https://5ka.ru/api/catalog/products", "empty_products_payload": True},
            {"status": 200, "url": "https://5ka.ru/static/app.js"},
            {"status": 403, "url": "https://5ka.ru/xpvnsulc/"},
        ]
    )

    assert summary["responses"] == 3
    assert summary["status_counts"] == {"200": 2, "403": 1}
    assert len(summary["product_api_samples"]) == 1
    assert len(summary["empty_product_api_samples"]) == 1
    assert summary["error_samples"][0]["status"] == 403
