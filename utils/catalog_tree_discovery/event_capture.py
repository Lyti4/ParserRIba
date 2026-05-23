"""Network event capture helpers for catalog research runs."""

from __future__ import annotations

from utils.catalog_tree_discovery.embedded_extractors import extract_embedded_category_evidence
from models.catalog_discovery import RouteHint

CATALOG_ROUTE_MARKERS = ("/api/", "graphql", "/catalog", "/category")
CATALOG_BODY_MARKERS = ("category", "catalog", "breadcrumb", "children")
PROTECTION_BODY_MARKERS = (
    "captcha",
    "cloudflare",
    "turnstile",
    "datadome",
    "perimeterx",
    "servicepipe",
    "access denied",
    "attention required",
)


class DiscoveryEventCapture:
    """Collect lightweight route hints from interesting discovery traffic."""

    def __init__(self) -> None:
        self.route_hints: list[RouteHint] = []
        self.request_urls: list[str] = []
        self.response_category_urls: list[str] = []
        self.protection_hints: list[str] = []

    async def record_request(self, url: str) -> None:
        """Remember one interesting request URL for later diagnostics."""
        lowered = str(url).casefold()
        if any(marker in lowered for marker in CATALOG_ROUTE_MARKERS):
            self.request_urls.append(url)

    async def record_response(
        self,
        *,
        url: str,
        status: int,
        content_type: str,
        body_text: str,
    ) -> None:
        """Convert one response into a route hint when it looks catalog-like."""
        lowered_meta = f"{url} {content_type}".casefold()
        lowered_body = str(body_text).casefold()
        if any(marker in lowered_body for marker in PROTECTION_BODY_MARKERS):
            protection_kind = f"protection:{_first_matching_marker(lowered_body, PROTECTION_BODY_MARKERS)}"
            if protection_kind not in self.protection_hints:
                self.protection_hints.append(protection_kind)
            self.route_hints.append(RouteHint(kind="protection_html", value=url, source="network"))
        if status >= 400:
            return
        if "json" not in lowered_meta and "graphql" not in lowered_meta:
            return
        if any(marker in lowered_body for marker in CATALOG_BODY_MARKERS):
            self.route_hints.append(RouteHint(kind="response_json", value=url, source="network"))
        for item in extract_embedded_category_evidence(url, body_text):
            if item.url not in self.response_category_urls:
                self.response_category_urls.append(item.url)


def _first_matching_marker(text: str, markers: tuple[str, ...]) -> str:
    for marker in markers:
        if marker in text:
            return marker
    return "unknown"
