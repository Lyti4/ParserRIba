"""Smoke test for Pyaterochka parsing through AsyncCamoufox.

This script intentionally avoids the current parser inheritance layer because
it is being repaired separately. It validates the important path first:
Knowledge Base -> Camoufox browser -> Pyaterochka category page -> product cards.
"""

from __future__ import annotations

import asyncio
import argparse
import json
import os
import re
import sys
import warnings
from datetime import datetime
from time import perf_counter
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from camoufox.async_api import AsyncCamoufox
from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.antibot import (
    classify_navigation_error,
    collect_page_diagnostics,
    wait_for_pyaterochka_state,
)
from utils.camoufox_launcher import build_camoufox_options, configure_windows_console
from utils.env import load_dotenv_file
from utils.fingerprint import fingerprint_summary_from_options
from utils.human_behavior import (
    browse_category_page,
    build_category_behavior_profile,
    cooldown_for_reason,
    hover_product_cards,
)
from utils.kb_loader import KBLoader, SelectorConfig
from utils.proxy import choose_proxy_for_attempt, load_proxy_urls, mask_proxy_url
from utils.smoke_report import write_smoke_report

OUTPUT_DIR = ROOT_DIR / "data"
PROFILE_DIR = ROOT_DIR / "profiles" / "pyaterochka"
DEFAULT_CATEGORY = "Рыба"
PROXY_ENV = "PARSER_PROXY"
PROXY_PREFLIGHT_URL = "https://api.ipify.org?format=json"
PRODUCT_API_MARKERS = ("api", "catalog", "product", "products", "search", "plu")
SENSITIVE_QUERY_KEYS = (
    "access",
    "auth",
    "authorization",
    "cookie",
    "email",
    "key",
    "password",
    "phone",
    "refresh",
    "secret",
    "session",
    "sid",
    "token",
)


def _split_selectors(config: SelectorConfig | None) -> list[str]:
    """Return individual CSS selectors from a KB selector config."""
    if not config or not config.css:
        return []
    return [item.strip() for item in config.css.split("|") if item.strip()]


async def _query_first_text(root: Any, selectors: list[str]) -> str:
    """Return text from the first matching selector."""
    for selector in selectors:
        try:
            element = await root.query_selector(selector)
            if element:
                text = await element.inner_text()
                if text.strip():
                    return text.strip()
        except Exception as exc:
            logger.debug("Selector failed: {} ({})", selector, exc)
    return ""


async def _query_first_attribute(root: Any, selectors: list[str], attr: str) -> str:
    """Return attribute from the first matching selector."""
    for selector in selectors:
        try:
            element = await root.query_selector(selector)
            if element:
                value = await element.get_attribute(attr)
                if value:
                    return value
        except Exception as exc:
            logger.debug("Selector failed: {} ({})", selector, exc)
    return ""


async def _find_cards(page: Any, selectors: list[str]) -> list[Any]:
    """Find product cards using KB selectors."""
    for selector in selectors:
        try:
            cards = await page.query_selector_all(selector)
            if cards:
                logger.info("Product cards found by selector '{}': {}", selector, len(cards))
                return cards
        except Exception as exc:
            logger.debug("Card selector failed: {} ({})", selector, exc)
    return []


async def _browser_external_ip(page: Any) -> str:
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


