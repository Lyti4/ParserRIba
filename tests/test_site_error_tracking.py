from utils.site_error_tracking import (
    attach_site_error_summary,
    build_browser_observations,
    build_site_error_summary,
)


def test_site_error_summary_groups_network_proxy_and_challenge() -> None:
    summary = build_site_error_summary(
        {
            "blocked": True,
            "block_reason": "pyaterochka_rotate_image_captcha",
            "navigation_error": "Page.goto: timeout",
            "network": {
                "status_counts": {"200": 10, "403": 1, "429": 2},
                "failure_counts": {"NS_ERROR_PROXY_CONNECTION_REFUSED": 1},
                "empty_product_api_samples": [{"url": "https://5ka.ru/api/catalog"}],
            },
            "proxy_diagnostics": {
                "preflight": {"enabled": True, "ok": False, "error": "proxy timeout"},
                "health": {"status": "preflight_failed", "traffic_risk": "high", "notes": ["route failed"]},
            },
            "product_api_diagnostics": {"page_context": {"selected_store_detected": False}},
        }
    )

    assert summary["total"] >= 7
    assert summary["code_counts"]["pyaterochka_rotate_image_captcha"] == 1
    assert summary["code_counts"]["http_403_forbidden_or_challenge"] == 1
    assert summary["code_counts"]["http_429_rate_limited"] == 1
    assert summary["source_counts"]["proxy"] == 2


def test_attach_site_error_summary_skips_clean_result() -> None:
    result = {"blocked": False, "block_reason": "ok", "network": {"status_counts": {"200": 5}}}

    attach_site_error_summary(result)

    assert "site_errors" not in result


def test_discovery_without_product_payload_is_tracked() -> None:
    summary = build_site_error_summary(
        {
            "events_count": 3,
            "product_events_count": 0,
            "status_counts": {"200": 3},
        }
    )

    assert summary["code_counts"]["api_discovery_no_product_payload"] == 1


def test_browser_observations_from_mcp_feed_site_errors() -> None:
    observations = build_browser_observations(
        console_messages=[
            {"level": "error", "text": "Uncaught TypeError: failed catalog render"},
            {"level": "info", "text": "hydrated"},
            "Warning: blocked third-party script",
        ],
        network_requests=[
            {"method": "GET", "status": 403, "url": "https://5ka.ru/xpvnsulc/"},
            {"method": "GET", "failure": "net::ERR_TUNNEL_CONNECTION_FAILED", "url": "https://5ka.ru/api"},
        ],
    )

    summary = build_site_error_summary({"browser_observations": observations})

    assert summary["code_counts"]["browser_console_error"] == 1
    assert summary["code_counts"]["browser_console_warning"] == 1
    assert summary["code_counts"]["http_403_forbidden_or_challenge"] == 1
    assert summary["code_counts"]["mcp_network_request_failed"] == 1
    assert summary["source_counts"]["mcp_console"] == 2
    assert summary["source_counts"]["mcp_network"] == 2
