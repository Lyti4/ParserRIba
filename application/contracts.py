"""Versioned P0-A application contracts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import math
import re
from types import MappingProxyType
from typing import Any, ClassVar, Literal, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from application.url_safety import (
    contains_restricted_artifact_reference,
    contains_sensitive_url_material,
)


_RESTRICTED_DATA_KEY = re.compile(
    r"(?i)^(?:"
    r"password|passwd|secret|token|api[_-]?key|access[_-]?token|authorization|bearer|credentials?|"
    r"cookies?|cookie[_-]?jar|proxy(?:[_-].*)?|proxies|profile(?:[_-](?:dir|path))?|"
    r"browser[_-]?profile|captcha(?:[_-].*)?|session(?:[_-].*)?|"
    r"(?:request|response)[_-]?headers?|headers?"
    r")$"
)
_SAFE_ARTIFACT_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_ALLOWED_EVENT_PAYLOAD_KEYS = frozenset(
    {
        "catalog_node_count",
        "catalog_node_id",
        "message",
        "product_count",
        "reason_code",
        "report_sha256",
        "retryable",
        "selected_product_count",
        "terminal_outcome",
    }
)


def is_restricted_data_key(value: Any) -> bool:
    """Return whether a mapping key names sensitive or operational data."""
    return not isinstance(value, str) or bool(_RESTRICTED_DATA_KEY.fullmatch(value.strip()))


def _assert_safe_text(value: Any) -> None:
    if isinstance(value, str):
        if contains_sensitive_url_material(value):
            raise ApplicationContractError(
                "EVENT_UNSAFE_TEXT", "Sensitive-looking text is not allowed in events."
            )
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if is_restricted_data_key(key):
                raise ApplicationContractError(
                    "EVENT_UNSAFE_TEXT", "Event text contains a sensitive assignment."
                )
            _assert_safe_text(key)
            _assert_safe_text(item)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            _assert_safe_text(nested)


def _assert_json_safe(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ApplicationContractError(
            "EVENT_PAYLOAD_NOT_JSON_SAFE",
            "EVENT_PAYLOAD_NOT_JSON_SAFE: Non-finite numbers are not allowed.",
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ApplicationContractError(
                    "EVENT_PAYLOAD_NOT_JSON_SAFE",
                    "EVENT_PAYLOAD_NOT_JSON_SAFE: Payload keys must be strings.",
                )
            _assert_json_safe(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _assert_json_safe(item)
        return
    raise ApplicationContractError(
        "EVENT_PAYLOAD_NOT_JSON_SAFE",
        "EVENT_PAYLOAD_NOT_JSON_SAFE: Payload values must be JSON-compatible.",
    )


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _deep_freeze(nested) for key, nested in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(nested) for nested in value)
    return value


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_value(nested) for key, nested in value.items()}
    if isinstance(value, tuple):
        return [_json_value(nested) for nested in value]
    return value


class ApplicationContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class RunState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    TERMINAL = "terminal"


class TerminalOutcome(str, Enum):
    READY = "ready"
    MANUAL_ACTION_REQUIRED = "manual_action_required"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    RUN_STARTED = "run_started"
    PROGRESS = "progress"
    TERMINAL = "terminal"


class ContractModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    contract_version: Literal[1] = 1

    @field_validator("contract_version", mode="before")
    @classmethod
    def _require_exact_v1(cls, value: Any) -> int:
        if type(value) is not int or value != 1:
            raise ValueError("contract_version must be the integer 1")
        return value


class StartResearchCommand(ContractModel):
    run_id: str
    workspace_id: str
    profile_id: str


class ReplaceCatalogSelectionCommand(ContractModel):
    run_id: str
    catalog_node_ids: tuple[str, ...]


class CollectProductsCommand(ContractModel):
    run_id: str
    catalog_node_ids: tuple[str, ...]


class SetSelectedProductsCommand(ContractModel):
    run_id: str
    product_ids: tuple[str, ...]


class GenerateReportCommand(ContractModel):
    run_id: str
    product_ids: tuple[str, ...]


class CancelRunCommand(ContractModel):
    run_id: str
    client_id: str


class GetRunQuery(ContractModel):
    run_id: str


class ListRunEventsQuery(ContractModel):
    run_id: str


class RunApplicationFixtureCommand(ContractModel):
    run_id: str
    workspace_id: str
    profile_id: str
    client_id: str
    clock_iso: str
    artifact_dir: str | None = None
    output_dir: str | None = None
    root_dir: str | None = None


class FilterProductsQuery(ContractModel):
    products: tuple[dict[str, Any], ...] | list[dict[str, Any]]
    spec: Any

    @field_validator("products")
    @classmethod
    def _validate_products(cls, value: tuple[dict[str, Any], ...] | list[dict[str, Any]]):
        for product in value:
            _require_restricted_key_safe_mapping(product, code="FILTER_PRODUCTS_QUERY_INVALID")
        return value


class FilterProductsResult(ContractModel):
    products: tuple[dict[str, Any], ...]

    @field_validator("products")
    @classmethod
    def _validate_products(cls, value: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        for product in value:
            _require_restricted_key_safe_mapping(product, code="FILTER_PRODUCTS_RESULT_INVALID")
        return value


class ApplicationEvent(ContractModel):
    run_id: str
    sequence: int = Field(ge=1)
    event_type: EventType
    created_at: str
    phase: str = ""
    progress_current: int = Field(default=0, ge=0)
    progress_total: int = Field(default=0, ge=0)
    reason_code: str = ""
    message: str = ""
    payload: Mapping[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _reject_sensitive_text(self) -> "ApplicationEvent":
        unsupported = sorted(set(self.payload) - _ALLOWED_EVENT_PAYLOAD_KEYS)
        if unsupported:
            raise ApplicationContractError(
                "EVENT_PAYLOAD_KEY_NOT_ALLOWED",
                "EVENT_PAYLOAD_KEY_NOT_ALLOWED: "
                f"Event payload key is not allowed: {unsupported[0]}.",
            )
        _assert_json_safe(self.payload)
        _assert_safe_text(
            (
                self.run_id,
                self.created_at,
                self.phase,
                self.reason_code,
                self.message,
                self.payload,
            )
        )
        return self

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "payload", _deep_freeze(self.payload))

    @field_serializer("payload")
    def _serialize_payload(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _json_value(value)


class EventJournal:
    _ALLOWED: ClassVar[frozenset[str]] = _ALLOWED_EVENT_PAYLOAD_KEYS

    def __init__(self, *, run_id: str, created_at: str) -> None:
        self.run_id = run_id
        self.created_at = created_at
        self._events: list[ApplicationEvent] = []
        self._terminal = False

    @property
    def events(self) -> tuple[ApplicationEvent, ...]:
        return tuple(self._events)

    def append(
        self,
        event_type: EventType,
        *,
        phase: str = "",
        progress_current: int = 0,
        progress_total: int = 0,
        reason_code: str = "",
        message: str = "",
        payload: Mapping[str, Any] | None = None,
        **extra_payload: Any,
    ) -> ApplicationEvent:
        if self._terminal:
            raise ApplicationContractError("EVENT_AFTER_TERMINAL", "No event may follow terminal.")
        safe_payload = dict(payload or {})
        safe_payload.update(extra_payload)
        unsupported = sorted(set(safe_payload) - self._ALLOWED)
        if unsupported:
            raise ApplicationContractError(
                "EVENT_PAYLOAD_KEY_NOT_ALLOWED", f"Event payload key is not allowed: {unsupported[0]}."
            )
        _assert_json_safe(safe_payload)
        _assert_safe_text(
            (
                self.run_id,
                self.created_at,
                phase,
                reason_code,
                message,
                safe_payload,
            )
        )
        event = ApplicationEvent(
            run_id=self.run_id,
            sequence=len(self._events) + 1,
            event_type=event_type,
            created_at=self.created_at,
            phase=phase,
            progress_current=progress_current,
            progress_total=progress_total,
            reason_code=reason_code,
            message=message,
            payload=safe_payload,
        )
        self._events.append(event)
        self._terminal = event.event_type is EventType.TERMINAL
        return event


class WorkflowRunResult(ContractModel):
    run_id: str
    run_state: RunState
    terminal_outcome: TerminalOutcome
    reason_code: str
    message: str
    retryable: bool
    started_at: str
    finished_at: str
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    events: tuple[ApplicationEvent, ...] = ()

    @field_validator("artifact_paths")
    @classmethod
    def _validate_artifact_paths(cls, value: Mapping[str, str]) -> Mapping[str, str]:
        return _require_safe_artifact_mapping(value, code="WORKFLOW_ARTIFACT_PATHS_INVALID")

    @field_validator("result")
    @classmethod
    def _validate_result(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _require_safe_mapping(value, code="WORKFLOW_RESULT_INVALID")


def _require_nonempty_safe_text(value: str, *, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplicationContractError(code, f"{code}: A non-empty string is required.")
    _assert_safe_text(value)
    return value


def require_artifact_run_id(value: Any) -> str:
    """Return one explicit filename-safe collection run identity."""
    if not isinstance(value, str) or not _SAFE_ARTIFACT_RUN_ID.fullmatch(value):
        raise ApplicationContractError(
            "COLLECTION_RUN_ID_ARTIFACT_INVALID",
            "COLLECTION_RUN_ID_ARTIFACT_INVALID: Use a filename-safe explicit collection run ID.",
        )
    return value


def _require_safe_locator(value: str, *, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplicationContractError(code, f"{code}: A non-empty string is required.")
    if contains_sensitive_url_material(value):
        raise ApplicationContractError(
            code,
            f"{code}: A locator must not contain sensitive or ambiguously encoded URL data.",
        )
    return value


def _assert_no_restricted_storage(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if is_restricted_data_key(key):
                raise ApplicationContractError(
                    "CONTRACT_RESTRICTED_STORAGE",
                    "Restricted browser, credential, proxy, CAPTCHA or session data is not allowed.",
                )
            _assert_no_restricted_storage(key)
            _assert_no_restricted_storage(nested)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            _assert_no_restricted_storage(nested)


def _require_safe_mapping(value: Mapping[str, Any], *, code: str) -> Mapping[str, Any]:
    _assert_json_safe(value)
    try:
        _assert_safe_text(value)
        _assert_no_restricted_storage(value)
    except ApplicationContractError as error:
        raise ApplicationContractError(code, f"{code}: Mapping contains unsafe text.") from error
    return value


def _require_restricted_key_safe_mapping(
    value: Mapping[str, Any], *, code: str
) -> Mapping[str, Any]:
    try:
        _assert_safe_text(value)
        _assert_no_restricted_storage(value)
    except ApplicationContractError as error:
        raise ApplicationContractError(code, f"{code}: Mapping contains unsafe text.") from error
    return value


def _require_safe_artifact_mapping(value: Mapping[str, str], *, code: str) -> Mapping[str, str]:
    _require_safe_mapping(value, code=code)
    if any(contains_restricted_artifact_reference(reference) for reference in value.values()):
        raise ApplicationContractError(code, f"{code}: Artifact reference is unsafe.")
    return value


class SourceKind(str, Enum):
    FIXTURE = "fixture"
    FILE = "file"
    BROWSER = "browser"
    API = "api"


class FieldValueType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"


class SourceProfile(ContractModel):
    """Explicit, non-secret configuration for one selected product source."""

    source_profile_id: str
    display_name: str
    source_kind: SourceKind
    source_locator: str
    adapter_id: str
    adapter_version: str

    @field_validator("source_profile_id", "display_name", "adapter_id", "adapter_version")
    @classmethod
    def _require_safe_identity(cls, value: str) -> str:
        return _require_nonempty_safe_text(value, code="SOURCE_PROFILE_TEXT_INVALID")

    @field_validator("source_locator")
    @classmethod
    def _require_safe_source_locator(cls, value: str) -> str:
        return _require_safe_locator(value, code="SOURCE_PROFILE_LOCATOR_INVALID")


class CatalogNode(ContractModel):
    """One source-scoped catalogue position that a caller may explicitly select."""

    source_profile_id: str
    catalog_node_id: str
    display_name: str
    parent_catalog_node_id: str | None = None
    locator: str | None = None

    @field_validator("source_profile_id", "catalog_node_id", "display_name")
    @classmethod
    def _require_safe_identity(cls, value: str) -> str:
        value = _require_nonempty_safe_text(value, code="CATALOG_NODE_TEXT_INVALID")
        if value != value.strip():
            raise ApplicationContractError(
                "CATALOG_NODE_TEXT_INVALID",
                "CATALOG_NODE_TEXT_INVALID: Catalog node text must not have surrounding whitespace.",
            )
        return value

    @field_validator("parent_catalog_node_id")
    @classmethod
    def _validate_optional_parent(cls, value: str | None) -> str | None:
        return None if value is None else _require_nonempty_safe_text(value, code="CATALOG_NODE_TEXT_INVALID")

    @field_validator("locator")
    @classmethod
    def _validate_optional_locator(cls, value: str | None) -> str | None:
        return None if value is None else _require_safe_locator(value, code="CATALOG_NODE_LOCATOR_INVALID")


class CollectionRequest(ContractModel):
    """The sole caller input for a source adapter collection run."""

    collection_run_id: str
    source_profile: SourceProfile
    catalog_nodes: tuple[CatalogNode, ...]
    runtime_settings: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("collection_run_id")
    @classmethod
    def _require_safe_run_id(cls, value: str) -> str:
        return require_artifact_run_id(value)

    @field_validator("runtime_settings")
    @classmethod
    def _validate_runtime_settings(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _require_safe_mapping(value, code="COLLECTION_RUNTIME_SETTINGS_INVALID")

    @model_validator(mode="after")
    def _require_explicit_selected_scope(self) -> "CollectionRequest":
        if not self.catalog_nodes:
            raise ApplicationContractError(
                "COLLECTION_SCOPE_REQUIRED",
                "COLLECTION_SCOPE_REQUIRED: At least one explicit CatalogNode is required.",
            )
        selected_ids: set[str] = set()
        for node in self.catalog_nodes:
            if node.source_profile_id != self.source_profile.source_profile_id:
                raise ApplicationContractError(
                    "COLLECTION_NODE_SOURCE_MISMATCH",
                    "COLLECTION_NODE_SOURCE_MISMATCH: CatalogNode belongs to another SourceProfile.",
                )
            if node.catalog_node_id in selected_ids:
                raise ApplicationContractError(
                    "COLLECTION_NODE_DUPLICATE",
                    "COLLECTION_NODE_DUPLICATE: A CatalogNode may be selected once only.",
                )
            selected_ids.add(node.catalog_node_id)
        return self

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "runtime_settings", _deep_freeze(self.runtime_settings))

    @field_serializer("runtime_settings")
    def _serialize_runtime_settings(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _json_value(value)


class Provenance(ContractModel):
    """Safe evidence tying one product record to an explicit collection selection."""

    source_profile_id: str
    adapter_id: str
    adapter_version: str
    collection_run_id: str
    catalog_node_id: str
    observed_at: str
    evidence_ref: str
    transformation_status: str

    @field_validator(
        "source_profile_id",
        "adapter_id",
        "adapter_version",
        "collection_run_id",
        "catalog_node_id",
        "transformation_status",
    )
    @classmethod
    def _require_safe_text(cls, value: str) -> str:
        return _require_nonempty_safe_text(value, code="PROVENANCE_TEXT_INVALID")

    @field_validator("evidence_ref")
    @classmethod
    def _require_safe_evidence_ref(cls, value: str) -> str:
        value = _require_safe_locator(value, code="PROVENANCE_EVIDENCE_REF_INVALID")
        if contains_restricted_artifact_reference(value):
            raise ApplicationContractError(
                "PROVENANCE_EVIDENCE_REF_INVALID",
                "PROVENANCE_EVIDENCE_REF_INVALID: Evidence reference is unsafe.",
            )
        return value

    @field_validator("observed_at")
    @classmethod
    def _require_timezone_timestamp(cls, value: str) -> str:
        value = _require_nonempty_safe_text(value, code="PROVENANCE_TIMESTAMP_INVALID")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ApplicationContractError(
                "PROVENANCE_TIMESTAMP_INVALID",
                "PROVENANCE_TIMESTAMP_INVALID: observed_at must be an ISO-8601 timestamp.",
            ) from error
        if parsed.tzinfo is None:
            raise ApplicationContractError(
                "PROVENANCE_TIMESTAMP_INVALID",
                "PROVENANCE_TIMESTAMP_INVALID: observed_at must include a timezone.",
            )
        return value


class ProductObservation(ContractModel):
    """Immutable source fields plus the provenance that explains them."""

    observation_id: str
    source_product_id: str
    source_fields: Mapping[str, Any]
    provenance: Provenance

    @field_validator("observation_id", "source_product_id")
    @classmethod
    def _require_safe_identity(cls, value: str) -> str:
        return _require_nonempty_safe_text(value, code="OBSERVATION_TEXT_INVALID")

    @field_validator("source_fields")
    @classmethod
    def _validate_source_fields(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _require_safe_mapping(value, code="OBSERVATION_SOURCE_FIELDS_INVALID")

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "source_fields", _deep_freeze(self.source_fields))

    @field_serializer("source_fields")
    def _serialize_source_fields(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _json_value(value)


class NormalizedProduct(ContractModel):
    """Small cross-source product projection; unknown values remain absent."""

    normalized_product_id: str
    observation_id: str
    name: str
    provenance: Provenance
    category: str | None = None
    price: str | None = None
    availability: bool | None = None
    brand: str | None = None
    supplier: str | None = None
    country: str | None = None
    attributes: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("normalized_product_id", "observation_id", "name")
    @classmethod
    def _require_safe_identity(cls, value: str) -> str:
        return _require_nonempty_safe_text(value, code="NORMALIZED_PRODUCT_TEXT_INVALID")

    @field_validator("category", "price", "brand", "supplier", "country")
    @classmethod
    def _validate_optional_text(cls, value: str | None) -> str | None:
        return None if value is None else _require_nonempty_safe_text(value, code="NORMALIZED_PRODUCT_TEXT_INVALID")

    @field_validator("attributes")
    @classmethod
    def _validate_attributes(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _require_safe_mapping(value, code="NORMALIZED_PRODUCT_ATTRIBUTES_INVALID")

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "attributes", _deep_freeze(self.attributes))

    @field_serializer("attributes")
    def _serialize_attributes(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _json_value(value)


class FieldDefinition(ContractModel):
    """One discovered product field; product categories never define global fields."""

    field_id: str
    display_label: str
    value_type: FieldValueType
    is_filterable: bool = False

    @field_validator("field_id", "display_label")
    @classmethod
    def _require_safe_identity(cls, value: str) -> str:
        return _require_nonempty_safe_text(value, code="FIELD_DEFINITION_TEXT_INVALID")


class CollectionResult(ContractModel):
    """The source-neutral result returned by `SourceAdapter.collect` at the application seam."""

    request: CollectionRequest
    terminal_outcome: TerminalOutcome
    observations: tuple[ProductObservation, ...] = ()
    normalized_products: tuple[NormalizedProduct, ...] = ()
    field_definitions: tuple[FieldDefinition, ...] = ()
    artifact_refs: Mapping[str, str] = Field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()

    @field_validator("artifact_refs")
    @classmethod
    def _validate_artifact_refs(cls, value: Mapping[str, str]) -> Mapping[str, str]:
        return _require_safe_artifact_mapping(value, code="COLLECTION_ARTIFACT_REFS_INVALID")

    @field_validator("diagnostics")
    @classmethod
    def _validate_diagnostics(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_require_nonempty_safe_text(item, code="COLLECTION_DIAGNOSTIC_INVALID") for item in value)

    @model_validator(mode="after")
    def _validate_result_provenance(self) -> "CollectionResult":
        source = self.request.source_profile
        selected_node_ids = {node.catalog_node_id for node in self.request.catalog_nodes}
        observations_by_id: dict[str, ProductObservation] = {}
        for observation in self.observations:
            self._validate_provenance(
                observation.provenance,
                source,
                self.request.collection_run_id,
                selected_node_ids,
            )
            if observation.observation_id in observations_by_id:
                raise ApplicationContractError(
                    "RESULT_OBSERVATION_DUPLICATE",
                    "RESULT_OBSERVATION_DUPLICATE: Observation IDs must be unique within a result.",
                )
            observations_by_id[observation.observation_id] = observation
        for product in self.normalized_products:
            self._validate_provenance(
                product.provenance,
                source,
                self.request.collection_run_id,
                selected_node_ids,
            )
            observation = observations_by_id.get(product.observation_id)
            if observation is None:
                raise ApplicationContractError(
                    "RESULT_PRODUCT_OBSERVATION_UNKNOWN",
                    "RESULT_PRODUCT_OBSERVATION_UNKNOWN: A normalized product must reference a returned observation.",
                )
            if product.provenance != observation.provenance:
                raise ApplicationContractError(
                    "RESULT_PRODUCT_PROVENANCE_MISMATCH",
                    "RESULT_PRODUCT_PROVENANCE_MISMATCH: A normalized product must retain its observation provenance.",
                )
        return self

    @staticmethod
    def _validate_provenance(
        provenance: Provenance,
        source: SourceProfile,
        collection_run_id: str,
        selected_node_ids: set[str],
    ) -> None:
        if provenance.source_profile_id != source.source_profile_id:
            raise ApplicationContractError(
                "RESULT_SOURCE_MISMATCH",
                "RESULT_SOURCE_MISMATCH: Product provenance belongs to another SourceProfile.",
            )
        if provenance.adapter_id != source.adapter_id or provenance.adapter_version != source.adapter_version:
            raise ApplicationContractError(
                "RESULT_ADAPTER_MISMATCH",
                "RESULT_ADAPTER_MISMATCH: Product provenance does not match the selected SourceProfile adapter.",
            )
        if provenance.collection_run_id != collection_run_id:
            raise ApplicationContractError(
                "RESULT_RUN_MISMATCH",
                "RESULT_RUN_MISMATCH: Product provenance does not match the collection run.",
            )
        if provenance.catalog_node_id not in selected_node_ids:
            raise ApplicationContractError(
                "RESULT_NODE_NOT_SELECTED",
                "RESULT_NODE_NOT_SELECTED: Product provenance must name an explicitly selected CatalogNode.",
            )

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "artifact_refs", _deep_freeze(self.artifact_refs))

    @field_serializer("artifact_refs")
    def _serialize_artifact_refs(self, value: Mapping[str, str]) -> dict[str, Any]:
        return _json_value(value)


@runtime_checkable
class SourceAdapter(Protocol):
    """A source-specific adapter behind the one generic application collection seam."""

    adapter_id: str
    adapter_version: str

    def collect(self, request: CollectionRequest) -> CollectionResult:
        """Collect only the request's explicitly selected source scope."""
        ...
