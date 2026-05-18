"""Passively discover Pyaterochka catalog API calls in visible Camoufox."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Any, Callable

from camoufox.async_api import AsyncCamoufox
from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.smoke_pyaterochka_camoufox import DEFAULT_CATEGORY, PROFILE_DIR  # noqa: E402
from utils.api_discovery import (  # noqa: E402
    build_discovery_result,
    build_markdown_report,
)
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console  # noqa: E402
from utils.env import load_dotenv_file  # noqa: E402
from utils.kb_loader import KBLoader  # noqa: E402
from utils.network_capture import record_api_discovery_response  # noqa: E402
from utils.interception_archive import write_interception_archive  # noqa: E402
from utils.interception_profiles import InterceptionProfile, get_interception_profile  # noqa: E402
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls, mask_proxy_url  # noqa: E402
from utils.proxy_history import ProxyHistoryStore, build_proxy_attempt_record  # noqa: E402
from utils.rate_profile import protected_store_rate_profile  # noqa: E402
from utils.run_context import RunContext  # noqa: E402
from utils.session_pool import SessionPool  # noqa: E402
from utils.site_error_tracking import attach_site_error_summary  # noqa: E402

OUTPUT_DIR = ROOT_DIR / "data"
PROXY_ENV = "PARSER_PROXY"
MANUAL_DISCOVERY_PROMPT = "Solve captcha if needed, then press Enter. After that, scroll/open catalog pages..."


async def _record_response(response: Any, events: list[dict[str, Any]], profile: InterceptionProfile) -> None:
    """Capture safe response diagnostics for interesting API calls."""
    captured = await record_api_discovery_response(
        response,
        events,
        profile=profile,
    )
    if captured:
        logger.info("Captured API response {}", response.url)


async def discover_pyaterochka_api(
    category_name: str = DEFAULT_CATEGORY,
    listen_seconds: int = 180,
    headless: bool | str | None = None,
    manual_wait: bool = True,
) -> dict[str, Any]:
    """Open Pyaterochka and passively capture catalog API responses."""
    configure_windows_console()
    load_dotenv_file(ROOT_DIR / ".env")
    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop("pyaterochka")
    interception_profile = get_interception_profile("pyaterochka", knowledge=kb)
    category_url = kb.categories.get(category_name)
    if not category_url:
        category_name, category_url = next(iter(kb.categories.items()))

    proxy_urls = load_proxy_urls(primary=os.environ.get(PROXY_ENV, ""), pool=os.environ.get("PARSER_PROXIES", ""))
    proxy_history = ProxyHistoryStore(OUTPUT_DIR / "proxy_history.db")
    proxy_urls = proxy_history.rank_proxy_urls("pyaterochka", proxy_urls)
    rate_profile = protected_store_rate_profile("pyaterochka-discovery")
    run_context = RunContext(store="pyaterochka", mode="api-discovery", rate_profile=rate_profile.name)
    session_pool = SessionPool("pyaterochka", proxy_urls=proxy_urls)
    session = session_pool.acquire()
    proxy_url = session.proxy_url or choose_proxy_for_attempt(proxy_urls, 1)
    attempt = run_context.start_attempt(attempt=1, proxy=mask_proxy_url(proxy_url) if proxy_url else "", session_id=session.session_id)
    geoip_enabled = os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    browser_headless = headless if headless is not None else (False if sys.platform == "win32" else "virtual")
    launch_options = build_camoufox_options(
        headless=browser_headless,
        proxy_url=proxy_url,
        geoip=geoip_enabled,
        block_images=False,
        block_webgl=False,
        humanize=True,
        fingerprint_os="windows",
        user_data_dir=PROFILE_DIR,
    )
    try:
        events, dom_link_evidence = await _capture_events(
            category_url,
            kb.headers.custom,
            launch_options,
            listen_seconds,
            interception_profile,
            manual_wait=manual_wait,
        )
    except Exception as exc:
        reason = str(exc).splitlines()[0][:200]
        attempt.finish("failed", reason)
        session_pool.record_failure(session.session_id, reason, rate_profile.cooldown_for_reason(reason))
        raise
    if any(event.get("candidate_product_count", 0) > 0 for event in events):
        attempt.finish("ok", "product_payload_captured")
        session_pool.record_success(session.session_id)
    elif any(event.get("empty_products_payload") for event in events):
        attempt.finish("empty", "empty_product_payload")
        session_pool.record_failure(session.session_id, "empty_product_payload", rate_profile.cooldown_for_reason("empty_product_payload"))
    else:
        attempt.finish("empty", "no_product_payload")
        session_pool.record_failure(session.session_id, "no_product_payload", rate_profile.cooldown_for_reason("no_product_payload"))
    result = build_discovery_result(
        category_name=category_name,
        category_url=category_url,
        proxy_url=proxy_url,
        geoip_enabled=geoip_enabled,
        listen_seconds=listen_seconds,
        events=events,
        dom_link_evidence=dom_link_evidence,
        run=run_context.summary(),
        attempt=attempt.summary(),
        session=session.summary(),
        rate_profile=rate_profile.summary(),
    )
    if proxy_url:
        proxy_history.record_attempt(
            build_proxy_attempt_record(
                store="pyaterochka",
                proxy_url=proxy_url,
                session_id=session.session_id,
                run_id=run_context.run_id,
                result=result,
            )
        )
    result["proxy_history"] = proxy_history.summary("pyaterochka", proxy_urls)
    attach_site_error_summary(result)
    return result


async def _capture_events(
    category_url: str,
    headers: dict[str, str],
    launch_options: dict[str, Any],
    listen_seconds: int,
    interception_profile: InterceptionProfile,
    *,
    manual_wait: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Open a browser and passively collect relevant API responses."""
    events: list[dict[str, Any]] = []
    dom_link_evidence: dict[str, Any] = {}
    tasks: set[asyncio.Task[None]] = set()
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()

        def track_response(response: Any) -> None:
            task = asyncio.create_task(_record_response(response, events, interception_profile))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        page.on("response", track_response)
        if headers:
            await page.set_extra_http_headers(headers)
        logger.info("Opening {}", category_url)
        await page.goto(category_url, wait_until="domcontentloaded", timeout=60_000)
        await _wait_for_manual_ready(manual_wait=manual_wait)
        logger.info("Listening for catalog API responses for {} seconds", listen_seconds)
        await page.wait_for_timeout(listen_seconds * 1000)
        dom_link_evidence = await _collect_dom_product_links(page)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    return events, dom_link_evidence


