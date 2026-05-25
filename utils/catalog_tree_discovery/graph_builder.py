"""Graph assembly for normalized catalog discovery nodes."""

from __future__ import annotations

from urllib.parse import urlparse

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
    edges = _attach_path_hierarchy(nodes)
    return DiscoveryGraph(
        primary_root_ids=[node.node_id for node in nodes if not node.parent_ids],
        nodes=nodes,
        edges=edges,
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


def _attach_path_hierarchy(nodes: list[DiscoveryNode]) -> list[DiscoveryEdge]:
    edges: list[DiscoveryEdge] = []
    paths = {node.node_id: _normalized_path(node.canonical_url) for node in nodes}
    by_id = {node.node_id: node for node in nodes}
    for child in nodes:
        parent_id = _find_parent_id(child.node_id, paths)
        if not parent_id:
            continue
        parent = by_id[parent_id]
        if child.node_id not in parent.child_ids:
            parent.child_ids.append(child.node_id)
        if parent.node_id not in child.parent_ids:
            child.parent_ids.append(parent.node_id)
        edges.append(
            DiscoveryEdge(
                from_node_id=parent.node_id,
                to_node_id=child.node_id,
                edge_type="parent_child",
                source=child.source,
            )
        )
    return edges


def _find_parent_id(child_id: str, paths: dict[str, str]) -> str:
    child_path = paths.get(child_id, "")
    candidates = [
        (node_id, path)
        for node_id, path in paths.items()
        if node_id != child_id and _is_parent_path(path, child_path)
    ]
    if not candidates:
        return ""
    return max(candidates, key=lambda item: len(item[1]))[0]


def _is_parent_path(parent_path: str, child_path: str) -> bool:
    if not parent_path or not child_path or parent_path == child_path:
        return False
    return child_path.startswith(f"{parent_path}/")


def _normalized_path(url: str) -> str:
    return urlparse(str(url or "")).path.rstrip("/")
