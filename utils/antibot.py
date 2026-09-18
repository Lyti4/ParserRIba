"""Anti-bot page detection helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


PAGE_DIAGNOSTIC_TEXT_TIMEOUT_SECONDS = 2
PYATEROCHKA_CHALLENGE_PATHS = ("/xpvnsulc/", "/exhkqyad")
PYATEROCHKA_CATALOG_MARKERS = ("/catalog/",)
PYATEROCHKA_READY_SURFACE_MARKERS = ('href="/catalog/', "href='/catalog/", 'href="/product/', "href='/product/")
PYATEROCHKA_READY_MIN_HTML_SIZE = 100_000


@dataclass(frozen=True)
class PageDiagnostics:
    """Small diagnostic snapshot for a loaded page."""

    blocked: bool
    reason: str
    final_url: str
    title: str
    html_size: int
    status: int | None = None
    catalog_ready: bool = False


def detect_pyaterochka_antibot(url: str, title: str, html: str) -> tuple[bool, str]:
    """Detect Pyaterochka anti-bot challenge pages."""
    lowered_url = url.lower()
    lowered_title = title.lower()
    lowered_html = html.lower()

    if any(path in lowered_url for path in PYATEROCHKA_CHALLENGE_PATHS):
        return True, "pyaterochka_antibot_redirect"
    if "back_location=" in lowered_url and "request_ip=" in lowered_url:
        return True, "pyaterochka_antibot_query"
    if lowered_title.startswith("loading https://5ka.ru/"):
        return True, "pyaterochka_loading_challenge"
    if "vpn" in lowered_html and (
        "\u043f\u0440\u043e\u0431\u043b\u0435\u043c\u044b \u0441\u043e \u0441\u0432\u044f\u0437\u044c\u044e" in lowered_html
        or "\u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u0430" in lowered_html
    ):
        return True, "pyaterochka_vpn_connection_block"
    if _pyaterochka_catalog_surface_ready(lowered_url, lowered_html):
        return False, "ok"
    if "captcha" in lowered_html or "капч" in lowered_html:
        return True, "pyaterochka_captcha"
    if "повер" in lowered_html and "изображ" in lowered_html:
        return True, "pyaterochka_rotate_image_captcha"
    if "rotate" in lowered_html and "image" in lowered_html:
        return True, "pyaterochka_rotate_image_captcha"
    if "/exhkqyad" in lowered_html or "xpvnsulc" in lowered_html:
        return True, "pyaterochka_antibot_html"
    return False, "ok"


def _pyaterochka_catalog_surface_ready(lowered_url: str, lowered_html: str) -> bool:
    if not any(marker in lowered_url for marker in PYATEROCHKA_CATALOG_MARKERS):
        return False
    if any(marker in lowered_html for marker in PYATEROCHKA_READY_SURFACE_MARKERS):
        return True
    return len(lowered_html) >= PYATEROCHKA_READY_MIN_HTML_SIZE and (
        "__next" in lowered_html or "_next/static" in lowered_html or "каталог" in lowered_html
    )


def classify_navigation_error(error_text: str) -> str:
    """Classify browser navigation errors into report-friendly reasons."""
    lowered = error_text.lower()
    if not lowered:
        return ""
    if "ns_error_unknown_host" in lowered or "err_name_not_resolved" in lowered:
        return "network_dns_error"
    if "timeout" in lowered:
        return "network_timeout"
    if "proxy" in lowered:
        return "network_proxy_error"
    if "connection" in lowered or "net::err_" in lowered:
        return "network_connection_error"
    return "navigation_error"


async def collect_page_diagnostics(page: Any, response: Any = None) -> PageDiagnostics:
    """Collect URL, title, status and anti-bot state from a Playwright page."""
    title = await _safe_page_text(page.title)
    html = await _safe_page_text(page.content)
    lowered_url = str(page.url or "").lower()
    lowered_html = html.lower()
    catalog_ready = _pyaterochka_catalog_surface_ready(lowered_url, lowered_html)
    blocked, reason = detect_pyaterochka_antibot(page.url, title, html)
    return PageDiagnostics(
        blocked=blocked,
        reason=reason,
        final_url=page.url,
        title=title,
        html_size=len(html),
        status=response.status if response else None,
        catalog_ready=catalog_ready,
    )


async def _safe_page_text(reader: Any) -> str:
    try:
        return str(await asyncio.wait_for(reader(), timeout=PAGE_DIAGNOSTIC_TEXT_TIMEOUT_SECONDS))
    except Exception:
        return ""


async def wait_for_pyaterochka_challenge(page: Any, seconds: int = 30) -> None:
    """Wait for a Pyaterochka challenge to redirect back to a catalog page."""
    for _ in range(seconds):
        if not any(path in page.url.lower() for path in PYATEROCHKA_CHALLENGE_PATHS):
            return
        await page.wait_for_timeout(1_000)


async def wait_for_pyaterochka_state(page: Any, response: Any = None, seconds: int = 30) -> PageDiagnostics:
    """Wait until Pyaterochka settles on catalog, challenge or timeout."""
    last_diagnostics = await collect_page_diagnostics(page, response)
    for _ in range(seconds):
        diagnostics = await collect_page_diagnostics(page, response)
        last_diagnostics = diagnostics
        if diagnostics.blocked:
            return diagnostics
        if diagnostics.catalog_ready:
            return diagnostics
        await page.wait_for_timeout(1_000)
    return last_diagnostics
