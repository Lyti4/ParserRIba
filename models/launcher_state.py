"""State models for the desktop launcher."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

LauncherTaskStatus = Literal["idle", "running", "succeeded", "failed"]
FavoriteType = Literal["store", "catalog_node", "product"]
FavoriteRefreshCapability = Literal["supported", "limited", "unsupported", "unresolved"]
FavoriteRefreshStatus = Literal["never", "success", "skipped", "failed", "partial"]


class LauncherSelectionState(BaseModel):
    """Current store/intent/category selection in the launcher."""

    shop: str = ""
    intent: str = ""
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


class LauncherWorkspaceState(BaseModel):
    """Current project workspace context above store profiles."""

    workspace_id: str = ""
    name: str = ""
    description: str = ""
    is_default: bool = False
    settings: dict[str, Any] = Field(default_factory=dict)


class WorkspaceProfileSelectionState(BaseModel):
    """Selected store profile inside the active project workspace."""

    workspace_id: str = ""
    selected_profile_id: str = ""
    selected_version_id: str = ""


class WorkspaceFavoriteState(BaseModel):
    """User favorite scoped to one project workspace."""

    favorite_id: str = ""
    workspace_id: str = ""
    profile_id: str = ""
    favorite_type: FavoriteType = "store"
    display_label: str = ""
    store_label: str = ""
    stable_key: str = ""
    source_version_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    refresh_capability: FavoriteRefreshCapability = "unresolved"
    last_refresh_status: FavoriteRefreshStatus = "never"
    last_refresh_message: str = ""
    last_refreshed_at: str = ""
    created_at: str = ""
    updated_at: str = ""


class FavoriteRefreshRunState(BaseModel):
    """One user-triggered favorite refresh batch."""

    refresh_run_id: str = ""
    workspace_id: str = ""
    requested_scope: Literal["selected", "all_refreshable"] = "selected"
    overall_status: FavoriteRefreshStatus = "never"
    requested_count: int = 0
    success_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    started_at: str = ""
    finished_at: str = ""


class FavoriteRefreshResultState(BaseModel):
    """Per-favorite result inside a refresh batch."""

    refresh_run_id: str = ""
    favorite_id: str = ""
    workspace_id: str = ""
    profile_id: str = ""
    status: FavoriteRefreshStatus = "never"
    reason: str = ""
    saved_version_id: str = ""
    artifact_refs: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""


class LauncherThemePreferenceState(BaseModel):
    """Local launcher theme preference."""

    theme_mode: Literal["light", "dark"] = "dark"
    updated_at: str = ""


class LauncherFavoritesState(BaseModel):
    """Favorites visible in the active workspace."""

    items: list[WorkspaceFavoriteState] = Field(default_factory=list)
    selected_favorite_ids: list[str] = Field(default_factory=list)
    latest_refresh: FavoriteRefreshRunState = Field(default_factory=FavoriteRefreshRunState)


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


class LauncherReportState(BaseModel):
    """Current report-column selection for Excel generation."""

    available_columns: list[str] = Field(default_factory=list)
    selected_columns: list[str] = Field(default_factory=list)
    column_titles: dict[str, str] = Field(default_factory=dict)
    columns_touched: bool = False


class LauncherFilterState(BaseModel):
    """Current post-capture filters selected in the launcher."""

    suppliers: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    min_price: float | None = None
    max_price: float | None = None
    in_stock: bool | None = None
    subcategories: list[str] = Field(default_factory=list)
    wine_styles: list[str] = Field(default_factory=list)
    alcohol_types: list[str] = Field(default_factory=list)
    sugar_classes: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    found_filters: dict[str, list[str]] = Field(default_factory=dict)
    strict_missing: bool = False

    @model_validator(mode="before")
    @classmethod
    def _sync_subcategory_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        values = data.get("subcategories") or data.get("wine_styles")
        if values:
            data = dict(data)
            data.setdefault("subcategories", values)
            data.setdefault("wine_styles", values)
        return data

    @model_validator(mode="after")
    def _ensure_subcategory_aliases(self) -> "LauncherFilterState":
        values = self.subcategories or self.wine_styles
        if values:
            object.__setattr__(self, "subcategories", list(values))
            object.__setattr__(self, "wine_styles", list(values))
        return self

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"subcategories", "wine_styles"}:
            values = [str(item) for item in (value or []) if str(item).strip()]
            object.__setattr__(self, "subcategories", list(values))
            object.__setattr__(self, "wine_styles", list(values))
            return
        super().__setattr__(name, value)


class LauncherSettingsState(BaseModel):
    """Persisted launcher settings for local desktop use."""

    output_dir: str = ""
    headless: bool = True
    manual_wait: bool = False
    attempts: int = 1
    listen_seconds: int = 6
    browser_runtime: str = "camoufox"
    remember_last_selection: bool = True
    theme_mode: Literal["light", "dark"] = "dark"


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

    workspace: LauncherWorkspaceState = Field(default_factory=LauncherWorkspaceState)
    workspace_selection: WorkspaceProfileSelectionState = Field(default_factory=WorkspaceProfileSelectionState)
    profile: LauncherProfileState = Field(default_factory=LauncherProfileState)
    catalog: LauncherCatalogState = Field(default_factory=LauncherCatalogState)
    products: LauncherProductWorkspaceState = Field(default_factory=LauncherProductWorkspaceState)
    dynamic_filters: LauncherDynamicFilterState = Field(default_factory=LauncherDynamicFilterState)
    report: LauncherReportState = Field(default_factory=LauncherReportState)
    selection: LauncherSelectionState = Field(default_factory=LauncherSelectionState)
    filters: LauncherFilterState = Field(default_factory=LauncherFilterState)
    settings: LauncherSettingsState = Field(default_factory=LauncherSettingsState)
    favorites: LauncherFavoritesState = Field(default_factory=LauncherFavoritesState)
    task: LauncherTaskState = Field(default_factory=LauncherTaskState)
    research: LauncherResearchState = Field(default_factory=LauncherResearchState)
    result: LauncherResultState = Field(default_factory=LauncherResultState)
