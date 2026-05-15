from utils.smoke_report import build_pyaterochka_smoke_report


def test_build_pyaterochka_smoke_report_blocked() -> None:
    report = build_pyaterochka_smoke_report(
        {
            "blocked": True,
            "block_reason": "pyaterochka_antibot_redirect",
            "http_status": 200,
            "cards_found": 0,
            "final_url": "https://5ka.ru/xpvnsulc/",
            "html_size": 1234,
            "html_path": "data/page.html",
            "screenshot_path": "data/page.png",
            "products_sample": [],
        }
    )

    assert "Status: blocked" in report
    assert "pyaterochka_antibot_redirect" in report
    assert "No sample products" in report


def test_build_pyaterochka_smoke_report_captcha_manual_action() -> None:
    report = build_pyaterochka_smoke_report(
        {
            "blocked": True,
            "block_reason": "pyaterochka_rotate_image_captcha",
            "products_sample": [],
        }
    )

    assert "Manual Action" in report
    assert "run_pyaterochka_visual.ps1" in report


def test_build_pyaterochka_smoke_report_network_action() -> None:
    report = build_pyaterochka_smoke_report(
        {
            "blocked": True,
            "block_reason": "network_dns_error",
            "navigation_error": "Page.goto: NS_ERROR_UNKNOWN_HOST",
            "products_sample": [],
        }
    )

    assert "Network Action" in report
    assert "working RU proxy" in report


def test_build_pyaterochka_smoke_report_products() -> None:
    report = build_pyaterochka_smoke_report(
        {
            "blocked": False,
            "block_reason": "ok",
            "attempt": 2,
            "max_attempts": 3,
            "http_status": 200,
            "cards_found": 1,
            "final_url": "https://5ka.ru/catalog/",
            "html_size": 999,
            "proxy_enabled": True,
            "proxy": "http://user:***@proxy.example:1000",
            "browser_external_ip": "203.0.113.10",
            "geoip_enabled": True,
            "persistent_profile": True,
            "profile_dir": "profiles/pyaterochka",
            "manual_wait": True,
            "manual_cards_ready": True,
            "fingerprint": {
                "engine": "camoufox-browserforge",
                "os": "windows",
                "locale": "ru-RU",
                "humanize": True,
            },
            "behavior_profile": {
                "name": "fish-category",
                "scroll_steps_min": 5,
                "scroll_steps_max": 8,
                "scroll_delta_min": 280,
                "scroll_delta_max": 760,
                "hover_cards": 6,
            },
            "run": {"run_id": "run-1", "mode": "visual-smoke"},
            "attempt_context": {"status": "ok", "reason": "cards_found", "session_id": "session-1"},
            "session": {"proxy_url": "http://***:***@proxy.example:1000", "success_rate": 1.0},
            "rate_profile": {"name": "pyaterochka-smoke", "max_concurrency": 1},
            "html_path": "data/page.html",
            "screenshot_path": "data/page.png",
            "products_sample": [
                {
                    "name": "Fish",
                    "price": "100",
                    "link": "https://5ka.ru/product",
                }
            ],
            "attempts": [
                {
                    "attempt": 1,
                    "blocked": True,
                    "block_reason": "pyaterochka_antibot_redirect",
                    "cards_found": 0,
                    "proxy": "http://***:***@proxy-one.example:1000",
                },
                {
                    "attempt": 2,
                    "blocked": False,
                    "block_reason": "ok",
                    "cards_found": 1,
                    "proxy": "http://***:***@proxy-two.example:1000",
                },
            ],
            "network": {
                "responses": 3,
                "status_counts": {"200": 2, "403": 1},
                "failure_counts": {"timeout": 1},
                "estimated_body_bytes": 12345,
                "error_samples": [{"status": 403, "url": "https://5ka.ru/xpvnsulc/"}],
                "catalog_samples": [{"status": 200, "url": "https://5ka.ru/api/catalog"}],
                "product_api_samples": [
                    {
                        "status": 200,
                        "url": "https://5ka.ru/api/catalog/products",
                        "empty_products_payload": False,
                    }
                ],
                "empty_product_api_samples": [
                    {
                        "status": 200,
                        "url": "https://5ka.ru/api/catalog/products",
                        "empty_products_payload": True,
                        "payload_preview": '{"products":[]}',
                    }
                ],
            },
            "product_api_diagnostics": {
                "page_context": {
                    "next_data_present": True,
                    "catalog_store_present": True,
                    "selected_store_detected": True,
                    "address_detected": True,
                    "region_hint_detected": True,
                    "products_list_empty": False,
                    "products_empty": False,
                    "products_response_null": False,
                }
            },
            "proxy_diagnostics": {
                "preflight": {
                    "enabled": True,
                    "ok": True,
                    "status": 200,
                    "duration_ms": 900,
                    "response_bytes": 24,
                    "ip": "203.0.113.10",
                },
                "health": {
                    "status": "ok",
                    "traffic_risk": "low",
                    "notes": ["No obvious proxy traffic/auth symptoms detected in this run."],
                },
            },
            "site_errors": {
                "total": 2,
                "severity_counts": {"warning": 2},
                "source_counts": {"network": 1, "product_api": 1},
                "code_counts": {"http_403_forbidden_or_challenge": 1, "product_api_empty_payload": 1},
                "events": [
                    {
                        "severity": "warning",
                        "source": "network",
                        "code": "http_403_forbidden_or_challenge",
                        "message": "HTTP 403 responses observed: 1",
                        "count": 1,
                    }
                ],
            },
        }
    )

    assert "Status: ok" in report
    assert "Attempt: 2 / 3" in report
    assert "#1: blocked=True" in report
    assert "Responses: 3" in report
    assert "Failure counts: {'timeout': 1}" in report
    assert "Estimated response bytes: 12345" in report
    assert "403" in report
    assert "Proxy enabled: True" in report
    assert "Browser external IP: 203.0.113.10" in report
    assert "Persistent profile: True" in report
    assert "Manual wait: True" in report
    assert "Manual cards ready: True" in report
    assert "Fingerprint OS: windows" in report
    assert "Behavior profile: fish-category" in report
    assert "Run Context" in report
    assert "pyaterochka-smoke" in report
    assert "Catalog/API samples" in report
    assert "https://5ka.ru/api/catalog" in report
    assert "Proxy Diagnostics" in report
    assert "Proxy health: ok" in report
    assert "Proxy traffic risk: low" in report
    assert "Site Error Tracking" in report
    assert "http_403_forbidden_or_challenge" in report
    assert "Product API Diagnostics" in report
    assert "Selected store detected: True" in report
    assert "empty=False https://5ka.ru/api/catalog/products" in report
    assert '{"products":[]}' in report
    assert "Fish | 100 | https://5ka.ru/product" in report
