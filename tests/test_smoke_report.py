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
                "error_samples": [{"status": 403, "url": "https://5ka.ru/xpvnsulc/"}],
            },
        }
    )

    assert "Status: ok" in report
    assert "Attempt: 2 / 3" in report
    assert "#1: blocked=True" in report
    assert "Responses: 3" in report
    assert "403" in report
    assert "Proxy enabled: True" in report
    assert "Browser external IP: 203.0.113.10" in report
    assert "Persistent profile: True" in report
    assert "Fingerprint OS: windows" in report
    assert "Behavior profile: fish-category" in report
    assert "Fish | 100 | https://5ka.ru/product" in report
