"""Source-neutral in-memory workspace built from completed collection results."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from numbers import Real
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from application.contracts import (
    ApplicationContractError,
    CollectionResult,
    FieldDefinition,
    FieldValueType,
    NormalizedProduct,
    ProductObservation,
)


_WORKSPACE_FORMAT = "parserriba-product-workspace-v1"
_WORKSPACE_KEYS = frozenset(
    {"format", "observations", "normalized_products", "field_definitions"}
)
_NORMALIZED_FACET_FIELDS = (
    "category",
    "price",
    "availability",
    "brand",
    "supplier",
    "country",
)


@dataclass(frozen=True)
class WorkspaceFilter:
    """Explicit facet selection; absent values remain visible unless strict filtering is requested."""

    facet_filters: Mapping[str, tuple[Any, ...]]
    strict: bool = False
    exact_text: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.facet_filters, Mapping)
            or type(self.strict) is not bool
            or type(self.exact_text) is not bool
        ):
            raise ApplicationContractError(
                "WORKSPACE_FILTER_INVALID",
                "WORKSPACE_FILTER_INVALID: Filters must use explicit field IDs, scalar values, and boolean strict/exact-text flags.",
            )
        if not self.facet_filters:
            raise ApplicationContractError(
                "WORKSPACE_FILTER_REQUIRED",
                "WORKSPACE_FILTER_REQUIRED: An explicit filtered selection requires at least one facet.",
            )
        normalized: dict[str, tuple[Any, ...]] = {}
        for field_id, values in self.facet_filters.items():
            if not isinstance(field_id, str) or not field_id or field_id != field_id.strip():
                raise ApplicationContractError(
                    "WORKSPACE_FILTER_INVALID",
                    "WORKSPACE_FILTER_INVALID: Each explicit workspace facet needs a non-empty field ID.",
                )
            if (
                not isinstance(values, tuple)
                or not values
                or any(_scalar_field_value_type(value) is None for value in values)
            ):
                raise ApplicationContractError(
                    "WORKSPACE_FILTER_INVALID",
                    "WORKSPACE_FILTER_INVALID: Each explicit workspace facet needs at least one scalar value.",
                )
            normalized[field_id] = values
        object.__setattr__(self, "facet_filters", MappingProxyType(normalized))


@dataclass(frozen=True)
class WorkspaceExportRequest:
    """Exactly one explicit selected-product, filtered-selection, or full-workspace export request."""

    product_ids: tuple[str, ...] = ()
    filter_selection: WorkspaceFilter | None = None
    export_workspace: bool = False
    include_provenance: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.product_ids, tuple)
            or type(self.export_workspace) is not bool
            or type(self.include_provenance) is not bool
            or (self.filter_selection is not None and not isinstance(self.filter_selection, WorkspaceFilter))
        ):
            raise ApplicationContractError(
                "WORKSPACE_EXPORT_SELECTION_INVALID",
                "WORKSPACE_EXPORT_SELECTION_INVALID: Export selection must use explicit IDs, an explicit filter, or a boolean whole-workspace flag.",
            )
        if any(
            not isinstance(product_id, str) or not product_id or product_id != product_id.strip()
            for product_id in self.product_ids
        ) or len(set(self.product_ids)) != len(self.product_ids):
            raise ApplicationContractError(
                "WORKSPACE_EXPORT_SELECTION_INVALID",
                "WORKSPACE_EXPORT_SELECTION_INVALID: Product IDs must be explicit, non-empty, and unique.",
            )
        selection_count = sum(
            (
                bool(self.product_ids),
                self.filter_selection is not None,
                self.export_workspace,
            )
        )
        if selection_count != 1:
            raise ApplicationContractError(
                "WORKSPACE_EXPORT_SELECTION_REQUIRED",
                "WORKSPACE_EXPORT_SELECTION_REQUIRED: Choose explicit product IDs, an explicit filtered selection, or explicitly export this workspace.",
            )


@dataclass(frozen=True)
class WorkspaceExport:
    """Pure source-neutral export projection; writing remains a separate local operation."""

    product_ids: tuple[str, ...]
    rows: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "rows", tuple(MappingProxyType(dict(row)) for row in self.rows)
        )


@dataclass(frozen=True)
class ProductWorkspace:
    """Canonical collection records and their separate declared/discovered field views."""

    observations: tuple[ProductObservation, ...]
    normalized_products: tuple[NormalizedProduct, ...]
    declared_field_definitions: tuple[FieldDefinition, ...]

    def __post_init__(self) -> None:
        observations_by_id = {item.observation_id: item for item in self.observations}
        if len(observations_by_id) != len(self.observations):
            raise ApplicationContractError(
                "WORKSPACE_OBSERVATION_DUPLICATE",
                "WORKSPACE_OBSERVATION_DUPLICATE: Observation IDs must be unique across a workspace.",
            )
        product_ids = {item.normalized_product_id for item in self.normalized_products}
        if len(product_ids) != len(self.normalized_products):
            raise ApplicationContractError(
                "WORKSPACE_PRODUCT_DUPLICATE",
                "WORKSPACE_PRODUCT_DUPLICATE: Normalized product IDs must be unique across a workspace.",
            )
        for product in self.normalized_products:
            observation = observations_by_id.get(product.observation_id)
            if observation is None or product.provenance != observation.provenance:
                raise ApplicationContractError(
                    "WORKSPACE_PRODUCT_PROVENANCE_INVALID",
                    "WORKSPACE_PRODUCT_PROVENANCE_INVALID: Every normalized product must retain matching stored observation provenance.",
                )
        definition_ids = {item.field_id for item in self.declared_field_definitions}
        if len(definition_ids) != len(self.declared_field_definitions):
            raise ApplicationContractError(
                "WORKSPACE_FIELD_DEFINITION_DUPLICATE",
                "WORKSPACE_FIELD_DEFINITION_DUPLICATE: Declared field IDs must be unique across a workspace.",
            )

    @classmethod
    def load_json(cls, path: Path) -> "ProductWorkspace":
        """Load only the strict local workspace v1 representation."""
        workspace_path = _required_local_json_path(
            path,
            code="WORKSPACE_PATH_INVALID",
            purpose="Workspace storage",
        )
        try:
            payload = json.loads(workspace_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApplicationContractError(
                "WORKSPACE_READ_FAILED",
                "WORKSPACE_READ_FAILED: The selected local workspace JSON cannot be read.",
            ) from error
        if not isinstance(payload, Mapping) or set(payload) != _WORKSPACE_KEYS:
            raise ApplicationContractError(
                "WORKSPACE_DOCUMENT_INVALID",
                "WORKSPACE_DOCUMENT_INVALID: The local workspace JSON must use the exact v1 fields.",
            )
        if payload.get("format") != _WORKSPACE_FORMAT:
            raise ApplicationContractError(
                "WORKSPACE_FORMAT_UNSUPPORTED",
                "WORKSPACE_FORMAT_UNSUPPORTED: The selected local workspace is not parserriba-product-workspace-v1.",
            )
        try:
            observations = tuple(ProductObservation.model_validate(item) for item in payload["observations"])
            products = tuple(NormalizedProduct.model_validate(item) for item in payload["normalized_products"])
            definitions = tuple(FieldDefinition.model_validate(item) for item in payload["field_definitions"])
        except (KeyError, TypeError, ValueError) as error:
            raise ApplicationContractError(
                "WORKSPACE_DOCUMENT_INVALID",
                "WORKSPACE_DOCUMENT_INVALID: Workspace records do not match source-neutral contracts.",
            ) from error
        return cls(
            observations=observations,
            normalized_products=products,
            declared_field_definitions=definitions,
        )

    def write_json(self, path: Path) -> Path:
        """Atomically persist only canonical workspace records at an explicit local JSON path."""
        workspace_path = _required_local_json_path(
            path,
            code="WORKSPACE_PATH_INVALID",
            purpose="Workspace storage",
        )
        payload = {
            "format": _WORKSPACE_FORMAT,
            "observations": [item.model_dump(mode="json") for item in self.observations],
            "normalized_products": [
                item.model_dump(mode="json") for item in self.normalized_products
            ],
            "field_definitions": [
                item.model_dump(mode="json") for item in self.declared_field_definitions
            ],
        }
        return _write_json_document(
            workspace_path,
            payload,
            code="WORKSPACE_WRITE_FAILED",
            purpose="The explicit local workspace JSON",
        )

    @classmethod
    def from_collection_results(
        cls, results: Iterable[CollectionResult]
    ) -> "ProductWorkspace":
        """Aggregate explicit results without merging source-specific fields or provenance."""
        received = tuple(results)
        if not received:
            raise ApplicationContractError(
                "WORKSPACE_COLLECTION_REQUIRED",
                "WORKSPACE_COLLECTION_REQUIRED: At least one CollectionResult is required.",
            )

        observations: list[ProductObservation] = []
        products: list[NormalizedProduct] = []
        definitions: list[FieldDefinition] = []
        observation_ids: set[str] = set()
        product_ids: set[str] = set()
        definitions_by_id: dict[str, FieldDefinition] = {}
        for result in received:
            for observation in result.observations:
                if observation.observation_id in observation_ids:
                    raise ApplicationContractError(
                        "WORKSPACE_OBSERVATION_DUPLICATE",
                        "WORKSPACE_OBSERVATION_DUPLICATE: Observation IDs must be unique across a workspace.",
                    )
                observation_ids.add(observation.observation_id)
                observations.append(observation)
            for product in result.normalized_products:
                if product.normalized_product_id in product_ids:
                    raise ApplicationContractError(
                        "WORKSPACE_PRODUCT_DUPLICATE",
                        "WORKSPACE_PRODUCT_DUPLICATE: Normalized product IDs must be unique across a workspace.",
                    )
                product_ids.add(product.normalized_product_id)
                products.append(product)
            for definition in result.field_definitions:
                existing = definitions_by_id.get(definition.field_id)
                if existing is None:
                    definitions_by_id[definition.field_id] = definition
                    definitions.append(definition)
                elif existing != definition:
                    raise ApplicationContractError(
                        "WORKSPACE_FIELD_DEFINITION_CONFLICT",
                        "WORKSPACE_FIELD_DEFINITION_CONFLICT: Repeated declared field IDs must have identical definitions.",
                    )
        return cls(
            observations=tuple(observations),
            normalized_products=tuple(products),
            declared_field_definitions=tuple(definitions),
        )

    def discovered_fields(self) -> tuple[FieldDefinition, ...]:
        """Return declared facets plus dynamically discovered scalar leaves from source-neutral fields."""
        inferred: dict[str, FieldValueType] = {}
        observations_by_id = {item.observation_id: item for item in self.observations}
        for product in self.normalized_products:
            observation = observations_by_id[product.observation_id]
            for field_name in _NORMALIZED_FACET_FIELDS:
                _record_scalar_value(
                    inferred,
                    f"normalized.{field_name}",
                    getattr(product, field_name),
                )
            self._record_scalar_fields(inferred, "attributes", product.attributes)
            self._record_scalar_fields(inferred, "source_fields", observation.source_fields)
        declared = {item.field_id: item for item in self.declared_field_definitions}
        fields = [
            declared.pop(
                field_id,
                FieldDefinition(
                    field_id=field_id,
                    display_label=field_id,
                    value_type=value_type,
                    is_filterable=True,
                ),
            )
            for field_id, value_type in inferred.items()
        ]
        fields.extend(declared.values())
        return tuple(sorted(fields, key=lambda field: field.field_id))

    def filter(self, selection: WorkspaceFilter) -> tuple[NormalizedProduct, ...]:
        """Return selected products without changing canonical records; missing facets are visible unless strict."""
        fields_by_id = {field.field_id: field for field in self.discovered_fields()}
        unknown = next(
            (field_id for field_id in selection.facet_filters if field_id not in fields_by_id),
            None,
        )
        if unknown is not None:
            raise ApplicationContractError(
                "WORKSPACE_FILTER_FIELD_UNKNOWN",
                f"WORKSPACE_FILTER_FIELD_UNKNOWN: Field is not discovered in this workspace: {unknown}.",
            )
        not_filterable = next(
            (
                field_id
                for field_id in selection.facet_filters
                if not fields_by_id[field_id].is_filterable
            ),
            None,
        )
        if not_filterable is not None:
            raise ApplicationContractError(
                "WORKSPACE_FILTER_FIELD_UNAVAILABLE",
                f"WORKSPACE_FILTER_FIELD_UNAVAILABLE: Field is declared but not filterable: {not_filterable}.",
            )
        observations_by_id = {item.observation_id: item for item in self.observations}
        return tuple(
            product
            for product in self.normalized_products
            if all(
                _facet_matches(
                    _workspace_field_values(
                        product,
                        observations_by_id[product.observation_id],
                        field_id,
                    ),
                    selected_values,
                    strict=selection.strict,
                    exact_text=selection.exact_text,
                )
                for field_id, selected_values in selection.facet_filters.items()
            )
        )

    def build_export(self, request: WorkspaceExportRequest) -> WorkspaceExport:
        """Build an explicit product/workspace projection with optional provenance columns."""
        products_by_id = {
            product.normalized_product_id: product for product in self.normalized_products
        }
        if request.export_workspace:
            selected = self.normalized_products
        elif request.filter_selection is not None:
            selected = self.filter(request.filter_selection)
        else:
            unknown = next(
                (product_id for product_id in request.product_ids if product_id not in products_by_id),
                None,
            )
            if unknown is not None:
                raise ApplicationContractError(
                    "WORKSPACE_EXPORT_PRODUCT_UNKNOWN",
                    f"WORKSPACE_EXPORT_PRODUCT_UNKNOWN: Product is not in this workspace: {unknown}.",
                )
            selected = tuple(products_by_id[product_id] for product_id in request.product_ids)
        observations_by_id = {item.observation_id: item for item in self.observations}
        return WorkspaceExport(
            product_ids=tuple(product.normalized_product_id for product in selected),
            rows=tuple(
                _export_row(
                    product,
                    observations_by_id[product.observation_id],
                    include_provenance=request.include_provenance,
                )
                for product in selected
            ),
        )

    def write_export_json(self, path: Path, request: WorkspaceExportRequest) -> Path:
        """Write only an explicitly selected source-neutral export to a local JSON file."""
        export_path = _required_local_json_path(
            path,
            code="WORKSPACE_EXPORT_PATH_INVALID",
            purpose="Export",
        )
        exported = self.build_export(request)
        payload = {
            "format": "parserriba-product-export-v1",
            "product_ids": list(exported.product_ids),
            "rows": [dict(row) for row in exported.rows],
        }
        return _write_json_document(
            export_path,
            payload,
            code="WORKSPACE_EXPORT_WRITE_FAILED",
            purpose="The explicit local export JSON",
        )

    @staticmethod
    def _record_scalar_fields(
        discovered: dict[str, FieldValueType], prefix: str, values: Mapping[str, Any]
    ) -> None:
        for name, value in values.items():
            _record_scalar_value(discovered, f"{prefix}.{name}", value)


def _required_local_json_path(path: Path, *, code: str, purpose: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute() or path.suffix.lower() != ".json":
        raise ApplicationContractError(
            code,
            f"{code}: {purpose} requires an explicit absolute local .json path.",
        )
    return path


def _write_json_document(
    path: Path,
    payload: Mapping[str, Any],
    *,
    code: str,
    purpose: str,
) -> Path:
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
        temporary_path.write_bytes(encoded)
        temporary_path.replace(path)
    except (OSError, TypeError, ValueError) as error:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ApplicationContractError(code, f"{code}: {purpose} cannot be written.") from error
    return path


def _export_row(
    product: NormalizedProduct,
    observation: ProductObservation,
    *,
    include_provenance: bool,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "normalized_product_id": product.normalized_product_id,
        "observation_id": product.observation_id,
        "name": product.name,
    }
    for field_name in ("category", "price", "availability", "brand", "supplier", "country"):
        value = getattr(product, field_name)
        if value is not None:
            row[f"normalized.{field_name}"] = value
    row.update(
        {
            f"attributes.{name}": _export_value(value)
            for name, value in product.attributes.items()
        }
    )
    row.update(
        {
            f"source_fields.{name}": _export_value(value)
            for name, value in observation.source_fields.items()
        }
    )
    if include_provenance:
        row.update(
            {
                f"provenance.{name}": value
                for name, value in product.provenance.model_dump(mode="json").items()
            }
        )
    return row


def _record_scalar_value(
    discovered: dict[str, FieldValueType], field_id: str, value: Any
) -> None:
    value_type = _scalar_field_value_type(value)
    if value_type is not None:
        discovered.setdefault(field_id, value_type)
        return
    if isinstance(value, Mapping):
        for name, nested in value.items():
            _record_scalar_value(discovered, f"{field_id}.{name}", nested)
        return
    if isinstance(value, tuple):
        for nested in value:
            _record_scalar_value(discovered, field_id, nested)


def _workspace_field_values(
    product: NormalizedProduct, observation: ProductObservation, field_id: str
) -> tuple[Any, ...]:
    prefix, separator, suffix = field_id.partition(".")
    if not separator:
        return ()
    if prefix == "attributes":
        return _nested_scalar_values(product.attributes, tuple(suffix.split(".")))
    if prefix == "source_fields":
        return _nested_scalar_values(observation.source_fields, tuple(suffix.split(".")))
    if prefix == "normalized" and suffix in _NORMALIZED_FACET_FIELDS:
        value = getattr(product, suffix)
        return () if value is None else (value,)
    return ()


def _nested_scalar_values(value: Any, path: tuple[str, ...]) -> tuple[Any, ...]:
    if not path:
        return _all_scalar_values(value)
    if isinstance(value, Mapping):
        nested = value.get(path[0])
        return () if nested is None else _nested_scalar_values(nested, path[1:])
    if isinstance(value, tuple):
        return tuple(
            scalar
            for item in value
            for scalar in _nested_scalar_values(item, path)
        )
    return ()


def _all_scalar_values(value: Any) -> tuple[Any, ...]:
    if _scalar_field_value_type(value) is not None:
        return (value,)
    if isinstance(value, Mapping):
        return tuple(
            scalar
            for nested in value.values()
            for scalar in _all_scalar_values(nested)
        )
    if isinstance(value, tuple):
        return tuple(scalar for nested in value for scalar in _all_scalar_values(nested))
    return ()


def _facet_matches(
    actual_values: tuple[Any, ...],
    selected_values: tuple[Any, ...],
    *,
    strict: bool,
    exact_text: bool,
) -> bool:
    if not actual_values:
        return not strict
    actual_keys = {
        _facet_comparison_key(value, exact_text=exact_text) for value in actual_values
    }
    return any(
        _facet_comparison_key(value, exact_text=exact_text) in actual_keys
        for value in selected_values
    )


def _export_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(name): _export_value(nested) for name, nested in value.items()}
    if isinstance(value, tuple):
        return [_export_value(nested) for nested in value]
    return value


def _facet_comparison_key(value: Any, *, exact_text: bool) -> tuple[str, Any]:
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, (Real, Decimal)) and not isinstance(value, bool):
        return ("number", Decimal(str(value)))
    if isinstance(value, str):
        return ("text", value if exact_text else " ".join(value.split()).casefold())
    return (type(value).__name__, value)


def _scalar_field_value_type(value: Any) -> FieldValueType | None:
    if isinstance(value, bool):
        return FieldValueType.BOOLEAN
    if isinstance(value, (Real, Decimal)) and not isinstance(value, bool):
        return FieldValueType.NUMBER
    if isinstance(value, str):
        return FieldValueType.TEXT
    return None
