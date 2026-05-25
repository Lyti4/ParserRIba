"""Network event capture helpers for catalog research runs."""

from __future__ import annotations

from models.catalog_discovery import RouteHint
from utils.catalog_tree_discovery.evidence_registry import EvidenceItem
from utils.catalog_tree_discovery.payload_classifiers import classify_payload

CATALOG_ROUTE_MARKERS = ("/api/", "graphql", "/catalog", "/category")
CATALOG_BODY_MARKERS = ("category", "catalog", "breadcrumb", "children")


class DiscoveryEventCapture:
    """Collect lightweight route hints from interesting discovery traffic."""

    def __init__(self) -> None:
        self.route_hints: list[RouteHint] = []
        self.request_urls: list[str] = []
        self.response_category_urls: list[str] = []
        self.response_evidence_items: list[EvidenceItem] = []
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
        classification = classify_payload(base_url=url, content_type=content_type, body_text=body_text)
        for signal in classification.protection_signals:
            if signal not in self.protection_hints:
                self.protection_hints.append(signal)
        if classification.protection_signals:
            self.route_hints.append(RouteHint(kind="protection_html", value=url, source="network"))
        for hint in classification.route_hints:
            if not any(existing.kind == hint.kind and existing.value == hint.value for existing in self.route_hints):
                self.route_hints.append(hint)
        for category in classification.categories:
            if category.url not in self.response_category_urls:
                self.response_category_urls.append(category.url)
            self.response_evidence_items.append(
                EvidenceItem(
                    label=category.name,
                    url=category.url,
                    source="network_response",
                    payload_type=classification.payload_type,
                    confidence=classification.confidence,
                    route_hint="response_payload",
                    protection_signals=classification.protection_signals,
                    evidence_ref=url,
                )
            )
        if status >= 400:
            return
        if "json" not in lowered_meta and "graphql" not in lowered_meta:
            return
        if any(marker in lowered_body for marker in CATALOG_BODY_MARKERS):
            self.route_hints.append(RouteHint(kind="response_json", value=url, source="network"))