def _build_network_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a compact network summary for smoke diagnostics."""
    status_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    error_samples: list[dict[str, Any]] = []
    catalog_samples: list[dict[str, Any]] = []
    product_api_samples: list[dict[str, Any]] = []
    empty_product_api_samples: list[dict[str, Any]] = []
    estimated_body_bytes = 0
    for event in events:
        failure = event.get("failure")
        if failure:
            failure_key = str(failure)
            failure_counts[failure_key] = failure_counts.get(failure_key, 0) + 1
            if len(error_samples) < 10:
                error_samples.append(event)
            continue
        status = event.get("status")
        status_key = str(status) if status is not None else "unknown"
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
        estimated_body_bytes += int(event.get("content_length") or 0)
        if isinstance(status, int) and status >= 400 and len(error_samples) < 10:
            error_samples.append(event)
        if _is_product_api_url(event.get("url", "")):
            catalog_samples.append(event)
            if len(product_api_samples) < 12:
                product_api_samples.append(event)
            if event.get("empty_products_payload") and len(empty_product_api_samples) < 8:
                empty_product_api_samples.append(event)
    return {
        "responses": len(events),
        "status_counts": status_counts,
        "failure_counts": failure_counts,
        "estimated_body_bytes": estimated_body_bytes,
        "error_samples": error_samples,
        "catalog_samples": catalog_samples[:15],
        "product_api_samples": product_api_samples,
        "empty_product_api_samples": empty_product_api_samples,
    }


def _classify_proxy_health(
    *,
    proxy_enabled: bool,
    preflight: dict[str, Any],
    network: dict[str, Any],
    browser_external_ip: str,
) -> dict[str, Any]:
    """Classify practical proxy health signals without provider API access."""
    if not proxy_enabled:
        return {
            "status": "not_configured",
            "traffic_risk": "unknown",
            "notes": ["Proxy is not configured for this attempt."],
        }

    status_counts = network.get("status_counts") or {}
    failure_counts = network.get("failure_counts") or {}
    notes: list[str] = []
    status = "ok"
    traffic_risk = "low"

    if not preflight.get("ok"):
        status = "preflight_failed"
        traffic_risk = "high"
        notes.append("Proxy preflight failed before opening Pyaterochka.")
    if int(status_counts.get("407", 0)) > 0:
        status = "proxy_auth_failed"
        traffic_risk = "high"
        notes.append("HTTP 407 means proxy authentication or account access failed.")
    if int(status_counts.get("429", 0)) > 0:
        status = "rate_limited"
        traffic_risk = "medium"
        notes.append("HTTP 429 suggests rate limiting by the site or proxy route.")
    server_errors = sum(int(status_counts.get(str(code), 0)) for code in range(500, 600))
    if server_errors:
        status = "upstream_errors" if status == "ok" else status
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("5xx responses can indicate unstable proxy route or upstream blocking.")
    if failure_counts:
        status = "network_failures" if status == "ok" else status
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("Browser reported failed network requests.")
    if not browser_external_ip:
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("Browser external IP check did not return an IP.")
    if network.get("responses", 0) < 5:
        traffic_risk = "medium" if traffic_risk == "low" else traffic_risk
        notes.append("Very few responses were observed; proxy or page load may have stopped early.")
    if not notes:
        notes.append("No obvious proxy traffic/auth symptoms detected in this run.")

    return {
        "status": status,
        "traffic_risk": traffic_risk,
        "notes": notes,
    }


def _is_product_api_url(url: Any) -> bool:
    """Return True when a URL looks relevant to catalog/product diagnostics."""
    lowered = str(url or "").lower()
    return any(marker in lowered for marker in PRODUCT_API_MARKERS)


def _sanitize_diagnostic_url(url: str, max_length: int = 260) -> str:
    """Mask sensitive query values before writing diagnostic URLs."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url[:max_length]
    safe_query: list[tuple[str, str]] = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if any(marker in lowered for marker in SENSITIVE_QUERY_KEYS):
            safe_query.append((key, "***"))
        else:
            safe_query.append((key, value))
    sanitized = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe_query), parts.fragment))
    return sanitized[:max_length]


def _payload_has_empty_products(payload: str) -> bool:
    """Detect product API payloads that explicitly contain empty product lists."""
    compact = re.sub(r"\s+", "", payload)
    empty_markers = (
        '"products":[]',
        '"productsList":[]',
        '"items":[]',
        '"results":[]',
        '"data":[]',
        '"productsResponse":null',
    )
    return compact == "[]" or any(marker in compact for marker in empty_markers)


def _payload_preview(payload: str, max_length: int = 500) -> str:
    """Return a compact response preview for diagnostics."""
    compact = re.sub(r"\s+", " ", payload).strip()
    return compact[:max_length]


