from utils.platform_reporting import (
    attach_platform_context,
    finish_attempt_from_result,
    record_session_outcome,
)
from utils.rate_profile import RateProfile
from utils.run_context import RunContext
from utils.session_pool import SessionPool


def test_finish_attempt_from_result_marks_cards_as_ok() -> None:
    run = RunContext(store="pyaterochka")
    attempt = run.start_attempt(1)

    finish_attempt_from_result(attempt, {"cards_found": 2, "blocked": False}, success_reason="cards_found")

    assert attempt.status == "ok"
    assert attempt.reason == "cards_found"


def test_attach_platform_context_masks_session_proxy() -> None:
    run = RunContext(store="pyaterochka")
    attempt = run.start_attempt(1, session_id="s1")
    pool = SessionPool("pyaterochka", ["http://user:secret@example.com:1000"])
    session = pool.acquire()
    result: dict[str, object] = {}

    attach_platform_context(
        result,
        run_context=run,
        attempt_context=attempt,
        session=session,
        rate_profile={"name": "test-profile"},
    )

    assert result["run"]["run_id"] == run.run_id
    assert result["session"]["proxy_url"] == "http://***:***@example.com:1000"
    assert "secret" not in str(result)


def test_record_session_outcome_quarantines_failed_session() -> None:
    pool = SessionPool("pyaterochka", ["http://one:1000"])
    session = pool.acquire()
    profile = RateProfile(block_cooldown_ms=(10_000, 10_000))

    record_session_outcome(pool, session, {"blocked": True, "block_reason": "captcha"}, profile)

    assert pool.summary()["available_sessions"] == 0
