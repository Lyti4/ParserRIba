"""Source-neutral desktop bridge for one canonical ProductWorkspace artifact."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from application.contracts import ApplicationContractError, NormalizedProduct, ProductObservation
from application.workspace import ProductWorkspace, WorkspaceExportRequest, WorkspaceFilter
from models.launcher_state import LauncherAppState


_NORMALIZED_FACET_FIELDS = frozenset(
    {"category", "price", "availability", "brand", "supplier", "country"}
)


def load_current_workspace(state: LauncherAppState) -> ProductWorkspace:
    """Load the current strict workspace artifact without a legacy fallback."""
    raw_path = state.result.artifact_paths.get("workspace_json")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ApplicationContractError(
            "DESKTOP_WORKSPACE_REQUIRED",
            "DESKTOP_WORKSPACE_REQUIRED: Collect or load one source-neutral product workspace first.",
        )
    return ProductWorkspace.load_json(Path(raw_path))


def workspace_product_items(workspace: ProductWorkspace) -> list[dict[str, Any]]:
    """Project canonical products into the existing desktop table shape."""
    observations = {item.observation_id: item for item in workspace.observations}
    result: list[dict[str, Any]] = []
    for product in workspace.normalized_products:
        observation = observations[product.observation_id]
        exact_facets = _exact_facets(product, observation, workspace)
        item: dict[str, Any] = {
            "id": product.normalized_product_id,
            "product_id": product.normalized_product_id,
            "name": product.name,
            "category": product.category or "",
            "brand": product.brand or "",
            "supplier": product.supplier,
            "price": {"current": product.price} if product.price is not None else {},
            "in_stock": product.availability,
            "raw_data": exact_facets,
        }
        result.append(item)
    return result


def workspace_facet_counts(workspace: ProductWorkspace) -> dict[str, dict[str, int]]:
    """Return display counts keyed by exact source-neutral discovered field IDs."""
    observations = {item.observation_id: item for item in workspace.observations}
    counts: dict[str, dict[str, int]] = {}
    for definition in workspace.discovered_fields():
        if not definition.is_filterable or not _supported_facet_id(definition.field_id):
            continue
        available_values = _facet_values_by_label(workspace, definition.field_id)
        field_counts: dict[str, int] = {}
        for product in workspace.normalized_products:
            values = _workspace_field_values(
                product,
                observations[product.observation_id],
                definition.field_id,
            )
            for value in _unique_scalars(values):
                label = facet_option_label(value, available_values)
                field_counts[label] = field_counts.get(label, 0) + 1
        if field_counts:
            counts[definition.field_id] = {
                key: field_counts[key] for key in sorted(field_counts)
            }
    return counts


def write_selected_workspace_export(
    state: LauncherAppState,
    output_path: Path,
    *,
    include_provenance: bool = False,
) -> Path:
    """Write an export for exact selected normalized-product IDs."""
    workspace = load_current_workspace(state)
    request = WorkspaceExportRequest(
        product_ids=tuple(state.selection.selected_product_ids),
        include_provenance=include_provenance,
    )
    return workspace.write_export_json(output_path, request)


def write_filtered_workspace_export(
    state: LauncherAppState,
    output_path: Path,
    *,
    include_provenance: bool = False,
) -> Path:
    """Write an export for exact generic facet IDs selected in the desktop state."""
    workspace = load_current_workspace(state)
    definitions = {item.field_id: item for item in workspace.discovered_fields()}
    selected: dict[str, tuple[Any, ...]] = {}
    for field_id, raw_values in state.filters.found_filters.items():
        if not raw_values:
            continue
        definition = definitions.get(field_id)
        if definition is None or not definition.is_filterable or not _supported_facet_id(field_id):
            raise ApplicationContractError(
                "DESKTOP_WORKSPACE_FILTER_INVALID",
                f"DESKTOP_WORKSPACE_FILTER_INVALID: Field is not an exact filterable workspace facet: {field_id}.",
            )
        available_values = _facet_values_by_label(workspace, field_id)
        typed_values: list[Any] = []
        for value in raw_values:
            if not isinstance(value, str) or value not in available_values:
                raise ApplicationContractError(
                    "DESKTOP_WORKSPACE_FILTER_VALUE_INVALID",
                    "DESKTOP_WORKSPACE_FILTER_VALUE_INVALID: The selected value is not present in the current workspace facet.",
                )
            typed_values.extend(available_values[value])
        selected[field_id] = tuple(_unique_scalars(typed_values))
    request = WorkspaceExportRequest(
        filter_selection=WorkspaceFilter(
            facet_filters=selected,
            strict=state.filters.strict_missing,
            exact_text=True,
        ),
        include_provenance=include_provenance,
    )
    return workspace.write_export_json(output_path, request)


def write_whole_workspace_export(
    state: LauncherAppState,
    output_path: Path,
    *,
    include_provenance: bool = False,
) -> Path:
    """Write an explicitly requested whole-workspace export."""
    workspace = load_current_workspace(state)
    request = WorkspaceExportRequest(
        export_workspace=True,
        include_provenance=include_provenance,
    )
    return workspace.write_export_json(output_path, request)


def _exact_facets(
    product: NormalizedProduct,
    observation: ProductObservation,
    workspace: ProductWorkspace,
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for definition in workspace.discovered_fields():
        if not definition.is_filterable or not _supported_facet_id(definition.field_id):
            continue
        scalars = _workspace_field_values(product, observation, definition.field_id)
        if len(scalars) == 1:
            values[definition.field_id] = scalars[0]
        elif scalars:
            values[definition.field_id] = list(scalars)
    return values


def _supported_facet_id(field_id: str) -> bool:
    prefix, separator, suffix = field_id.partition(".")
    if not separator:
        return False
    if prefix == "normalized":
        return suffix in _NORMALIZED_FACET_FIELDS
    return prefix in {"attributes", "source_fields"}


def _workspace_field_values(
    product: NormalizedProduct,
    observation: ProductObservation,
    field_id: str,
) -> tuple[Any, ...]:
    prefix, separator, suffix = field_id.partition(".")
    if not separator:
        return ()
    root: Mapping[str, Any]
    if prefix == "attributes":
        root = product.attributes
    elif prefix == "source_fields":
        root = observation.source_fields
    elif prefix == "normalized" and suffix in _NORMALIZED_FACET_FIELDS:
        value = getattr(product, suffix)
        return () if value is None else (value,)
    else:
        return ()
    return _nested_scalar_values(root, tuple(suffix.split(".")))


def _nested_scalar_values(value: Any, path: tuple[str, ...]) -> tuple[Any, ...]:
    if path:
        if not isinstance(value, Mapping) or path[0] not in value:
            return ()
        return _nested_scalar_values(value[path[0]], path[1:])
    return _all_scalar_values(value)


def _all_scalar_values(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (str, int, float, Decimal, bool)) and value is not None:
        return (value,)
    if isinstance(value, Mapping):
        return tuple(
            scalar
            for nested in value.values()
            for scalar in _all_scalar_values(nested)
        )
    if isinstance(value, (tuple, list)):
        return tuple(scalar for nested in value for scalar in _all_scalar_values(nested))
    return ()


def _unique_scalars(values: Iterable[Any]) -> tuple[Any, ...]:
    unique: dict[tuple[str, str], Any] = {}
    for value in values:
        key = (type(value).__name__, repr(value))
        unique.setdefault(key, value)
    return tuple(unique.values())


def _canonical_facet_label(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
        label = format(number.normalize(), "f")
        return "0" if label == "-0" else label
    return json.dumps(str(value), ensure_ascii=False)


def facet_option_label(value: Any, available_labels: Iterable[str] = ()) -> str:
    """Resolve a canonical workspace label, preserving undeclared legacy labels."""
    canonical_label = _canonical_facet_label(value)
    labels = frozenset(available_labels)
    if canonical_label in labels:
        return canonical_label
    return str(value)


def _facet_values_by_label(
    workspace: ProductWorkspace,
    field_id: str,
) -> dict[str, tuple[Any, ...]]:
    observations = {item.observation_id: item for item in workspace.observations}
    grouped: dict[str, list[Any]] = {}
    for product in workspace.normalized_products:
        for value in _workspace_field_values(
            product,
            observations[product.observation_id],
            field_id,
        ):
            grouped.setdefault(_canonical_facet_label(value), []).append(value)
    return {label: _unique_scalars(values) for label, values in grouped.items()}
