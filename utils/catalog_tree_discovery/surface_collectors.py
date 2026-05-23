"""Low-level HTML signal collection for catalog discovery."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from models.catalog_discovery import ApiEvidence, CategoryEvidence, DocumentEvidence, ProductLinkEvidence
from utils.catalog_tree_discovery.embedded_extractors import (
    extract_embedded_api_hints,
    extract_embedded_category_evidence,
)

CHALLENGE_MARKERS = ("captcha", "challenge", "turnstile", "cloudflare", "access denied")
REGION_MARKERS = ("выберите ваш регион", "регион", "город")
PDF_MARKERS = ("3dflipbook", "pdf.min.js", "flipbook")
API_PATTERNS = ("/api/", "graphql", "fetch(", "xmlhttprequest")
CATEGORY_NOISE_MARKERS = (
    "sale",
    "brand",
    "brands",
    "promo",
    "discount",
    "account",
    "profile",
    "login",
    "signin",
    "signup",
    "cart",
    "basket",
    "wishlist",
    "favorite",
    "novinki",
    "skid",
    "акци",
    "скид",
    "бренд",
    "новин",
    "профил",
    "кабинет",
    "вход",
    "регистра",
    "корзин",
    "избран",
    "under_search",
    "erid=",
    "rustore",
)


class SurfaceSignals(BaseModel):
    """Raw surface signals collected from one HTML response."""

    dom_categories: list[CategoryEvidence] = Field(default_factory=list)
    dom_products: list[ProductLinkEvidence] = Field(default_factory=list)
    api_hints: list[ApiEvidence] = Field(default_factory=list)
    documents: list[DocumentEvidence] = Field(default_factory=list)
    raw_hrefs: list[str] = Field(default_factory=list)
    blocked_hint: bool = False
    challenge_hint: bool = False
    region_hint: bool = False
    pdf_hint: bool = False
    csrf_meta_detected: bool = False
    products_path_seen: bool = False
    pagination_hint: bool = False


def collect_catalog_surface_signals(
    *,
    site_url: str,
    final_url: str,
    status_code: int,
    html: str,
) -> SurfaceSignals:
    """Collect low-level DOM, link, document, and API signals from HTML."""
    lowered = html.casefold()
    base_url = final_url or site_url
    soup = BeautifulSoup(html, "html.parser")
    raw_hrefs = _collect_hrefs(soup, base_url)
    documents = _collect_documents(soup, base_url, html)
    blocked_hint = int(status_code) in {401, 403, 429}
    challenge_hint = blocked_hint and any(marker in lowered for marker in CHALLENGE_MARKERS)
    region_hint = any(marker in lowered for marker in REGION_MARKERS)
    return SurfaceSignals(
        dom_categories=_dedup_category_links(
            _collect_category_links(soup, base_url) + extract_embedded_category_evidence(base_url, html)
        ),
        dom_products=_collect_product_links(soup, base_url),
        api_hints=_dedup_api_hints(_collect_api_hints(soup, html) + extract_embedded_api_hints(html)),
        documents=documents,
        raw_hrefs=raw_hrefs,
        blocked_hint=blocked_hint,
        challenge_hint=challenge_hint,
        region_hint=region_hint,
        pdf_hint=bool(documents) and any(marker in lowered for marker in PDF_MARKERS),
        csrf_meta_detected='name="csrf-token"' in lowered,
        products_path_seen="/products" in base_url.casefold()
        or any("/products" in item.url.casefold() for item in _collect_product_links(soup, base_url)),
        pagination_hint=any("?page=" in link.casefold() for link in raw_hrefs),
    )


def _collect_hrefs(soup: BeautifulSoup, base_url: str) -> list[str]:
    hrefs = [
        str(anchor.get("href") or "").strip()
        for anchor in soup.find_all("a")
        if str(anchor.get("href") or "").strip()
    ]
    return [urljoin(base_url, href) for href in hrefs]


def _collect_category_links(soup: BeautifulSoup, base_url: str) -> list[CategoryEvidence]:
    seen: set[str] = set()
    links: list[CategoryEvidence] = []
    for anchor in soup.find_all("a"):
        href = urljoin(base_url, str(anchor.get("href") or "").strip())
        name = anchor.get_text(" ", strip=True)
        if not href or href in seen or not _is_category_candidate_href(href) or _is_noise_category_candidate(name, href):
            continue
        seen.add(href)
        links.append(CategoryEvidence(name=name, url=href))
    return links


def _collect_product_links(soup: BeautifulSoup, base_url: str) -> list[ProductLinkEvidence]:
    seen: set[str] = set()
    links: list[ProductLinkEvidence] = []
    for anchor in soup.find_all("a"):
        href = urljoin(base_url, str(anchor.get("href") or "").strip())
        if not href or href in seen or not _is_product_candidate_href(href):
            continue
        seen.add(href)
        links.append(ProductLinkEvidence(name=anchor.get_text(" ", strip=True), url=href))
    return links


def _collect_documents(soup: BeautifulSoup, base_url: str, html: str) -> list[DocumentEvidence]:
    urls: list[str] = []
    for tag in soup.find_all(True):
        for attr_name in ("href", "src", "data-path", "data-pdf"):
            value = str(tag.get(attr_name) or "").strip()
            if value.casefold().endswith(".pdf"):
                urls.append(urljoin(base_url, value))
    for match in re.findall(r'["\']([^"\']+\.pdf)["\']', html, flags=re.IGNORECASE):
        urls.append(urljoin(base_url, match))
    seen: set[str] = set()
    documents: list[DocumentEvidence] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        documents.append(DocumentEvidence(kind="pdf", url=url))
    return documents


def _collect_api_hints(soup: BeautifulSoup, html: str) -> list[ApiEvidence]:
    hints: list[ApiEvidence] = []
    seen: set[tuple[str, str]] = set()
    for script in soup.find_all("script"):
        script_src = str(script.get("src") or "").strip()
        if "/api/" in script_src.casefold():
            key = ("script_src", script_src)
            if key not in seen:
                seen.add(key)
                hints.append(ApiEvidence(kind="script_src", value=script_src))
        script_text = script.get_text(" ", strip=True)
        lowered = script_text.casefold()
        for pattern in API_PATTERNS:
            if pattern in lowered:
                key = ("inline_marker", pattern)
                if key not in seen:
                    seen.add(key)
                    hints.append(ApiEvidence(kind="inline_marker", value=pattern))
    lowered_html = html.casefold()
    for pattern in API_PATTERNS:
        if pattern in lowered_html:
            key = ("html_marker", pattern)
            if key not in seen:
                seen.add(key)
                hints.append(ApiEvidence(kind="html_marker", value=pattern))
    return hints


def _is_category_candidate_href(href: str) -> bool:
    lowered = href.casefold()
    if "?page=" in lowered:
        return False
    return "/catalog" in lowered or "/category" in lowered or "/categories" in lowered


def _is_product_candidate_href(href: str) -> bool:
    lowered = href.casefold()
    if "?page=" in lowered:
        return False
    return "/products/" in lowered or "/product/" in lowered


def _is_noise_category_candidate(name: str, href: str) -> bool:
    lowered_name = str(name or "").casefold()
    lowered_href = href.casefold()
    if not lowered_name.strip():
        return True
    return any(marker in lowered_name or marker in lowered_href for marker in CATEGORY_NOISE_MARKERS)


def _dedup_category_links(items: list[CategoryEvidence]) -> list[CategoryEvidence]:
    seen: set[str] = set()
    result: list[CategoryEvidence] = []
    for item in items:
        if item.url in seen:
            continue
        seen.add(item.url)
        result.append(item)
    return result


def _dedup_api_hints(items: list[ApiEvidence]) -> list[ApiEvidence]:
    seen: set[tuple[str, str]] = set()
    result: list[ApiEvidence] = []
    for item in items:
        key = (item.kind, item.value)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
