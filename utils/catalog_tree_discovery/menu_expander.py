"""Safe menu expansion helpers for browser-backed catalog research."""

from __future__ import annotations

from typing import Any

MENU_EXPANDER_SELECTORS = (
    "button[aria-expanded='false']",
    "[data-testid*='menu'] button",
    "button[class*='burger']",
    "button[class*='catalog']",
)


async def expand_menu_surfaces(page: Any) -> None:
    """Try a few low-risk menu interactions to reveal hidden catalog branches."""
    for selector in MENU_EXPANDER_SELECTORS:
        locator = page.locator(selector)
        count = await locator.count()
        for index in range(min(count, 5)):
            item = locator.nth(index)
            try:
                await item.hover(timeout=1_500)
                await page.wait_for_timeout(300)
                await item.click(timeout=1_500)
                await page.wait_for_timeout(500)
            except Exception:
                continue