async def _record_network_response(item: Any, network_events: list[dict[str, Any]]) -> None:
    """Record a response and a small product API payload diagnostic when safe."""
    url = _sanitize_diagnostic_url(str(item.url))
    event: dict[str, Any] = {
        "status": item.status,
        "url": url,
    }
    try:
        headers = await item.all_headers()
    except Exception:
        headers = {}
    content_type = str(headers.get("content-type", ""))
    if content_type:
        event["content_type"] = content_type.split(";")[0]
    content_length = str(headers.get("content-length", ""))
    if content_length.isdigit():
        event["content_length"] = int(content_length)
    if _is_product_api_url(url) and "json" in content_type.lower():
        try:
            payload = await item.text()
        except Exception as exc:
            event["payload_error"] = str(exc).splitlines()[0][:180]
        else:
            event["empty_products_payload"] = _payload_has_empty_products(payload)
            event["payload_preview"] = _payload_preview(payload)
    network_events.append(event)


async def _record_network_failure(item: Any, network_events: list[dict[str, Any]]) -> None:
    """Record failed requests without leaking query secrets."""
    try:
        failure = item.failure or ""
    except Exception:
        failure = ""
    network_events.append(
        {
            "failure": str(failure or "unknown")[:180],
            "url": _sanitize_diagnostic_url(str(item.url)),
        }
    )


async def _run_proxy_preflight(page: Any, proxy_url: str) -> dict[str, Any]:
    """Check that the browser can pass a small request through the proxy."""
    if not proxy_url:
        return {"enabled": False, "ok": None, "url": PROXY_PREFLIGHT_URL}
    started = perf_counter()
    result: dict[str, Any] = {
        "enabled": True,
        "ok": False,
        "url": PROXY_PREFLIGHT_URL,
        "proxy": mask_proxy_url(proxy_url),
    }
    try:
        response = await page.goto(PROXY_PREFLIGHT_URL, wait_until="domcontentloaded", timeout=30_000)
        body = await page.inner_text("body")
    except Exception as exc:
        result["error"] = str(exc).splitlines()[0][:240]
    else:
        result["status"] = response.status if response else None
        result["response_bytes"] = len(body.encode("utf-8", errors="ignore"))
        result["ok"] = bool(response and response.ok and '"ip"' in body)
        match = re.search(r'"ip"\s*:\s*"([^"]+)"', body)
        if match:
            result["ip"] = match.group(1)
    result["duration_ms"] = int((perf_counter() - started) * 1000)
    return result


def _extract_page_context(page_html: str) -> dict[str, Any]:
    """Extract store/region/product state hints from saved page HTML."""
    compact = re.sub(r"\s+", "", page_html)
    return {
        "next_data_present": "__NEXT_DATA__" in page_html,
        "catalog_store_present": "catalogStore" in page_html,
        "selected_store_detected": bool(
            re.search(r'"(?:selectedStore|currentStore|activeStore|store)"\s*:\s*\{', page_html)
        ),
        "address_detected": bool(re.search(r'"address"\s*:\s*"[^"]+', page_html)),
        "region_hint_detected": any(marker in page_html.lower() for marker in ("москва", "moscow", "city")),
        "products_list_empty": '"productsList":[]' in compact,
        "products_empty": '"products":[]' in compact,
        "products_response_null": '"productsResponse":null' in compact,
    }


async def _wait_for_cards_after_manual_challenge(
    page: Any,
    response: Any,
    card_selectors: list[str],
    timeout_ms: int = 45_000,
) -> tuple[Any, list[Any], bool]:
    """Wait after manual captcha solving until products appear or challenge remains."""
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    last_diagnostics = await collect_page_diagnostics(page, response)
    last_cards: list[Any] = []
    while asyncio.get_running_loop().time() < deadline:
        last_diagnostics = await collect_page_diagnostics(page, response)
        last_cards = await _find_cards(page, card_selectors)
        if last_cards:
            return last_diagnostics, last_cards, True
        if last_diagnostics.blocked:
            return last_diagnostics, [], False
        await page.wait_for_timeout(1_000)
    return last_diagnostics, last_cards, False


