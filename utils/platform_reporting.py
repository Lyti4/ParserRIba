"""Helpers for attaching platform context to diagnostic reports."""

from __future__ import annotations

from typing import Any

from utils.rate_profile import RateProfile
from utils.run_context import AttemptContext, RunContext
from utils.session_pool import ParserSession, SessionPool


def finish_attempt_from_result(
    attempt_context: AttemptContext,
    result: dict[str, Any],
    *,
    success_reason: str = "ok",
) -> None:
    """Set final attempt status from a parser diagnostic result."""
    reason = str(result.get("block_reason") or result.get("reason") or "")
    if result.get("cards_found", 0) > 0 and not result.get("blocked"):
        attempt_context.finish("ok", success_reason)
    elif result.get("blocked"):
        attempt_context.finish("blocked", reason or "blocked")
    else:
        attempt_context.finish("empty", reason or "empty_result")


def attach_platform_context(
    result: dict[str, Any],
    *,
    run_context: RunContext,
    attempt_context: AttemptContext,
    session: ParserSession,
    rate_profile: dict[str, Any],
) -> None:
    """Attach report-safe platform context to a result dictionary."""
    result["run"] = run_context.summary()
    result["attempt_context"] = attempt_context.summary()
    result["session"] = session.summary()
    result["rate_profile"] = rate_profile


def record_session_outcome(
    session_pool: SessionPool,
    session: ParserSession,
    result: dict[str, Any],
    rate_profile: RateProfile,
) -> None:
    """Update session health from a diagnostic result."""
    if result.get("cards_found", 0) > 0 and not result.get("blocked"):
        session_pool.record_success(session.session_id)
        return
    reason = str(result.get("block_reason") or result.get("reason") or "empty_result")
    session_pool.record_failure(
        session.session_id,
        reason,
        cooldown_ms=rate_profile.cooldown_for_reason(reason),
    )
