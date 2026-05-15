from utils.proxy_history import (
    ProxyHistoryStore,
    build_proxy_attempt_record,
    proxy_key,
)


def test_proxy_history_records_masked_proxy_only(tmp_path) -> None:
    store = ProxyHistoryStore(tmp_path / "proxy_history.db")
    proxy_url = "http://user:secret@example.com:1000"
    record = build_proxy_attempt_record(
        store="pyaterochka",
        proxy_url=proxy_url,
        session_id="session-1",
        run_id="run-1",
        result={
            "cards_found": 3,
            "blocked": False,
            "browser_external_ip": "203.0.113.10",
            "network": {
                "responses": 12,
                "estimated_body_bytes": 4096,
                "status_counts": {"200": 12},
                "failure_counts": {},
            },
            "proxy_diagnostics": {
                "health": {"status": "ok", "traffic_risk": "low"},
                "preflight": {"ok": True, "ip": "203.0.113.10"},
            },
            "attempt_context": {"duration_ms": 1500},
        },
    )

    store.record_attempt(record)
    summary = store.summary("pyaterochka", [proxy_url])

    assert summary["known_proxies"] == 1
    assert summary["stats"][0]["successes"] == 1
    assert summary["stats"][0]["proxy"] == "http://***:***@example.com:1000"
    assert "secret" not in str(summary)
    assert proxy_key(proxy_url) in str(summary)


def test_proxy_history_ranks_recently_successful_proxy_first(tmp_path) -> None:
    store = ProxyHistoryStore(tmp_path / "proxy_history.db")
    good = "http://good:1000"
    bad = "http://bad:1000"

    store.record_attempt(
        build_proxy_attempt_record(
            store="pyaterochka",
            proxy_url=bad,
            session_id="bad-session",
            run_id="run-1",
            result={
                "blocked": True,
                "block_reason": "http_429",
                "network": {"responses": 2, "status_counts": {"429": 1}, "failure_counts": {}},
                "proxy_diagnostics": {"health": {"status": "rate_limited", "traffic_risk": "medium"}},
            },
        )
    )
    store.record_attempt(
        build_proxy_attempt_record(
            store="pyaterochka",
            proxy_url=good,
            session_id="good-session",
            run_id="run-1",
            result={
                "cards_found": 4,
                "blocked": False,
                "network": {"responses": 30, "estimated_body_bytes": 8000, "status_counts": {"200": 30}},
                "proxy_diagnostics": {"health": {"status": "ok", "traffic_risk": "low"}},
            },
        )
    )

    assert store.rank_proxy_urls("pyaterochka", [bad, good]) == [good, bad]


def test_proxy_attempt_record_uses_proxy_health_when_no_block_reason() -> None:
    record = build_proxy_attempt_record(
        store="pyaterochka",
        proxy_url="http://proxy:1000",
        session_id="session-1",
        run_id="run-1",
        result={
            "blocked": False,
            "network": {"responses": 1, "status_counts": {}, "failure_counts": {"timeout": 1}},
            "proxy_diagnostics": {"health": {"status": "network_failures", "traffic_risk": "medium"}},
        },
    )

    assert record.reason == "network_failures"
    assert record.failure_counts == {"timeout": 1}
