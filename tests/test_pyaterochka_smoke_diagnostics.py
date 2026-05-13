from scripts.smoke_pyaterochka_camoufox import (
    _build_network_summary,
    _classify_proxy_health,
    _extract_page_context,
    _is_product_api_url,
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


def test_extract_page_context_treats_store_id_as_selected_store() -> None:
    html = '{"catalogStore":{"storeId":"35XY","productsList":[]}}'

    context = _extract_page_context(html)

    assert context["selected_store_detected"] is True


def test_build_network_summary_groups_product_api_samples() -> None:
    summary = _build_network_summary(
        [
            {"status": 200, "url": "https://5ka.ru/api/catalog/products", "empty_products_payload": True},
            {"status": 200, "url": "https://5ka.ru/static/app.js", "content_length": 1200},
            {"status": 200, "url": "https://api.ipify.org/?format=json"},
            {"status": 200, "url": "https://fonts.googleapis.com/css2?family=Manrope"},
            {"status": 403, "url": "https://5ka.ru/xpvnsulc/"},
            {"failure": "NS_ERROR_PROXY_CONNECTION_REFUSED", "url": "https://5ka.ru/catalog/"},
        ]
    )

    assert summary["responses"] == 6
    assert summary["status_counts"] == {"200": 4, "403": 1}
    assert summary["failure_counts"] == {"NS_ERROR_PROXY_CONNECTION_REFUSED": 1}
    assert summary["estimated_body_bytes"] == 1200
    assert len(summary["product_api_samples"]) == 1
    assert len(summary["empty_product_api_samples"]) == 1
    assert summary["error_samples"][0]["status"] == 403


def test_is_product_api_url_ignores_non_5ka_api_urls() -> None:
    assert _is_product_api_url("https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories")
    assert _is_product_api_url("https://5ka.ru/api/orders/v3/orders")
    assert not _is_product_api_url("https://api.ipify.org/?format=json")
    assert not _is_product_api_url("https://fonts.googleapis.com/css2?family=Manrope")


def test_classify_proxy_health_flags_auth_and_preflight_failures() -> None:
    health = _classify_proxy_health(
        proxy_enabled=True,
        preflight={"ok": False},
        network={
            "responses": 2,
            "status_counts": {"407": 1},
            "failure_counts": {"timeout": 1},
        },
        browser_external_ip="",
    )

    assert health["status"] == "proxy_auth_failed"
    assert health["traffic_risk"] == "high"
    assert any("407" in note for note in health["notes"])


def test_classify_proxy_health_handles_transient_407_after_successful_preflight() -> None:
    health = _classify_proxy_health(
        proxy_enabled=True,
        preflight={"ok": True},
        network={
            "responses": 12,
            "status_counts": {"200": 11, "407": 1},
            "failure_counts": {},
        },
        browser_external_ip="203.0.113.10",
    )

    assert health["status"] == "ok"
    assert health["traffic_risk"] == "medium"
    assert any("transient HTTP 407" in note for note in health["notes"])


def test_classify_proxy_health_reports_low_risk_when_signals_are_clean() -> None:
    health = _classify_proxy_health(
        proxy_enabled=True,
        preflight={"ok": True},
        network={
            "responses": 12,
            "status_counts": {"200": 12},
            "failure_counts": {},
        },
        browser_external_ip="203.0.113.10",
    )

    assert health["status"] == "ok"
    assert health["traffic_risk"] == "low"
