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


def test_build_pyaterochka_smoke_report_products() -> None:
    report = build_pyaterochka_smoke_report(
        {
            "blocked": False,
            "block_reason": "ok",
            "http_status": 200,
            "cards_found": 1,
            "final_url": "https://5ka.ru/catalog/",
            "html_size": 999,
            "proxy_enabled": True,
            "proxy": "http://user:***@proxy.example:1000",
            "browser_external_ip": "203.0.113.10",
            "geoip_enabled": True,
            "html_path": "data/page.html",
            "screenshot_path": "data/page.png",
            "products_sample": [
                {
                    "name": "Fish",
                    "price": "100",
                    "link": "https://5ka.ru/product",
                }
            ],
        }
    )

    assert "Status: ok" in report
    assert "Proxy enabled: True" in report
    assert "Browser external IP: 203.0.113.10" in report
    assert "Fish | 100 | https://5ka.ru/product" in report
