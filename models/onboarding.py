"""Versioned models for guided site onboarding."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1
OnboardingStatus = Literal["discovery_only", "needs_operator", "scaffold_ready", "runtime_ready", "failed"]


class DiscoveredCategoryNode(BaseModel):
    """Normalized site category node for launcher selection."""

    name: str = Field(..., description="Display name of the category")
    url: str = Field(..., description="Absolute or site-relative category URL")
    children: list["DiscoveredCategoryNode"] = Field(default_factory=list)


class ArtifactPaths(BaseModel):
    """Paths created for one onboarding session."""

    runtime_db_path: str = ""
    runtime_report_dir: str = ""
    session_state_path: str = ""
    kb_draft_path: str = ""


class OnboardingResult(BaseModel):
    """Stable result contract for guided launcher onboarding."""

    session_id: str
    shop_slug: str
    site_url: str
    intent: str = "fish_catalog"
    status: OnboardingStatus
    category_tree: list[DiscoveredCategoryNode] = Field(default_factory=list)
    selected_categories: list[str] = Field(default_factory=list)
    active_profile_id: str = ""
    active_profile_version_id: str = ""
    streamed_categories: list[str] = Field(default_factory=list)
    research_mode: str = "live"
    current_phase: str = ""
    artifact_paths: ArtifactPaths = Field(default_factory=ArtifactPaths)
    diagnostics_summary: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(arbitrary_types_allowed=True)
