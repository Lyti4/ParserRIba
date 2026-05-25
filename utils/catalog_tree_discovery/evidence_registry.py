"""Evidence registry for catalog discovery provenance."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.catalog_discovery import CategoryEvidence, DiscoverySource, PayloadType


class EvidenceItem(BaseModel):
    """One typed discovery signal retained for internal profile snapshots."""

    label: str = ""
    url: str
    source: DiscoverySource = "dom"
    payload_type: PayloadType = ""
    confidence: float = 0.0
    route_hint: str = ""
    protection_signals: list[str] = Field(default_factory=list)
    evidence_ref: str = ""


class EvidenceRegistry(BaseModel):
    """Deduplicated collection of discovery evidence."""

    items: list[EvidenceItem] = Field(default_factory=list)

    def add(self, item: EvidenceItem) -> None:
        """Add one evidence item, merging duplicate URL/source/payload records."""
        for existing in self.items:
            if (
                existing.url == item.url
                and existing.source == item.source
                and existing.payload_type == item.payload_type
            ):
                if item.confidence > existing.confidence:
                    existing.confidence = item.confidence
                if not existing.label and item.label:
                    existing.label = item.label
                existing.protection_signals = list(
                    dict.fromkeys(existing.protection_signals + item.protection_signals)
                )
                return
        self.items.append(item)

    def add_category(
        self,
        category: CategoryEvidence,
        *,
        source: DiscoverySource,
        payload_type: PayloadType,
        confidence: float,
        route_hint: str = "",
        protection_signals: list[str] | None = None,
        evidence_ref: str = "",
    ) -> None:
        """Add one category evidence item with provenance."""
        self.add(
            EvidenceItem(
                label=category.name,
                url=category.url,
                source=source,
                payload_type=payload_type,
                confidence=confidence,
                route_hint=route_hint,
                protection_signals=protection_signals or [],
                evidence_ref=evidence_ref,
            )
        )

    def to_categories(self) -> list[CategoryEvidence]:
        """Expose registry entries through the legacy category list contract."""
        seen: set[str] = set()
        categories: list[CategoryEvidence] = []
        for item in self.items:
            if item.url in seen:
                continue
            seen.add(item.url)
            categories.append(CategoryEvidence(name=item.label, url=item.url, source=item.source))
        return categories
