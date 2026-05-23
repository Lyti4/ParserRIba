"""Graph assembly for normalized catalog discovery nodes."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.catalog_discovery import DiscoveryEdge, DiscoveryNode, RouteHint
from utils.catalog_tree_discovery.evidence_registry import EvidenceItem
from utils.catalog_tree_discovery.surface_collectors import SurfaceSignals
from utils.catalog_tree_discovery.tree_normalizer import normalize_label_for_launcher


class DiscoveryGraph(BaseModel):
    """Normalized graph result assembled from low-level surface signals."""

    primary_root_ids: list[str] = Field(default_factory=list)
    nodes: list[DiscoveryNode] = Field(default_factory=list)
    edges: list[DiscoveryEdge] = Field(default_factory=list)


def build_discovery_graph(signals: SurfaceSignals) -> DiscoveryGraph:
    """Merge duplicate category URLs into normalized discovery nodes."""
    evidence_items = _evidence_for_graph(signals)
    grouped: dict[str, list[EvidenceItem]] = {}
    ordered_urls: list[str] = []
    for item in evidence_items:
        url = item.url
        if url not in grouped:
            grouped[url] = []
            ordered_urls.append(url)
        grouped[url].append(item)
    nodes: list[DiscoveryNode] = []
    for index, url in enumerate(ordered_urls, start=1):
        items = grouped[url]
        labels = [item.label or url for item in items]
        best = max(items, key=lambda item: item.confidence)
        nodes.append(
            DiscoveryNode(
                node_id=f"category-{index}",
                label_ru=normalize_label_for_launcher(labels[0], url),
                label_original=labels[0],
                canonical_url=url,
                candidate_urls=[url],
                source=best.source,
                listing_confidence=best.confidence,
                payload_type=best.payload_type,
                route_hints=_route_hints(items, url),
                protection_signals=list(dict.fromkeys(signal for item in items for signal in item.protection_signals)),
                raw_evidence_refs=_raw_refs(items, labels),
            )
        )
    return DiscoveryGraph(
        primary_root_ids=[node.node_id for node in nodes],
        nodes=nodes,
        edges=[],
    )


def _evidence_for_graph(signals: SurfaceSignals) -> list[EvidenceItem]:
    if signals.evidence_items:
        return signals.evidence_items
    return [
        EvidenceItem(
            label=item.name,
            url=item.url,
            source="dom",
            payload_type="",
            confidence=0.55,
            route_hint="legacy_dom_category",
            evidence_ref=item.source,
        )
        for item in signals.dom_categories
    ]


def _route_hints(items: list[EvidenceItem], url: str) -> list[RouteHint]:
    hints: list[RouteHint] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if not item.route_hint:
            continue
        key = (item.route_hint, url)
        if key in seen:
            continue
        seen.add(key)
        hints.append(RouteHint(kind=item.route_hint, value=url, source=item.source))
    return hints


def _raw_refs(items: list[EvidenceItem], labels: list[str]) -> list[str]:
    refs = labels[1:]
    for item in items:
        if item.source == "dom" and item.evidence_ref in {"html", "dom:a[href]"}:
            continue
        ref = f"{item.source}:{item.payload_type or 'link'}:{item.evidence_ref or item.url}"
        if ref not in refs:
            refs.append(ref)
    return refs
