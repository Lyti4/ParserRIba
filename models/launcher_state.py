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
    excel_path: str = ""
    json_path: str = ""
    report_dir: str = ""


class LauncherAppState(BaseModel):
    """Full launcher state snapshot."""

    selection: LauncherSelectionState = Field(default_factory=LauncherSelectionState)
    filters: LauncherFilterState = Field(default_factory=LauncherFilterState)
    settings: LauncherSettingsState = Field(default_factory=LauncherSettingsState)
    task: LauncherTaskState = Field(default_factory=LauncherTaskState)
    research: LauncherResearchState = Field(default_factory=LauncherResearchState)
    result: LauncherResultState = Field(default_factory=LauncherResultState)
