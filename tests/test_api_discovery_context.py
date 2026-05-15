from utils.api_discovery import build_discovery_result, build_markdown_report


def test_build_discovery_result_accepts_platform_context() -> None:
    result = build_discovery_result(
        category_name="fish",
        category_url="https://5ka.ru/catalog/ryba--251C13077/",
        proxy_url="http://user:pass@example.com:1000",
        geoip_enabled=True,
        listen_seconds=10,
        events=[],
        run={"run_id": "run-1", "mode": "api-discovery"},
        attempt={"status": "empty", "reason": "no_product_payload"},
        session={"session_id": "session-1", "proxy_url": "http://***:***@example.com:1000"},
        rate_profile={"name": "pyaterochka-discovery", "max_concurrency": 1},
    )
    report = build_markdown_report(result)

    assert result["run"]["run_id"] == "run-1"
    assert result["session"]["proxy_url"] == "http://***:***@example.com:1000"
    assert "Run Context" in report
    assert "pyaterochka-discovery" in report
