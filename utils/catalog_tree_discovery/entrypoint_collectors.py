"""Catalog entrypoint collection helpers for research runs."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from models.catalog_discovery import CategoryEvidence
from utils.catalog_tree_discovery.surface_collectors import collect_catalog_surface_signals


def collect_catalog_entrypoints_from_html(site_url: str, html: str) -> list[CategoryEvidence]:
    """Collect category-like entrypoints from one rendered page snapshot."""
    signals = collect_catalog_surface_signals(
        site_url=site_url,
        final_url=site_url,
        status_code=200,
        html=html,
    )
    entrypoints = list(signals.dom_categories)
    seen_urls = {item.url for item in entrypoints}
    candidate_hrefs = list(signals.raw_hrefs) + _extract_catalog_urls_from_html(site_url, html)
    for href in candidate_hrefs:
        normalized = href.casefold().rstrip("/")
        if normalized.endswith("/catalog") and href not in seen_urls:
            entrypoints.append(CategoryEvidence(name="Каталог", url=href, source="html"))
            seen_urls.add(href)
            continue
        if not _looks_like_catalog_entrypoint(href) or href in seen_urls:
            continue
        entrypoints.append(
            CategoryEvidence(
                name=_derive_category_label(href),
                url=href,
                source="href_frontier",
            )
        )
        seen_urls.add(href)
    entrypoints.sort(key=_entrypoint_sort_key)
    return entrypoints


def _looks_like_catalog_entrypoint(url: str) -> bool:
    lowered = str(url or "").casefold()
    return "/catalog/" in lowered or "/category/" in lowered or "/categories/" in lowered


def _derive_category_label(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else ""
    if not slug:
        return "Каталог"
    slug = re.sub(r"--?[0-9a-z]+$", "", slug, flags=re.IGNORECASE)
    slug = slug.replace("-", " ").replace("_", " ").strip()
    if not slug:
        return "Каталог"
    return slug[:1].upper() + slug[1:]


def _extract_catalog_urls_from_html(site_url: str, html: str) -> list[str]:
    matches = re.findall(r'["\'](/(?:catalog|category|categories)/[^"\']+)["\']', html, flags=re.IGNORECASE)
    base = site_url.rstrip("/")
    result: list[str] = []
    seen: set[str] = set()
    for match in matches:
        url = f"{base}{match}" if match.startswith("/") else match
        if url in seen:
            continue
        seen.add(url)
        result.append(url)
    return result


def _entrypoint_sort_key(item: CategoryEvidence) -> tuple[int, int, str]:
    url = str(item.url or "")
    normalized = url.casefold().rstrip("/")
    path = urlparse(url).path
    root_rank = 0 if normalized.endswith("/catalog") else 1
    depth = path.count("/")
    return (root_rank, depth, normalized)
