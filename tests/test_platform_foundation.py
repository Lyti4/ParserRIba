import random

from utils.rate_profile import RateProfile
from utils.run_context import RunContext, StoreState
from utils.session_pool import SessionPool


def test_rate_profile_uses_long_cooldown_for_captcha() -> None:
    profile = RateProfile(block_cooldown_ms=(300_000, 300_000))

    assert profile.cooldown_for_reason("pyaterochka_rotate_image_captcha", random.Random(1)) == 300_000


def test_run_context_creates_attempt_context() -> None:
    run = RunContext(store="pyaterochka", mode="discovery")
    attempt = run.start_attempt(attempt=1, proxy="http://***:***@example.com:1000", session_id="s1")
    attempt.store_state = StoreState(store_id="35XY", selected_store_detected=True)
    attempt.finish("blocked", "captcha")

    summary = attempt.summary()

    assert summary["run_id"] == run.run_id
    assert summary["status"] == "blocked"
    assert summary["store_state"]["store_id"] == "35XY"


def test_session_pool_masks_proxy_in_summary() -> None:
    pool = SessionPool("pyaterochka", ["http://user:secret@example.com:1000"])
    session = pool.acquire()
    pool.record_failure(session.session_id, "captcha", cooldown_ms=1_000)

    summary = pool.summary()

    assert summary["total_sessions"] == 1
    assert summary["sessions"][0]["proxy_url"] == "http://***:***@example.com:1000"
    assert "secret" not in str(summary)


def test_session_pool_rotates_when_current_session_quarantined() -> None:
    pool = SessionPool("pyaterochka", ["http://one:1000", "http://two:1000"])
    first = pool.acquire()
    pool.record_failure(first.session_id, "http_429", cooldown_ms=60_000)
    second = pool.acquire()

    assert second.session_id != first.session_id
    assert second.proxy_url == "http://two:1000"
