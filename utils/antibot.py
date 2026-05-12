"""Anti-bot page detection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PYATEROCHKA_CHALLENGE_PATHS = ("/xpvnsulc/", "/exhkqyad")


@dataclass(frozen=True)
class PageDiagnostics:
    """Small diagnostic snapshot for a loaded page."""

    blocked: bool
    reason: str
    final_url: str
    title: str
    html_size: int
    status: int | None = None


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
    if "captcha" in lowered_html or "капч" in lowered_html:
        return True, "pyaterochka_captcha"
    if "повер" in lowered_html and "изображ" in lowered_html:
        return True, "pyaterochka_rotate_image_captcha"
    if "rotate" in lowered_html and "image" in lowered_html:
        return True, "pyaterochka_rotate_image_captcha"
    if "/exhkqyad" in lowered_html or "xpvnsulc" in lowered_html:
        return True, "pyaterochka_antibot_html"
    return False, "ok"


async def collect_page_diagnostics(page: Any, response: Any = None) -> PageDiagnostics:
    """Collect URL, title, status and anti-bot state from a Playwright page."""
    title = await page.title()
    html = await page.content()
    blocked, reason = detect_pyaterochka_antibot(page.url, title, html)
    return PageDiagnostics(
        blocked=blocked,
        reason=reason,
        final_url=page.url,
        title=title,
        html_size=len(html),
        status=response.status if response else None,
    )


async def wait_for_pyaterochka_challenge(page: Any, seconds: int = 30) -> None:
    """Wait for a Pyaterochka challenge to redirect back to a catalog page."""
    for _ in range(seconds):
        if not any(path in page.url.lower() for path in PYATEROCHKA_CHALLENGE_PATHS):
            return
        await page.wait_for_timeout(1_000)