async def _wait_for_manual_ready(
    *,
    manual_wait: bool,
    prompt_func: Callable[[str], Any] = input,
) -> None:
    """Wait for manual captcha/user confirmation when enabled."""
    if not manual_wait:
        logger.info("Skipping manual discovery prompt; listening starts immediately")
        return
    await asyncio.to_thread(prompt_func, MANUAL_DISCOVERY_PROMPT)


async def _collect_dom_product_links(page: Any, *, limit: int = 10) -> dict[str, Any]:
    """Collect visible DOM product links for later comparison with API ids."""
    raw_links = await page.evaluate(
        """
        (limit) => {
          const anchors = Array.from(document.querySelectorAll('a[href*="/product/"]'));
          return anchors.slice(0, Math.max(limit * 3, limit)).map((anchor) => ({
            href: String(anchor.href || '').trim(),
            title: String(anchor.textContent || '').replace(/\\s+/g, ' ').trim(),
          }));
        }
        """,
        limit,
    )
    unique_links: list[dict[str, str]] = []
    seen: set[str] = set()
    product_ids: list[str] = []
    links_by_id: dict[str, str] = {}
    for item in raw_links:
        if not isinstance(item, dict):
            continue
        href = str(item.get("href") or "").strip()
        if not href or href in seen or "/product/" not in href:
            continue
        seen.add(href)
        unique_links.append({"href": href, "title": str(item.get("title") or "").strip()})
        product_id = _extract_product_id_from_href(href)
        if product_id:
            product_ids.append(product_id)
            links_by_id[product_id] = href
        if len(unique_links) >= limit:
            break
    return {
        "count": len(unique_links),
        "sample_links": unique_links,
        "product_ids": product_ids,
        "links_by_id": links_by_id,
    }


def _extract_product_id_from_href(href: str) -> str:
    """Extract numeric product id from a public 5ka product URL."""
    match = re.search(r"/product/[^/]*--(\d+)/?$", href)
    if match:
        return match.group(1)
    return ""


def _write_outputs(result: dict[str, Any]) -> tuple[Path, Path, Path]:
    """Write JSON and Markdown discovery reports."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "pyaterochka_api_discovery.json"
    md_path = OUTPUT_DIR / "pyaterochka_api_discovery.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown_report(result), encoding="utf-8")
    archive_path = write_interception_archive(result, OUTPUT_DIR / "interception")
    return json_path, md_path, archive_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Discover Pyaterochka catalog API responses")
    parser.add_argument("--category", default=DEFAULT_CATEGORY)
    parser.add_argument("--listen-seconds", type=int, default=180)
    parser.add_argument("--headless", action="store_true", default=None)
    parser.add_argument("--no-headless", action="store_false", dest="headless")
    parser.set_defaults(manual_wait=True)
    parser.add_argument("--manual-wait", action="store_true", dest="manual_wait")
    parser.add_argument("--no-manual-wait", action="store_false", dest="manual_wait")
    return parser.parse_args(argv)


if __name__ == "__main__":
    if sys.platform == "win32":
        warnings.filterwarnings("ignore", category=ResourceWarning)
    args = _parse_args()
    result_payload = asyncio.run(
        discover_pyaterochka_api(
            category_name=args.category,
            listen_seconds=args.listen_seconds,
            headless=args.headless,
            manual_wait=args.manual_wait,
        )
    )
    output_path, report_path, archive_path = _write_outputs(result_payload)
    logger.info("Discovery JSON saved: {}", output_path)
    logger.info("Discovery report saved: {}", report_path)
    logger.info("Interception archive saved: {}", archive_path)
