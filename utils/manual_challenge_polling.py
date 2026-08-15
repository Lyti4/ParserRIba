"""Dependency-light polling for a human-resolved browser challenge."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from utils.challenge_handoff import ChallengeWaitResult, wait_for_challenge_resolution

DiagnosticsCollector = Callable[[Any, Any], Awaitable[Any]]
CardFinder = Callable[[Any, list[str]], Awaitable[list[Any]]]


def is_transient_page_navigation_error(error: Exception) -> bool:
    """Return true only for Playwright's page-content navigation race."""
    message = str(error).lower()
    return "page.content" in message and "page is navigating and changing the content" in message


async def wait_for_cards_after_manual_challenge(
    *,
    page: Any,
    response: Any,
    card_selectors: list[str],
    collect_diagnostics: DiagnosticsCollector,
    find_cards: CardFinder,
    timeout_ms: int,
    initial_diagnostics: Any = None,
    resolved_url_markers: tuple[str, ...] = (),
) -> tuple[Any, list[Any], ChallengeWaitResult]:
    """Wait for cards or a verified unblocked destination after human action."""
    last_diagnostics = initial_diagnostics
    if last_diagnostics is None:
        last_diagnostics = await collect_diagnostics(page, response)
    last_cards: list[Any] = []

    async def cards_ready() -> bool:
        nonlocal last_diagnostics, last_cards
        try:
            last_diagnostics = await collect_diagnostics(page, response)
            last_cards = await find_cards(page, card_selectors)
        except Exception as error:
            if not is_transient_page_navigation_error(error):
                raise
            return False
        final_url = str(getattr(last_diagnostics, "final_url", "")).lower()
        challenge_cleared = not bool(getattr(last_diagnostics, "blocked", True))
        reached_expected_page = bool(resolved_url_markers) and any(
            marker.lower() in final_url for marker in resolved_url_markers
        )
        return bool(last_cards) or (challenge_cleared and reached_expected_page)

    async def browser_wait(seconds: float) -> None:
        await page.wait_for_timeout(max(1, int(seconds * 1_000)))

    wait_result = await wait_for_challenge_resolution(
        cards_ready,
        timeout_seconds=timeout_ms / 1_000,
        poll_interval_seconds=1,
        sleep=browser_wait,
    )
    return last_diagnostics, last_cards, wait_result
