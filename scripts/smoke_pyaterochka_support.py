"""Support helpers for the Pyaterochka Camoufox smoke script."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from utils.dom_evidence import build_dom_inventory
from utils.fingerprint import fingerprint_summary_from_options
from utils.human_behavior import hover_product_cards
from utils.network_diagnostics import build_network_summary, classify_proxy_health
from utils.page_context import extract_pyaterochka_page_context
from utils.product_sampling import extract_sample_products, find_cards
from utils.proxy import mask_proxy_url
from utils.site_error_tracking import attach_site_error_summary
from utils.smoke_report import write_smoke_report
from utils.structured_product_evidence import structured_product_evidence_for_result


def split_selectors(selector_config: Any) -> list[str]:
    """Return individual CSS selectors from one KB selector config."""
    if not selector_config or not selector_config.css:
        return []
    return [item.strip() for item in selector_config.css.split("|") if item.strip()]


async def browser_external_ip(page: Any) -> str:
    """Return the external IP observed from inside the browser page."""
    try:
        value = await page.evaluate(
            """async () => {
                const response = await fetch("https://api.ipify.org?format=json", {
                    cache: "no-store"
                });
                const payload = await response.json();
                return payload.ip || "";
            }"""
        )
        return str(value or "")
    except Exception as exc:
        logger.warning("Browser IP check failed: {}", exc)
        return ""


async def build_attempt_result(
    *,
    page: Any,
    diagnostics: Any,
    navigation_error: str,
    network_events: list[dict[str, Any]],
    proxy_preflight: dict[str, Any],
    card_selectors: list[str],
    name_selectors: list[str],
    price_selectors: list[str],
    link_selectors: list[str],
    behavior_profile: Any,
    category_name: str,
    category_url: str,
    launch_options: dict[str, Any],
    proxy_url: str,
    geoip_enabled: bool,
    attempt: int,
    attempts: int,
    output_dir: Path,
    navigation_reason: str,
    persist_operational_outputs: bool = True,
    content_timeout_seconds: float = 10.0,
    cards_override: list[Any] | None = None,
    manual_wait: bool = False,
    manual_cards_ready: bool = False,
    manual_wait_status: str = "",
    manual_checkpoint_state: str = "",
) -> dict[str, Any]:
    """Collect the final smoke result from the current page state."""
    status_blocked = diagnostics.status == 403
    blocked = bool(navigation_reason) or diagnostics.blocked or status_blocked
    if navigation_reason:
        block_reason = navigation_reason
    elif diagnostics.blocked:
        block_reason = diagnostics.reason
    elif status_blocked:
        block_reason = "http_403"
    else:
        block_reason = diagnostics.reason
    external_ip = await browser_external_ip(page)
    try:
        async with asyncio.timeout(content_timeout_seconds):
            page_html = await page.content()
    except Exception as exc:
        logger.warning("Page content unavailable while building smoke result: {}", type(exc).__name__)
        page_html = ""
    dom_inventory = build_dom_inventory(page_html)
    page_context = extract_pyaterochka_page_context(page_html)
    screenshot_path: Path | None = None
    html_path: Path | None = None
    if persist_operational_outputs:
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = output_dir / "pyaterochka_camoufox_smoke.png"
        html_path = output_dir / "pyaterochka_camoufox_smoke.html"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        html_path.write_text(page_html, encoding="utf-8")

    if navigation_error:
        cards = []
    elif cards_override is not None:
        cards = cards_override
    else:
        cards = await find_cards(page, card_selectors)
    if cards:
        await hover_product_cards(page, cards, behavior_profile)
    products = await extract_sample_products(cards, name_selectors, price_selectors, link_selectors)
    structured_product_evidence = structured_product_evidence_for_result(
        page_html,
        base_url=diagnostics.final_url or category_url,
        blocked=blocked,
    )
    network_summary = build_network_summary(network_events)
    proxy_diagnostics = classify_proxy_health(
        proxy_enabled=bool(proxy_url),
        preflight=proxy_preflight,
        network=network_summary,
        browser_external_ip=external_ip,
    )
    result = {
        "shop": "pyaterochka",
        "category": category_name,
        "category_url": category_url,
        "attempt": attempt,
        "max_attempts": attempts,
        "http_status": diagnostics.status,
        "page_title": diagnostics.title,
        "final_url": diagnostics.final_url,
        "html_size": diagnostics.html_size,
        "blocked": blocked,
        "block_reason": block_reason,
        "navigation_error": navigation_error,
        "proxy_enabled": bool(proxy_url),
        "proxy": mask_proxy_url(proxy_url) if proxy_url else "",
        "geoip_enabled": geoip_enabled,
        "persistent_profile": bool(launch_options.get("persistent_context")),
        "profile_dir": str(launch_options.get("user_data_dir", "")),
        "manual_wait": manual_wait,
        "manual_cards_ready": manual_cards_ready,
        "manual_wait_status": manual_wait_status,
        "manual_checkpoint_state": manual_checkpoint_state,
        "fingerprint": fingerprint_summary_from_options(launch_options),
        "behavior_profile": behavior_profile.summary(),
        "browser_external_ip": external_ip,
        "screenshot_path": str(screenshot_path) if screenshot_path is not None else "",
        "html_path": str(html_path) if html_path is not None else "",
        "dom_inventory": dom_inventory,
        "cards_found": len(cards),
        "products_sample": products,
        "structured_product_evidence": structured_product_evidence,
        "network": network_summary,
        "proxy_diagnostics": {
            "preflight": proxy_preflight,
            "health": proxy_diagnostics,
        },
        "product_api_diagnostics": {
            "page_context": page_context,
        },
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
    }
    attach_site_error_summary(result)
    return result


def write_smoke_outputs(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write smoke JSON and Markdown outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "pyaterochka_camoufox_smoke.json"
    report_path = output_dir / "pyaterochka_camoufox_smoke.md"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_smoke_report(result, report_path)
    return output_path, report_path


def failed_attempt_result(
    category_name: str,
    category_url: str,
    attempt: int,
    attempts: int,
    exc: Exception,
) -> dict[str, Any]:
    """Build a smoke result for one failed attempt."""
    result = {
        "shop": "pyaterochka",
        "category": category_name,
        "category_url": category_url,
        "attempt": attempt,
        "max_attempts": attempts,
        "blocked": True,
        "block_reason": "attempt_failed",
        "navigation_error": str(exc),
        "cards_found": 0,
        "products_sample": [],
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
    }
    attach_site_error_summary(result)
    return result


def parse_args(default_category: str) -> argparse.Namespace:
    """Parse smoke-test CLI arguments."""
    parser = argparse.ArgumentParser(description="Run Pyaterochka Camoufox smoke test")
    parser.add_argument("--category", default=default_category)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--headless", action="store_true", default=None)
    parser.add_argument("--no-headless", action="store_false", dest="headless")
    parser.add_argument("--pause", action="store_true", help="Keep browser open after the smoke attempt")
    parser.add_argument("--load-images", action="store_true", help="Allow images for visual captcha checks")
    parser.add_argument("--persistent-profile", action="store_true", help="Reuse local Camoufox profile/session")
    parser.add_argument("--manual-wait", action="store_true", help="Wait for remote human challenge resolution")
    parser.add_argument(
        "--manual-timeout-seconds",
        type=float,
        default=600,
        help="Maximum remote challenge wait before an honest blocked result",
    )
    return parser.parse_args()


class SmokeCooldownPage:
    """Minimal cooldown page adapter for category behavior delays."""

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        await asyncio.sleep(timeout_ms / 1000)
