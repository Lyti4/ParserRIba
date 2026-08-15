"""Smoke test for Pyaterochka parsing through AsyncCamoufox.

This script intentionally avoids the current parser inheritance layer because
it is being repaired separately. It validates the important path first:
Knowledge Base -> Camoufox browser -> Pyaterochka category page -> product cards.
"""
# ruff: noqa: E402

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
import sys
import warnings
from pathlib import Path
from typing import Any

from camoufox.async_api import AsyncCamoufox
from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from application.url_safety import is_explicit_http_url
from utils.antibot import (
    classify_navigation_error,
    collect_page_diagnostics,
    wait_for_pyaterochka_state,
)
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console
from utils.challenge_handoff import (
    ChallengeCheckpoint,
    ChallengeCheckpointState,
    ChallengeWaitStatus,
    challenge_view_url,
    resolve_challenge_browser_headless,
    set_challenge_access,
    write_challenge_checkpoint,
)
from utils.env import load_dotenv_file
from utils.human_behavior import (
    browse_category_page,
    build_category_behavior_profile,
    cooldown_for_reason,
)
from utils.kb_loader import KBLoader
from utils.manual_challenge_polling import wait_for_cards_after_manual_challenge
from utils.network_capture import (
    payload_has_empty_products,
    record_network_failure,
    record_network_response,
    run_proxy_preflight,
    sanitize_diagnostic_url,
)
from utils.network_diagnostics import build_network_summary, classify_proxy_health, is_product_api_url
from utils.page_context import extract_pyaterochka_page_context
from utils.platform_reporting import (
    attach_platform_context,
    finish_attempt_from_result,
    record_session_outcome,
)
from utils.product_sampling import find_cards
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls, mask_proxy_url
from utils.proxy_history import ProxyHistoryStore, build_proxy_attempt_record
from utils.rate_profile import protected_store_rate_profile
from utils.run_context import AttemptContext, RunContext
from utils.session_pool import ParserSession, SessionPool
from scripts.smoke_pyaterochka_support import (
    SmokeCooldownPage,
    build_attempt_result,
    failed_attempt_result,
    parse_args,
    split_selectors,
    write_smoke_outputs,
)

OUTPUT_DIR = ROOT_DIR / "data"
PROFILE_DIR = ROOT_DIR / "profiles" / "pyaterochka"
DEFAULT_CATEGORY = "Рыба"
PROXY_ENV = "PARSER_PROXY"
PROXY_PREFLIGHT_URL = "https://api.ipify.org?format=json"
CHALLENGE_VIEW_URL_ENV = "PARSERRIBA_CHALLENGE_VIEW_URL"
CHALLENGE_ACCESS_UNIT_ENV = "PARSERRIBA_CHALLENGE_ACCESS_UNIT"
CHALLENGE_CHECKPOINT_PATH = OUTPUT_DIR / "pyaterochka_challenge_checkpoint.json"


def _log_smoke_summary(result: dict[str, Any]) -> None:
    """Log only aggregate counts; raw product evidence is validated downstream."""
    products = result.get("products_sample")
    products_count = len(products) if isinstance(products, list) else 0
    logger.info("Cards found: {}", result.get("cards_found", 0))
    logger.info("Products sampled: {}", products_count)


async def _find_cards(page: Any, selectors: list[str]) -> list[Any]:
    """Find product cards using KB selectors."""
    return await find_cards(page, selectors)


