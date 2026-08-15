"""Dependency-light async browser evidence adapter for source-neutral collection."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from application.contracts import (
    ApplicationContractError,
    CollectionRequest,
    CollectionResult,
    NormalizedProduct,
    ProductObservation,
    Provenance,
    SourceKind,
    TerminalOutcome,
    is_restricted_data_key,
)
from application.url_safety import (
    contains_restricted_artifact_reference,
    contains_sensitive_url_material,
)


class BrowserCollectionRunner(Protocol):
    """Internal port implemented by production browser and offline test runners."""

    async def collect(self, request: CollectionRequest) -> Mapping[str, Any]:
        """Return serializable, source-scoped browser evidence."""
        ...


class _BrowserProductEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    observation_id: str
    source_product_id: str
    normalized_product_id: str
    catalog_node_id: str
    observed_at: str
    evidence_ref: str
    name: str
    source_fields: dict[str, Any]
    category: str | None = None
    price: str | None = None
    availability: bool | None = None
    brand: str | None = None
    supplier: str | None = None
    country: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class _BrowserEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    format: Literal["parserriba-browser-evidence-v1"]
    terminal_outcome: Literal[
        "ready",
        "manual_action_required",
        "blocked",
        "partial",
        "failed",
        "cancelled",
    ]
    products: tuple[_BrowserProductEvidence, ...] = ()
    artifact_refs: dict[str, str] = Field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()


_SAFE_DIAGNOSTIC_CODE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")


def _assert_safe_browser_value(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if is_restricted_data_key(key):
                raise ApplicationContractError(
                    "BROWSER_EVIDENCE_UNSAFE",
                    "BROWSER_EVIDENCE_UNSAFE: Browser evidence contains operational or sensitive data.",
                )
            _assert_safe_browser_value(nested)
        return
    if isinstance(value, (list, tuple)):
        for nested in value:
            _assert_safe_browser_value(nested)
        return
    if isinstance(value, str):
        if contains_sensitive_url_material(value):
            raise ApplicationContractError(
                "BROWSER_EVIDENCE_UNSAFE",
                "BROWSER_EVIDENCE_UNSAFE: Browser evidence contains sensitive or ambiguously encoded URL data.",
            )


def _assert_safe_artifact_ref(value: str) -> None:
    if contains_restricted_artifact_reference(value):
        raise ApplicationContractError(
            "BROWSER_EVIDENCE_UNSAFE",
            "BROWSER_EVIDENCE_UNSAFE: Browser artifact reference contains operational or sensitive data.",
        )
    try:
        parsed = urlsplit(value)
        parsed.port
    except ValueError as error:
        raise ApplicationContractError(
            "BROWSER_EVIDENCE_UNSAFE",
            "BROWSER_EVIDENCE_UNSAFE: Browser artifact reference is not safely parseable.",
        ) from error
    valid_file = parsed.scheme == "file" and not parsed.netloc and parsed.path.startswith("/")
    valid_https = parsed.scheme == "https" and bool(parsed.hostname)
    if (
        not (valid_file or valid_https)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ApplicationContractError(
            "BROWSER_EVIDENCE_UNSAFE",
            "BROWSER_EVIDENCE_UNSAFE: Browser artifact reference contains operational or sensitive data.",
        )


class BrowserSourceAdapter:
    """Map one injected browser run to the source-neutral application contracts."""

    adapter_id = "browser-evidence-v1"
    adapter_version = "1"
    _ALLOWED_ARTIFACT_KEYS = frozenset({"rendered_html", "screenshot", "serialized_result"})

    def __init__(self, runner: BrowserCollectionRunner) -> None:
        self._runner = runner

    async def collect(self, request: CollectionRequest) -> CollectionResult:
        """Collect only the explicit browser source scope and preserve provenance."""
        profile = request.source_profile
        if profile.source_kind is not SourceKind.BROWSER:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_KIND_MISMATCH",
                "SOURCE_ADAPTER_KIND_MISMATCH: The browser adapter requires a browser SourceProfile.",
            )
        if profile.adapter_id != self.adapter_id or profile.adapter_version != self.adapter_version:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_VERSION_MISMATCH",
                "SOURCE_ADAPTER_VERSION_MISMATCH: The selected profile does not match the browser adapter.",
            )

        try:
            evidence = _BrowserEvidence.model_validate(await self._runner.collect(request))
        except (TypeError, ValidationError):
            raise ApplicationContractError(
                "BROWSER_EVIDENCE_INVALID",
                "BROWSER_EVIDENCE_INVALID: Browser evidence does not match the supported format.",
            ) from None

        unsupported_artifact_key = next(
            (key for key in evidence.artifact_refs if key not in self._ALLOWED_ARTIFACT_KEYS),
            None,
        )
        if unsupported_artifact_key is not None:
            raise ApplicationContractError(
                "BROWSER_EVIDENCE_ARTIFACT_KEY_INVALID",
                "BROWSER_EVIDENCE_ARTIFACT_KEY_INVALID: Browser evidence contains an unsupported artifact reference.",
            )
        for artifact_ref in evidence.artifact_refs.values():
            _assert_safe_artifact_ref(artifact_ref)
        for item in evidence.products:
            _assert_safe_browser_value(item.evidence_ref)
            _assert_safe_browser_value(item.source_fields)
            _assert_safe_browser_value(item.attributes)
        if any(not _SAFE_DIAGNOSTIC_CODE.fullmatch(item) for item in evidence.diagnostics):
            raise ApplicationContractError(
                "BROWSER_EVIDENCE_UNSAFE",
                "BROWSER_EVIDENCE_UNSAFE: Browser diagnostics must contain safe machine reason codes only.",
            )
        if evidence.terminal_outcome != TerminalOutcome.READY.value and evidence.products:
            raise ApplicationContractError(
                "BROWSER_EVIDENCE_NON_READY_PRODUCTS",
                "BROWSER_EVIDENCE_NON_READY_PRODUCTS: Non-ready browser evidence cannot publish products.",
            )

        observations: list[ProductObservation] = []
        normalized_products: list[NormalizedProduct] = []
        for item in evidence.products:
            provenance = Provenance(
                source_profile_id=profile.source_profile_id,
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                collection_run_id=request.collection_run_id,
                catalog_node_id=item.catalog_node_id,
                observed_at=item.observed_at,
                evidence_ref=item.evidence_ref,
                transformation_status="browser_evidence_without_inference",
            )
            observation = ProductObservation(
                observation_id=item.observation_id,
                source_product_id=item.source_product_id,
                source_fields=item.source_fields,
                provenance=provenance,
            )
            observations.append(observation)
            normalized_products.append(
                NormalizedProduct(
                    normalized_product_id=item.normalized_product_id,
                    observation_id=observation.observation_id,
                    name=item.name,
                    provenance=provenance,
                    category=item.category,
                    price=item.price,
                    availability=item.availability,
                    brand=item.brand,
                    supplier=item.supplier,
                    country=item.country,
                    attributes=item.attributes,
                )
            )

        return CollectionResult(
            request=request,
            terminal_outcome=TerminalOutcome(evidence.terminal_outcome),
            observations=tuple(observations),
            normalized_products=tuple(normalized_products),
            artifact_refs=evidence.artifact_refs,
            diagnostics=evidence.diagnostics,
        )
