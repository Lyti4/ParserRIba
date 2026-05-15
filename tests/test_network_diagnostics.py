from utils.network_diagnostics import (
    build_network_summary,
    classify_proxy_health,
    is_product_api_url,
)


def test_build_network_summary_groups_product_api_samples() -> None:
    summary = build_network_summary(
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
    assert is_product_api_url("https://5d.5ka.ru/api/catalog/v3/stores/35XY/categories")
    assert is_product_api_url("https://5ka.ru/api/orders/v3/orders")
    assert not is_product_api_url("https://api.ipify.org/?format=json")
    assert not is_product_api_url("https://fonts.googleapis.com/css2?family=Manrope")


def test_classify_proxy_health_flags_auth_and_preflight_failures() -> None:
    health = classify_proxy_health(
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
    health = classify_proxy_health(
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
    health = classify_proxy_health(
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
