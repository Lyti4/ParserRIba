"""Report request contracts for launcher-driven local exports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ExportSelection(BaseModel):
    """Pre-capture or report selection chosen by the launcher."""

    shop: str
    intent: str
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
    def _ensure_subcategory_aliases(self) -> "ProductFilter":
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


class ReportRequest(BaseModel):
    """Machine-readable request for building a local report from storage."""

    selection: ExportSelection
    filters: ProductFilter = Field(default_factory=ProductFilter)
    report_columns: list[str] | None = None
    report_column_titles: dict[str, str] = Field(default_factory=dict)
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
