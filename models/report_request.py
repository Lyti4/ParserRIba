"""Report request contracts for launcher-driven local exports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExportSelection(BaseModel):
    """Pre-capture or report selection chosen by the launcher."""

    shop: str
    intent: str = "fish_catalog"
    categories: list[str] = Field(default_factory=list)
    selected_product_ids: list[str] = Field(default_factory=list)


class ProductFilter(BaseModel):
    """Post-capture product filters applied while building reports."""

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


class ReportRequest(BaseModel):
    """Machine-readable request for building a local report from storage."""

    selection: ExportSelection
    filters: ProductFilter = Field(default_factory=ProductFilter)
    output_name: str = ""
    output_format: Literal["xlsx"] = "xlsx"


class ReportBuildResult(BaseModel):
    """Machine-readable result for one generated report."""

    report_path: str
    products_count: int
    categories: list[str] = Field(default_factory=list)
    filters_applied: dict[str, object] = Field(default_factory=dict)
    report_summary: dict[str, object] = Field(default_factory=dict)


class ReportFilterOptionsResult(BaseModel):
    """Machine-readable available filter values for one report selection."""

    shop: str
    intent: str
    products_count: int
    categories: list[str] = Field(default_factory=list)
    available_filters: dict[str, list[str]] = Field(default_factory=dict)
    available_filter_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