async def smoke_parse_pyaterochka(
    category_name: str = DEFAULT_CATEGORY,
    attempts: int = 3,
    headless: bool | str | None = None,
    pause: bool = False,
    block_images: bool = True,
    persistent_profile: bool = False,
    manual_wait: bool = False,
) -> dict[str, Any]:
    """Open Pyaterochka category through Camoufox and collect a small sample."""
    configure_windows_console()
    load_dotenv_file(ROOT_DIR / ".env")

    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop("pyaterochka")
    category_url = kb.categories.get(category_name)
    if not category_url:
        category_name, category_url = next(iter(kb.categories.items()))

    card_selectors = _split_selectors(kb.selectors.get("product_card"))
    name_selectors = _split_selectors(kb.selectors.get("product_name"))
    price_selectors = _split_selectors(kb.selectors.get("price_current"))
    link_selectors = _split_selectors(kb.selectors.get("product_link"))

    logger.info("Starting Camoufox for Pyaterochka smoke test")
    logger.info("Category: {} -> {}", category_name, category_url)

    proxy_urls = load_proxy_urls(
        primary=os.environ.get(PROXY_ENV, ""),
        pool=os.environ.get("PARSER_PROXIES", ""),
    )
    geoip_enabled = os.environ.get("PARSER_GEOIP", "").lower() in {"1", "true", "yes"}
    browser_headless = headless
    if browser_headless is None:
        browser_headless = False if sys.platform == "win32" else "virtual"

    final_result: dict[str, Any] | None = None
    attempt_results: list[dict[str, Any]] = []
    for attempt in range(1, attempts + 1):
        proxy_url = choose_proxy_for_attempt(proxy_urls, attempt)
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
            )
        except Exception as exc:
            logger.warning("Smoke attempt {} failed: {}", attempt, exc)
            final_result = _failed_attempt_result(category_name, category_url, attempt, attempts, exc)
        attempt_results.append(
            {
                "attempt": attempt,
                "blocked": final_result.get("blocked"),
                "block_reason": final_result.get("block_reason"),
                "cards_found": final_result.get("cards_found", 0),
                "proxy": final_result.get("proxy", ""),
            }
        )
        if final_result.get("cards_found", 0) > 0 and not final_result.get("blocked"):
            break
        if attempt < attempts:
            reason = str(final_result.get("block_reason") or "empty_result")
            await cooldown_for_reason(_SmokeCooldownPage(), reason, build_category_behavior_profile(category_name))

    result = final_result or _failed_attempt_result(
        category_name, category_url, 0, attempts, RuntimeError("no attempts executed")
    )
    result["attempts"] = attempt_results

    output_path, report_path = _write_smoke_outputs(result)
    logger.info("Smoke result saved: {}", output_path)
    logger.info("Smoke report saved: {}", report_path)
    logger.info("Cards found: {}", result["cards_found"])
    for product in result.get("products_sample", [])[:5]:
        logger.info("{} | {} | {}", product["name"], product["price"], product["link"])
    return result


