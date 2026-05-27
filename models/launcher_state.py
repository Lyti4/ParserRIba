"""State models for the desktop launcher."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LauncherTaskStatus = Literal["idle", "running", "succeeded", "failed"]


class LauncherSelectionState(BaseModel):
    """Current store/intent/category selection in the launcher."""

    shop: str = "pyaterochka"
    intent: str = "fish_catalog"
    categories: list[str] = Field(default_factory=list)
    selected_catalog_nodes: list[dict[str, Any]] = Field(default_factory=list)
    selected_product_ids: list[str] = Field(default_factory=list)


class LauncherProfileState(BaseModel):
    """Current store profile context shown and persisted by the launcher."""

    profile_id: str = ""
    profile_version_id: str = ""
    site_url: str = ""
    domain: str = ""
    shop: str = ""
    display_name: str = ""
    settings: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class LauncherCatalogState(BaseModel):
    """Current catalog tree and selected catalog-node workspace."""

    full_tree: list[dict[str, Any]] = Field(default_factory=list)
    full_links: list[dict[str, Any]] = Field(default_factory=list)
    selected_nodes: list[dict[str, Any]] = Field(default_factory=list)
    selected_node_urls: list[str] = Field(default_factory=list)
    catalog_type: str = ""
    updated_at: str = ""


class LauncherProductWorkspaceState(BaseModel):
    """Current collected-product workspace summary."""

    products_count: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)
    source_categories: list[str] = Field(default_factory=list)
    selected_product_ids: list[str] = Field(default_factory=list)
    json_path: str = ""
    excel_path: str = ""
    discovered_fields: dict[str, Any] = Field(default_factory=dict)


class LauncherDynamicFilterState(BaseModel):
    """Dynamic filter schema and values derived from collected products."""

    available_filters: dict[str, Any] = Field(default_factory=dict)
    applied_values: dict[str, Any] = Field(default_factory=dict)
    counts: dict[str, Any] = Field(default_factory=dict)
    ranges: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    updated_at: str = ""


class LauncherFilterState(BaseModel):
    """Current post-capture filters selected in the launcher."""

    suppliers: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    min_price: float | None = None
    max_price: float | None = None
    in_stock: bool | None = None
    wine_styles: list[str] = Field(default_factory=list)
    alcohol_types: list[str] = Field(default_factory=list)
    sugar_classes: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    strict_missing: bool = False


class LauncherSettingsState(BaseModel):
    """Persisted launcher settings for local desktop use."""

    output_dir: str = ""
    headless: bool = True
    manual_wait: bool = False
    attempts: int = 1
    listen_seconds: int = 6
    remember_last_selection: bool = True


class LauncherTaskState(BaseModel):
    """Current task execution state shown in the launcher."""

    status: LauncherTaskStatus = "idle"
    task_name: str = ""
    task_kind: str = ""
    phase: str = ""
    progress_current: int = 0
    progress_total: int = 0
    started_at: str = ""
    finished_at: str = ""
    source_profile_id: str = ""
    message: str = ""
    last_error: str = ""


class LauncherResearchState(BaseModel):
    """Current launcher research progress and active profile summary."""

    mode: Literal["live", "quiet"] = "live"
    current_phase: str = ""
    current_status: str = ""
    streamed_categories: list[str] = Field(default_factory=list)
    active_profile_id: str = ""
    active_profile_version_id: str = ""


class LauncherResultState(BaseModel):
    """Last normalized launcher result available to the UI."""

    launcher_view: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    products_count: int = 0
    source_profile_id: str = ""
    filter_snapshot: dict[str, Any] = Field(default_factory=dict)
    excel_path: str = ""
    json_path: str = ""
    report_dir: str = ""


class LauncherAppState(BaseModel):
    """Full launcher state snapshot."""

    profile: LauncherProfileState = Field(default_factory=LauncherProfileState)
    catalog: LauncherCatalogState = Field(default_factory=LauncherCatalogState)
    products: LauncherProductWorkspaceState = Field(default_factory=LauncherProductWorkspaceState)
    dynamic_filters: LauncherDynamicFilterState = Field(default_factory=LauncherDynamicFilterState)
    selection: LauncherSelectionState = Field(default_factory=LauncherSelectionState)
    filters: LauncherFilterState = Field(default_factory=LauncherFilterState)
    settings: LauncherSettingsState = Field(default_factory=LauncherSettingsState)
    task: LauncherTaskState = Field(default_factory=LauncherTaskState)
    research: LauncherResearchState = Field(default_factory=LauncherResearchState)
    result: LauncherResultState = Field(default_factory=LauncherResultState)
