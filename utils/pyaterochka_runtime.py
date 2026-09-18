"""Runtime constants and helpers for Pyaterochka adapters."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "data"
PROFILE_DIR = ROOT_DIR / "profiles" / "pyaterochka"
DEFAULT_CATEGORY = "Рыба"


async def collect_dom_product_links(page: Any, *, limit: int = 10) -> dict[str, Any]:
    """Collect visible DOM product links for comparison with API product ids."""
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
        product_id = extract_product_id_from_href(href)
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


def extract_product_id_from_href(href: str) -> str:
    """Extract numeric product id from a public 5ka product URL."""
    match = re.search(r"/product/[^/]*--(\d+)/?$", href)
    if match:
        return match.group(1)
    return ""
