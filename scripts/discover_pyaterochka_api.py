"""Passively discover Pyaterochka catalog API calls in visible Camoufox."""

from __future__ import annotations

import argparse
import asyncio
import json
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

from scripts.smoke_pyaterochka_camoufox import DEFAULT_CATEGORY, PROFILE_DIR  # noqa: E402
from utils.api_discovery import (  # noqa: E402
    build_discovery_result,
    build_markdown_report,
)
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console  # noqa: E402
from utils.env import load_dotenv_file  # noqa: E402
from utils.kb_loader import KBLoader  # noqa: E402
from utils.network_capture import record_api_discovery_response  # noqa: E402
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls, mask_proxy_url  # noqa: E402
from utils.proxy_history import ProxyHistoryStore, build_proxy_attempt_record  # noqa: E402
from utils.rate_profile import protected_store_rate_profile  # noqa: E402
from utils.run_context import RunContext  # noqa: E402
from utils.session_pool import SessionPool  # noqa: E402
from utils.site_error_tracking import attach_site_error_summary  # noqa: E402

OUTPUT_DIR = ROOT_DIR / "data"
PROXY_ENV = "PARSER_PROXY"


async def _record_response(response: Any, events: list[dict[str, Any]]) -> None:
    """Capture safe response diagnostics for interesting API calls."""
    captured = await record_api_discovery_response(response, events)
    if captured:
        logger.info("Captured API response {}", response.url)


async def discover_pyaterochka_api(
    category_name: str = DEFAULT_CATEGORY,
    listen_seconds: int = 180,
    headless: bool | str | None = None,
) -> dict[str, Any]:
    """Open Pyaterochka and passively capture catalog API responses."""
    configure_windows_console()
    load_dotenv_file(ROOT_DIR / ".env")
    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop("pyaterochka")
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
        events = await _capture_events(category_url, kb.headers.custom, launch_options, listen_seconds)
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
) -> list[dict[str, Any]]:
    """Open a browser and passively collect relevant API responses."""
    events: list[dict[str, Any]] = []
    tasks: set[asyncio.Task[None]] = set()
    async with AsyncCamoufox(**launch_options) as browser:
        page = await browser.new_page()

        def track_response(response: Any) -> None:
            task = asyncio.create_task(_record_response(response, events))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        page.on("response", track_response)
        if headers:
            await page.set_extra_http_headers(headers)
        logger.info("Opening {}", category_url)
        await page.goto(category_url, wait_until="domcontentloaded", timeout=60_000)
        await asyncio.to_thread(
            input,
            "Solve captcha if needed, then press Enter. After that, scroll/open catalog pages...",
        )
        logger.info("Listening for catalog API responses for {} seconds", listen_seconds)
        await page.wait_for_timeout(listen_seconds * 1000)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    return events


def _write_outputs(result: dict[str, Any]) -> tuple[Path, Path]:
    """Write JSON and Markdown discovery reports."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "pyaterochka_api_discovery.json"
    md_path = OUTPUT_DIR / "pyaterochka_api_discovery.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(build_markdown_report(result), encoding="utf-8")
    return json_path, md_path


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Discover Pyaterochka catalog API responses")
    parser.add_argument("--category", default=DEFAULT_CATEGORY)
    parser.add_argument("--listen-seconds", type=int, default=180)
    parser.add_argument("--headless", action="store_true", default=None)
    parser.add_argument("--no-headless", action="store_false", dest="headless")
    return parser.parse_args()


if __name__ == "__main__":
    if sys.platform == "win32":
        warnings.filterwarnings("ignore", category=ResourceWarning)
    args = _parse_args()
    result_payload = asyncio.run(
        discover_pyaterochka_api(
            category_name=args.category,
            listen_seconds=args.listen_seconds,
            headless=args.headless,
        )
    )
    output_path, report_path = _write_outputs(result_payload)
    logger.info("Discovery JSON saved: {}", output_path)
    logger.info("Discovery report saved: {}", report_path)