def _build_network_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a compact network summary for smoke diagnostics."""
    return build_network_summary(events)


def _classify_proxy_health(
    *,
    proxy_enabled: bool,
    preflight: dict[str, Any],
    network: dict[str, Any],
    browser_external_ip: str,
) -> dict[str, Any]:
    """Classify practical proxy health signals without provider API access."""
    return classify_proxy_health(
        proxy_enabled=proxy_enabled,
        preflight=preflight,
        network=network,
        browser_external_ip=browser_external_ip,
    )


def _extract_page_context(page_html: str) -> dict[str, Any]:
    """Extract store/region/product state hints from saved page HTML."""
    return extract_pyaterochka_page_context(page_html)


def _payload_has_empty_products(payload: str) -> bool:
    """Detect product API payloads that explicitly contain empty product lists."""
    return payload_has_empty_products(payload)


def _sanitize_diagnostic_url(url: str, max_length: int = 260) -> str:
    """Mask sensitive query values before writing diagnostic URLs."""
    return sanitize_diagnostic_url(url, max_length=max_length)


def _is_product_api_url(url: Any) -> bool:
    """Return True when a URL looks relevant to catalog/product diagnostics."""
    return is_product_api_url(url)


async def _record_network_response(item: Any, network_events: list[dict[str, Any]]) -> None:
    """Record a response and a small product API payload diagnostic when safe."""
    await record_network_response(item, network_events, product_api_checker=_is_product_api_url)


async def _record_network_failure(item: Any, network_events: list[dict[str, Any]]) -> None:
    """Record failed requests without leaking query secrets."""
    await record_network_failure(item, network_events)


async def _run_proxy_preflight(page: Any, proxy_url: str) -> dict[str, Any]:
    """Check that the browser can pass a small request through the proxy."""
    return await run_proxy_preflight(page, proxy_url, preflight_url=PROXY_PREFLIGHT_URL)


async def smoke_parse_pyaterochka(
    category_name: str = DEFAULT_CATEGORY,
    category_url_override: str | None = None,
    output_dir: Path = OUTPUT_DIR,
    persist_operational_outputs: bool = True,
    attempts: int = 3,
    headless: bool | str | None = None,
    pause: bool = False,
    block_images: bool = True,
    persistent_profile: bool = False,
    manual_wait: bool = False,
    manual_wait_timeout_seconds: float = 600,
) -> dict[str, Any]:
    """Open Pyaterochka category through Camoufox and collect a small sample."""
    if category_url_override is not None and not is_explicit_http_url(
        category_url_override, require_https=True
    ):
        raise RuntimeError("LIVE_BROWSER_SOURCE_LOCATOR_INVALID")
    configure_windows_console()
    load_dotenv_file(ROOT_DIR / ".env")

    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop("pyaterochka")
    category_url = category_url_override.strip() if category_url_override is not None else kb.categories.get(category_name)
    if not category_url:
        raise RuntimeError("LIVE_BROWSER_SOURCE_LOCATOR_MISSING")
    if not is_explicit_http_url(category_url, require_https=True):
        raise RuntimeError("LIVE_BROWSER_SOURCE_LOCATOR_INVALID")

    logger.info("Starting Camoufox for Pyaterochka smoke test")
    logger.info("Category: {} -> {}", category_name, category_url)

    output_dir = output_dir.resolve()
    proxy_urls = load_proxy_urls(
        primary=os.environ.get(PROXY_ENV, ""),
        pool=os.environ.get("PARSER_PROXIES", ""),
    )
    proxy_history = ProxyHistoryStore(output_dir / "proxy_history.db")
    proxy_urls = proxy_history.rank_proxy_urls("pyaterochka", proxy_urls)
    geoip_enabled = os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    configured_challenge_view = os.environ.get(CHALLENGE_VIEW_URL_ENV, "")
    configured_challenge_access_unit = os.environ.get(CHALLENGE_ACCESS_UNIT_ENV, "")
    browser_headless = resolve_challenge_browser_headless(
        headless,
        challenge_view=configured_challenge_view,
        platform=sys.platform,
    )

    final_result: dict[str, Any] | None = None
    attempt_results: list[dict[str, Any]] = []
    rate_profile = protected_store_rate_profile("pyaterochka-smoke")
    run_context = RunContext(store="pyaterochka", mode="visual-smoke", rate_profile=rate_profile.name)
    session_pool = SessionPool("pyaterochka", proxy_urls=proxy_urls)
    for attempt in range(1, attempts + 1):
        session = session_pool.acquire()
        proxy_url = session.proxy_url or choose_proxy_for_attempt(proxy_urls, attempt)
        attempt_context = run_context.start_attempt(
            attempt=attempt,
            proxy=mask_proxy_url(proxy_url) if proxy_url else "",
            session_id=session.session_id,
        )
        if proxy_url:
            logger.info("Smoke attempt {} uses proxy {}", attempt, mask_proxy_url(proxy_url))
        else:
            logger.info("Smoke attempt {} runs without proxy", attempt)

        launch_options = build_camoufox_options(
            headless=browser_headless,
            proxy_url=proxy_url,
            geoip=geoip_enabled,
            block_images=block_images,
            block_webgl=False,
            humanize=True,
            fingerprint_os="windows",
            user_data_dir=PROFILE_DIR if persistent_profile else None,
        )
        try:
            final_result = await _run_smoke_attempt(
                kb=kb,
                category_name=category_name,
                category_url=category_url,
                launch_options=launch_options,
                proxy_url=proxy_url,
                geoip_enabled=geoip_enabled,
                attempt=attempt,
                attempts=attempts,
                pause=pause,
                manual_wait=manual_wait,
                manual_wait_timeout_seconds=manual_wait_timeout_seconds,
                challenge_view=configured_challenge_view,
                challenge_access_unit=configured_challenge_access_unit,
                output_dir=output_dir,
                persist_operational_outputs=persist_operational_outputs,
                run_context=run_context,
                attempt_context=attempt_context,
                session=session,
                rate_profile=rate_profile.summary(),
            )
        except Exception as exc:
            logger.warning("Smoke attempt {} failed: {}", attempt, exc)
            final_result = failed_attempt_result(category_name, category_url, attempt, attempts, exc)
            finish_attempt_from_result(attempt_context, final_result, success_reason="cards_found")
            attach_platform_context(
                final_result,
                run_context=run_context,
                attempt_context=attempt_context,
                session=session,
                rate_profile=rate_profile.summary(),
            )
        record_session_outcome(session_pool, session, final_result, rate_profile)
        if proxy_url:
            proxy_history.record_attempt(
                build_proxy_attempt_record(
                    store="pyaterochka",
                    proxy_url=proxy_url,
                    session_id=session.session_id,
                    run_id=run_context.run_id,
                    result=final_result,
                )
            )
        attempt_results.append(
            {
                "attempt": attempt,
                "blocked": final_result.get("blocked"),
                "block_reason": final_result.get("block_reason"),
                "cards_found": final_result.get("cards_found", 0),
                "proxy": final_result.get("proxy", ""),
                "session_id": session.session_id,
            }
        )
        if final_result.get("cards_found", 0) > 0 and not final_result.get("blocked"):
            break
        if attempt < attempts:
            reason = str(final_result.get("block_reason") or "empty_result")
            await cooldown_for_reason(SmokeCooldownPage(), reason, build_category_behavior_profile(category_name))

    result = final_result or failed_attempt_result(
        category_name, category_url, 0, attempts, RuntimeError("no attempts executed")
    )
    result["attempts"] = attempt_results
    result["proxy_history"] = proxy_history.summary("pyaterochka", proxy_urls)

    if persist_operational_outputs:
        output_path, report_path = write_smoke_outputs(result, output_dir)
        logger.info("Smoke result saved: {}", output_path)
        logger.info("Smoke report saved: {}", report_path)
    _log_smoke_summary(result)
    return result
async def _run_smoke_attempt(
    kb: Any,
    category_name: str,
    category_url: str,
    launch_options: dict[str, Any],
    proxy_url: str,
    geoip_enabled: bool,
    attempt: int,
    attempts: int,
    pause: bool,
    manual_wait: bool,
    manual_wait_timeout_seconds: float,
    challenge_view: str,
    challenge_access_unit: str,
    output_dir: Path,
    persist_operational_outputs: bool,
    run_context: RunContext,
    attempt_context: AttemptContext,
    session: ParserSession,
    rate_profile: dict[str, Any],
) -> dict[str, Any]:
    """Run one browser/proxy smoke attempt."""
    card_selectors = split_selectors(kb.selectors.get("product_card"))
    name_selectors = split_selectors(kb.selectors.get("product_name"))
    price_selectors = split_selectors(kb.selectors.get("price_current"))
    link_selectors = split_selectors(kb.selectors.get("product_link"))
    behavior_profile = build_category_behavior_profile(category_name)
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()
        network_events: list[dict[str, Any]] = []
        network_tasks: set[asyncio.Task[None]] = set()

        def track_response(item: Any) -> None:
            task = asyncio.create_task(_record_network_response(item, network_events))
            network_tasks.add(task)
            task.add_done_callback(network_tasks.discard)

        def track_request_failed(item: Any) -> None:
            task = asyncio.create_task(_record_network_failure(item, network_events))
            network_tasks.add(task)
            task.add_done_callback(network_tasks.discard)

        page.on(
            "response",
            track_response,
        )
        page.on(
            "requestfailed",
            track_request_failed,
        )
        proxy_preflight = await _run_proxy_preflight(page, proxy_url)
        if kb.headers.custom:
            await page.set_extra_http_headers(kb.headers.custom)
        navigation_error = ""
        response = None
        try:
            response = await page.goto(category_url, wait_until="domcontentloaded", timeout=60_000)
        except Exception as exc:
            navigation_error = str(exc)
            logger.warning("Navigation failed: {}", exc)
        await page.wait_for_timeout(5_000)
        if not navigation_error:
            diagnostics = await wait_for_pyaterochka_state(page, response)
            if not diagnostics.blocked:
                await browse_category_page(page, behavior_profile)
                diagnostics = await wait_for_pyaterochka_state(page, response)
        else:
            diagnostics = await collect_page_diagnostics(page, response)
        manual_wait_enabled = manual_wait and diagnostics.blocked
        if manual_wait_enabled:
            checkpoint_created_at = ""
            checkpoint_path = output_dir / CHALLENGE_CHECKPOINT_PATH.name
            if diagnostics.blocked:
                checkpoint_created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                write_challenge_checkpoint(
                    checkpoint_path,
                    ChallengeCheckpoint(
                        run_id=run_context.run_id,
                        store="pyaterochka",
                        attempt=attempt,
                        state=ChallengeCheckpointState.BLOCKED_CHALLENGE,
                        created_at=checkpoint_created_at,
                        updated_at=checkpoint_created_at,
                    ),
                )
                logger.info("Challenge checkpoint saved: {}", checkpoint_path)
            try:
                access_started = False
                if checkpoint_created_at:
                    access_started = await set_challenge_access(
                        challenge_access_unit,
                        "start",
                        checkpoint_path=checkpoint_path,
                        expected_run_id=run_context.run_id,
                    )
                if challenge_view and access_started:
                    logger.info("Remote challenge view: {}", challenge_view_url(challenge_view))
                logger.info("Manual wait enabled; waiting for product cards without terminal input")
                diagnostics, manual_cards, manual_wait_result = await wait_for_cards_after_manual_challenge(
                    page=page,
                    response=response,
                    card_selectors=card_selectors,
                    collect_diagnostics=collect_page_diagnostics,
                    find_cards=find_cards,
                    timeout_ms=max(1, int(manual_wait_timeout_seconds * 1_000)),
                    initial_diagnostics=diagnostics,
                    resolved_url_markers=("/catalog/",),
                )
            except asyncio.CancelledError:
                if checkpoint_created_at:
                    write_challenge_checkpoint(
                        checkpoint_path,
                        ChallengeCheckpoint(
                            run_id=run_context.run_id,
                            store="pyaterochka",
                            attempt=attempt,
                            state=ChallengeCheckpointState.CANCELLED,
                            created_at=checkpoint_created_at,
                            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        ),
                    )
                raise
            finally:
                if checkpoint_created_at and challenge_access_unit:
                    await asyncio.shield(set_challenge_access(challenge_access_unit, "stop"))
            manual_cards_ready = manual_wait_result.status is ChallengeWaitStatus.RESOLVED
            manual_wait_status = manual_wait_result.status.value
            manual_checkpoint_state = ""
            if checkpoint_created_at:
                checkpoint_state = ChallengeCheckpointState(manual_wait_status)
                write_challenge_checkpoint(
                    checkpoint_path,
                    ChallengeCheckpoint(
                        run_id=run_context.run_id,
                        store="pyaterochka",
                        attempt=attempt,
                        state=checkpoint_state,
                        created_at=checkpoint_created_at,
                        updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    ),
                )
                manual_checkpoint_state = checkpoint_state.value
            logger.info(
                "Post-manual wait finished: status={}, cards_ready={}, cards_found={}",
                manual_wait_status,
                manual_cards_ready,
                len(manual_cards),
            )
            if manual_cards_ready:
                navigation_error = ""
        else:
            manual_cards = []
            manual_cards_ready = False
            manual_wait_status = ""
            manual_checkpoint_state = ""

        if network_tasks:
            await asyncio.gather(*network_tasks, return_exceptions=True)

        result = await build_attempt_result(
            page=page,
            diagnostics=diagnostics,
            navigation_error=navigation_error,
            network_events=network_events,
            proxy_preflight=proxy_preflight,
            card_selectors=card_selectors,
            name_selectors=name_selectors,
            price_selectors=price_selectors,
            link_selectors=link_selectors,
            behavior_profile=behavior_profile,
            category_name=category_name,
            category_url=category_url,
            launch_options=launch_options,
            proxy_url=proxy_url,
            geoip_enabled=geoip_enabled,
            attempt=attempt,
            attempts=attempts,
            output_dir=output_dir,
            navigation_reason=classify_navigation_error(navigation_error),
            persist_operational_outputs=persist_operational_outputs,
            cards_override=manual_cards or None,
            manual_wait=manual_wait_enabled,
            manual_cards_ready=manual_cards_ready,
            manual_wait_status=manual_wait_status,
            manual_checkpoint_state=manual_checkpoint_state,
        )
        finish_attempt_from_result(attempt_context, result, success_reason="cards_found")
        attach_platform_context(
            result,
            run_context=run_context,
            attempt_context=attempt_context,
            session=session,
            rate_profile=rate_profile,
        )
        if pause:
            if network_tasks:
                await asyncio.gather(*network_tasks, return_exceptions=True)
            if persist_operational_outputs:
                output_path, report_path = write_smoke_outputs(result, output_dir)
                logger.info("Smoke result saved before pause: {}", output_path)
                logger.info("Smoke report saved before pause: {}", report_path)
            logger.info("Pause enabled; leave this PowerShell window open to inspect Camoufox")
            while True:
                await page.wait_for_timeout(60_000)
        return result
if __name__ == "__main__":
    if sys.platform == "win32":
        warnings.filterwarnings("ignore", category=ResourceWarning)
    args = parse_args(DEFAULT_CATEGORY)
    asyncio.run(
        smoke_parse_pyaterochka(
            category_name=args.category,
            attempts=args.attempts,
            headless=args.headless,
            pause=args.pause,
            block_images=not args.load_images,
            persistent_profile=args.persistent_profile,
            manual_wait=args.manual_wait,
            manual_wait_timeout_seconds=args.manual_timeout_seconds,
        )
    )
