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

from scripts.smoke_pyaterochka_camoufox import (  # noqa: E402
    DEFAULT_CATEGORY,
    PROFILE_DIR,
    _payload_has_empty_products,
    _payload_preview,
    _sanitize_diagnostic_url,
)
from utils.api_discovery import (  # noqa: E402
    build_discovery_result,
    build_markdown_report,
    extract_product_candidates,
    is_interesting_api_url,
    safe_json_loads,
    summarize_event,
)
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console  # noqa: E402
from utils.env import load_dotenv_file  # noqa: E402
from utils.kb_loader import KBLoader  # noqa: E402
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls, mask_proxy_url  # noqa: E402

OUTPUT_DIR = ROOT_DIR / "data"
PROXY_ENV = "PARSER_PROXY"


async def _record_response(response: Any, events: list[dict[str, Any]]) -> None:
    """Capture safe response diagnostics for interesting API calls."""
    url = _sanitize_diagnostic_url(str(response.url), max_length=420)
    if not is_interesting_api_url(url):
        return
    event: dict[str, Any] = {
        "method": response.request.method,
        "status": response.status,
        "url": url,
    }
    try:
        headers = await response.all_headers()
    except Exception:
        headers = {}
    content_type = str(headers.get("content-type", ""))
    event["content_type"] = content_type.split(";")[0] if content_type else ""
    if "json" in content_type.lower():
        try:
            payload_text = await response.text()
        except Exception as exc:
            event["error"] = str(exc).splitlines()[0][:200]
        else:
            payload = safe_json_loads(payload_text)
            event["empty_products_payload"] = _payload_has_empty_products(payload_text)
            event["payload_preview"] = _payload_preview(payload_text, max_length=700)
            if payload is not None:
                products = extract_product_candidates(payload)
                event["candidate_product_count"] = len(products)
                event["sample_products"] = products
    events.append(summarize_event(event))
    logger.info("Captured API response {} {}", event.get("status"), url)


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

    proxy_url = choose_proxy_for_attempt(
        load_proxy_urls(primary=os.environ.get(PROXY_ENV, ""), pool=os.environ.get("PARSER_PROXIES", "")),
        1,
    )
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
    events = await _capture_events(category_url, kb.headers.custom, launch_options, listen_seconds)
    return build_discovery_result(
        category_name=category_name,
        category_url=category_url,
        proxy_url=proxy_url,
        geoip_enabled=geoip_enabled,
        listen_seconds=listen_seconds,
        events=events,
    )


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
