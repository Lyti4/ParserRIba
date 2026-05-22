"""Graph assembly for normalized catalog discovery nodes."""

from __future__ import annotations

from pydantic import BaseModel, Field

from models.catalog_discovery import DiscoveryEdge, DiscoveryNode
from utils.catalog_tree_discovery.surface_collectors import SurfaceSignals
from utils.catalog_tree_discovery.tree_normalizer import normalize_label_for_launcher


class DiscoveryGraph(BaseModel):
    """Normalized graph result assembled from low-level surface signals."""

    primary_root_ids: list[str] = Field(default_factory=list)
    nodes: list[DiscoveryNode] = Field(default_factory=list)
    edges: list[DiscoveryEdge] = Field(default_factory=list)


def build_discovery_graph(signals: SurfaceSignals) -> DiscoveryGraph:
    """Merge duplicate category URLs into normalized discovery nodes."""
    grouped: dict[str, list[str]] = {}
    ordered_urls: list[str] = []
    for item in signals.dom_categories:
        url = item.url
        if url not in grouped:
            grouped[url] = []
            ordered_urls.append(url)
        label = item.name or url
        if label not in grouped[url]:
            grouped[url].append(label)
    nodes: list[DiscoveryNode] = []
    for index, url in enumerate(ordered_urls, start=1):
        labels = grouped[url]
        nodes.append(
            DiscoveryNode(
                node_id=f"category-{index}",
                label_ru=normalize_label_for_launcher(labels[0], url),
                label_original=labels[0],
                canonical_url=url,
                candidate_urls=[url],
                source="dom",
                raw_evidence_refs=labels[1:],
            )
        )
    return DiscoveryGraph(
        primary_root_ids=[node.node_id for node in nodes],
        nodes=nodes,
        edges=[],
    )
