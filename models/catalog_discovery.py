"""Typed models for store-neutral catalog discovery."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CatalogSurfaceType = Literal[
    "category_tree",
    "product_listing",
    "api_backed",
    "pdf_flipbook",
    "region_gate",
    "challenge",
    "blocked",
    "unknown",
]
DiscoverySource = Literal["dom", "network", "mixed", "manual_confirmed"]
ValidationState = Literal[
    "unknown",
    "listing_valid",
    "menu_only",
    "promo",
    "pdf_flipbook",
    "region_gate",
    "challenge",
    "blocked",
    "empty",
]
DiscoveryEdgeType = Literal[
    "parent_child",
    "cross_link",
    "duplicate_candidate",
    "alternative_source_confirmation",
]


class CategoryEvidence(BaseModel):
    """One discovered category-like link."""

    name: str = ""
    url: str
    source: str = "html"


class ProductLinkEvidence(BaseModel):
    """One discovered product-like link."""

    name: str = ""
    url: str
    source: str = "html"


class ApiEvidence(BaseModel):
    """One API hint discovered from page markup."""

    kind: str
    value: str
    source: str = "html"


class DocumentEvidence(BaseModel):
    """One document-like asset discovered from page markup."""

    kind: str
    url: str
    source: str = "html"


class RouteHint(BaseModel):
    """One route or API hint attached to a discovery node."""

    kind: str
    value: str
    source: DiscoverySource = "dom"


class DiscoveryNode(BaseModel):
    """Rich internal discovery node retained for future research flows."""

    node_id: str
    label_ru: str
    label_original: str = ""
    canonical_url: str = ""
    candidate_urls: list[str] = Field(default_factory=list)
    child_ids: list[str] = Field(default_factory=list)
    parent_ids: list[str] = Field(default_factory=list)
    source: DiscoverySource = "dom"
    validation_state: ValidationState = "unknown"
    listing_confidence: float = 0.0
    route_hints: list[RouteHint] = Field(default_factory=list)
    protection_signals: list[str] = Field(default_factory=list)
    manual_step_seen: bool = False
    last_seen_run_id: str = ""
    raw_evidence_refs: list[str] = Field(default_factory=list)


class DiscoveryEdge(BaseModel):
    """Relationship between discovered nodes."""

    from_node_id: str
    to_node_id: str
    edge_type: DiscoveryEdgeType = "parent_child"
    source: DiscoverySource = "dom"


class SiteProfileVersion(BaseModel):
    """Persisted discovery profile snapshot for one site run."""

    profile_id: str
    version_id: str
    shop_slug: str
    site_url: str
    run_id: str
    primary_root_ids: list[str] = Field(default_factory=list)
    nodes: list[DiscoveryNode] = Field(default_factory=list)
    edges: list[DiscoveryEdge] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DiscoveryPhaseEvent(BaseModel):
    """Launcher-facing phase update emitted during site research."""

    phase: str
    status: str
    message_ru: str
    discovered_categories: list[str] = Field(default_factory=list)


class CatalogDiscoveryResult(BaseModel):
    """Store-neutral summary of a catalog surface."""

    reachable: bool
    status_code: int
    final_url: str
    surface_type: CatalogSurfaceType
    products_path_seen: bool = False
    pagination_hint: bool = False
    region_hint: bool = False
    challenge_hint: bool = False
    blocked_hint: bool = False
    csrf_meta_detected: bool = False
    category_links: list[CategoryEvidence] = Field(default_factory=list)
    product_links: list[ProductLinkEvidence] = Field(default_factory=list)
    api_hints: list[ApiEvidence] = Field(default_factory=list)
    documents: list[DocumentEvidence] = Field(default_factory=list)
    discovery_source: DiscoverySource = "dom"
    validation_state: ValidationState = "unknown"
    profile_id: str = ""
    profile_version_id: str = ""
    primary_root_ids: list[str] = Field(default_factory=list)
    nodes: list[DiscoveryNode] = Field(default_factory=list)
    edges: list[DiscoveryEdge] = Field(default_factory=list)
    phase_events: list[DiscoveryPhaseEvent] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    error: str = ""