def _write_smoke_outputs(result: dict[str, Any]) -> tuple[Path, Path]:
    """Write smoke JSON and Markdown outputs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.json"
    report_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.md"
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_smoke_report(result, report_path)
    return output_path, report_path


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
) -> dict[str, Any]:
    """Run one browser/proxy smoke attempt."""
    card_selectors = _split_selectors(kb.selectors.get("product_card"))
    name_selectors = _split_selectors(kb.selectors.get("product_name"))
    price_selectors = _split_selectors(kb.selectors.get("price_current"))
    link_selectors = _split_selectors(kb.selectors.get("product_link"))
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
        if manual_wait:
            logger.info("Manual wait enabled; solve captcha in Camoufox, then press Enter here")
            await asyncio.to_thread(
                input,
                "Press Enter only after product cards are visible in Camoufox...",
            )
            diagnostics, manual_cards, manual_cards_ready = await _wait_for_cards_after_manual_challenge(
                page=page,
                response=response,
                card_selectors=card_selectors,
            )
            logger.info(
                "Post-manual wait finished: cards_ready={}, cards_found={}",
                manual_cards_ready,
                len(manual_cards),
            )
            navigation_error = ""
        else:
            manual_cards = []
            manual_cards_ready = False

        if network_tasks:
            await asyncio.gather(*network_tasks, return_exceptions=True)

        result = await _build_attempt_result(
            page=page,
            response=response,
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
            cards_override=manual_cards,
            manual_wait=manual_wait,
            manual_cards_ready=manual_cards_ready,
        )
        if pause:
            if network_tasks:
                await asyncio.gather(*network_tasks, return_exceptions=True)
            output_path, report_path = _write_smoke_outputs(result)
            logger.info("Smoke result saved before pause: {}", output_path)
            logger.info("Smoke report saved before pause: {}", report_path)
            logger.info("Pause enabled; leave this PowerShell window open to inspect Camoufox")
            while True:
                await page.wait_for_timeout(60_000)
        return result


async def _build_attempt_result(
    page: Any,
    response: Any,
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
    cards_override: list[Any] | None = None,
    manual_wait: bool = False,
    manual_cards_ready: bool = False,
) -> dict[str, Any]:
    """Collect the final smoke result from the current page state."""
    block_reason = diagnostics.reason
    blocked = diagnostics.blocked
    navigation_reason = classify_navigation_error(navigation_error)
    if navigation_reason:
        block_reason = navigation_reason
        blocked = True
    external_ip = await _browser_external_ip(page)
    page_html = await page.content()
    page_context = _extract_page_context(page_html)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.png"
    html_path = OUTPUT_DIR / "pyaterochka_camoufox_smoke.html"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    html_path.write_text(page_html, encoding="utf-8")

    if navigation_error:
        cards = []
    elif cards_override is not None:
        cards = cards_override
    else:
        cards = await _find_cards(page, card_selectors)
    if cards:
        await hover_product_cards(page, cards, behavior_profile)
    products = await _extract_sample_products(cards, name_selectors, price_selectors, link_selectors)
    network_summary = _build_network_summary(network_events)
    proxy_diagnostics = _classify_proxy_health(
        proxy_enabled=bool(proxy_url),
        preflight=proxy_preflight,
        network=network_summary,
        browser_external_ip=external_ip,
    )
    return {
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
        "fingerprint": fingerprint_summary_from_options(launch_options),
        "behavior_profile": behavior_profile.summary(),
        "browser_external_ip": external_ip,
        "screenshot_path": str(screenshot_path),
        "html_path": str(html_path),
        "cards_found": len(cards),
        "products_sample": products,
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


async def _extract_sample_products(
    cards: list[Any],
    name_selectors: list[str],
    price_selectors: list[str],
    link_selectors: list[str],
) -> list[dict[str, str]]:
    """Extract a small product sample from cards."""
    products: list[dict[str, str]] = []
    for index, card in enumerate(cards[:10], start=1):
        name = await _query_first_text(card, name_selectors)
        price = await _query_first_text(card, price_selectors)
        link = await _query_first_attribute(card, link_selectors, "href")
        if link and link.startswith("/"):
            link = f"https://5ka.ru{link}"
        if name or price:
            products.append({"index": str(index), "name": name, "price": price, "link": link})
    return products


def _failed_attempt_result(
    category_name: str,
    category_url: str,
    attempt: int,
    attempts: int,
    exc: Exception,
) -> dict[str, Any]:
    """Build a smoke result for a failed attempt."""
    return {
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


def _parse_args() -> argparse.Namespace:
    """Parse smoke-test CLI arguments."""
    parser = argparse.ArgumentParser(description="Run Pyaterochka Camoufox smoke test")
    parser.add_argument("--category", default=DEFAULT_CATEGORY)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--headless", action="store_true", default=None)
    parser.add_argument("--no-headless", action="store_false", dest="headless")
    parser.add_argument("--pause", action="store_true", help="Keep browser open after the smoke attempt")
    parser.add_argument("--load-images", action="store_true", help="Allow images for visual captcha checks")
    parser.add_argument("--persistent-profile", action="store_true", help="Reuse local Camoufox profile/session")
    parser.add_argument("--manual-wait", action="store_true", help="Wait for Enter after manual captcha solving")
    return parser.parse_args()


class _SmokeCooldownPage:
    async def wait_for_timeout(self, timeout_ms: int) -> None:
        await asyncio.sleep(timeout_ms / 1000)


if __name__ == "__main__":
    if sys.platform == "win32":
        warnings.filterwarnings("ignore", category=ResourceWarning)
    args = _parse_args()
    asyncio.run(
        smoke_parse_pyaterochka(
            category_name=args.category,
            attempts=args.attempts,
            headless=args.headless,
            pause=args.pause,
            block_images=not args.load_images,
            persistent_profile=args.persistent_profile,
            manual_wait=args.manual_wait,
        )
    )
