"""Deterministic source adapters behind the versioned application collection seam."""

from __future__ import annotations

from collections.abc import Iterable
import json
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit

from pydantic import ValidationError

from application.contracts import (
    ApplicationContractError,
    CatalogNode,
    CollectionRequest,
    CollectionResult,
    FieldDefinition,
    FieldValueType,
    NormalizedProduct,
    ProductObservation,
    Provenance,
    SourceAdapter,
    SourceKind,
    SourceProfile,
    TerminalOutcome,
)


class SourceAdapterRegistry:
    """Explicit adapter lookup; collection never falls back to an inferred source."""

    def __init__(self, adapters: Iterable[SourceAdapter]) -> None:
        by_id: dict[str, SourceAdapter] = {}
        for adapter in adapters:
            if adapter.adapter_id in by_id:
                raise ApplicationContractError(
                    "SOURCE_ADAPTER_DUPLICATE",
                    f"SOURCE_ADAPTER_DUPLICATE: Adapter ID is repeated: {adapter.adapter_id}.",
                )
            by_id[adapter.adapter_id] = adapter
        self._by_id = by_id

    def collect(self, request: CollectionRequest) -> CollectionResult:
        profile = request.source_profile
        adapter = self._by_id.get(profile.adapter_id)
        if adapter is None:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_UNAVAILABLE",
                f"SOURCE_ADAPTER_UNAVAILABLE: No selected adapter is registered: {profile.adapter_id}.",
            )
        if adapter.adapter_version != profile.adapter_version:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_VERSION_MISMATCH",
                "SOURCE_ADAPTER_VERSION_MISMATCH: The selected profile version does not match its adapter.",
            )
        return adapter.collect(request)


class SyntheticFixtureSourceAdapter:
    """One non-retailer fixture source for deterministic source-contract acceptance."""

    adapter_id = "synthetic-fixture-v1"
    adapter_version = "1"
    _SOURCE_LOCATOR = "fixture://example-catalog-v1"
    _OBSERVED_AT = "2026-08-10T00:00:00Z"
    _PRODUCTS_BY_NODE: Mapping[str, tuple[Mapping[str, Any], ...]] = {
        "example-notebooks": (
            {
                "observation_id": "example-notebook-observation-001",
                "source_product_id": "example-notebook-001",
                "normalized_product_id": "example-notebook-normalized-001",
                "name": "Example grid notebook",
                "source_fields": {"title": "Example grid notebook", "sheet_count": 80, "price": "4.50"},
                "price": "4.50",
                "attributes": {"sheet_count": 80},
            },
        ),
        "example-lamps": (
            {
                "observation_id": "example-lamp-observation-001",
                "source_product_id": "example-lamp-001",
                "normalized_product_id": "example-lamp-normalized-001",
                "name": "Example desk lamp",
                "source_fields": {"title": "Example desk lamp", "wattage": 8, "price": "18.00"},
                "price": "18.00",
                "attributes": {"wattage": 8},
            },
        ),
    }

    def collect(self, request: CollectionRequest) -> CollectionResult:
        profile = request.source_profile
        if profile.source_kind is not SourceKind.FIXTURE:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_KIND_MISMATCH",
                "SOURCE_ADAPTER_KIND_MISMATCH: The synthetic fixture adapter requires a fixture SourceProfile.",
            )
        if profile.source_locator != self._SOURCE_LOCATOR:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_LOCATOR_UNAVAILABLE",
                "SOURCE_ADAPTER_LOCATOR_UNAVAILABLE: The selected fixture locator is unavailable.",
            )

        selected_node_ids = tuple(node.catalog_node_id for node in request.catalog_nodes)
        unavailable = next((node_id for node_id in selected_node_ids if node_id not in self._PRODUCTS_BY_NODE), None)
        if unavailable is not None:
            raise ApplicationContractError(
                "SOURCE_CATALOG_NODE_UNAVAILABLE",
                f"SOURCE_CATALOG_NODE_UNAVAILABLE: The selected catalog node is unavailable: {unavailable}.",
            )

        observations: list[ProductObservation] = []
        normalized_products: list[NormalizedProduct] = []
        for node_id in selected_node_ids:
            for product in self._PRODUCTS_BY_NODE[node_id]:
                provenance = self._provenance(request, node_id, product["source_product_id"])
                observation = ProductObservation(
                    observation_id=str(product["observation_id"]),
                    source_product_id=str(product["source_product_id"]),
                    source_fields=dict(product["source_fields"]),
                    provenance=provenance,
                )
                observations.append(observation)
                normalized_products.append(
                    NormalizedProduct(
                        normalized_product_id=str(product["normalized_product_id"]),
                        observation_id=observation.observation_id,
                        name=str(product["name"]),
                        price=str(product["price"]),
                        provenance=provenance,
                        attributes=dict(product["attributes"]),
                    )
                )

        return CollectionResult(
            request=request,
            terminal_outcome=TerminalOutcome.READY,
            observations=tuple(observations),
            normalized_products=tuple(normalized_products),
            field_definitions=(
                FieldDefinition(field_id="price", display_label="Price", value_type=FieldValueType.TEXT, is_filterable=True),
            ),
            artifact_refs={"fixture": profile.source_locator},
        )

    def _provenance(self, request: CollectionRequest, catalog_node_id: str, source_product_id: Any) -> Provenance:
        profile = request.source_profile
        return Provenance(
            source_profile_id=profile.source_profile_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            collection_run_id=request.collection_run_id,
            catalog_node_id=catalog_node_id,
            observed_at=self._OBSERVED_AT,
            evidence_ref=f"{profile.source_locator}/products/{source_product_id}",
            transformation_status="normalized_without_inference",
        )


class LocalJsonFileSourceAdapter:
    """Import one explicit local JSON v1 catalog without schema inference or network access."""

    adapter_id = "local-json-file-v1"
    adapter_version = "1"
    _FORMAT = "parserriba-local-catalog-v1"
    _DOCUMENT_KEYS = frozenset({"format", "observed_at", "catalog_nodes", "products"})
    _CATALOG_NODE_REQUIRED_KEYS = frozenset({"catalog_node_id", "display_name"})
    _CATALOG_NODE_OPTIONAL_KEYS = frozenset({"parent_catalog_node_id"})
    _PRODUCT_REQUIRED_KEYS = frozenset(
        {"observation_id", "source_product_id", "normalized_product_id", "catalog_node_id", "name", "source_fields"}
    )
    _PRODUCT_OPTIONAL_KEYS = frozenset({"category", "price", "availability", "brand", "supplier", "country", "attributes"})

    def collect(self, request: CollectionRequest) -> CollectionResult:
        profile = request.source_profile
        self._require_file_profile(profile)
        document = self._validated_document(profile)
        declared_nodes = self._declared_nodes(profile, document["catalog_nodes"])
        declared_node_ids = frozenset(node.catalog_node_id for node in declared_nodes)
        selected_node_ids = tuple(node.catalog_node_id for node in request.catalog_nodes)
        unavailable = next((node_id for node_id in selected_node_ids if node_id not in declared_node_ids), None)
        if unavailable is not None:
            raise ApplicationContractError(
                "SOURCE_CATALOG_NODE_UNAVAILABLE",
                f"SOURCE_CATALOG_NODE_UNAVAILABLE: The selected catalog node is unavailable: {unavailable}.",
            )
        self._validate_observed_at(request, document["observed_at"])
        validated_products = self._validated_products(request, document["products"], declared_node_ids, document["observed_at"])
        observations = tuple(observation for node_id, observation, _ in validated_products if node_id in selected_node_ids)
        normalized_products = tuple(product for node_id, _, product in validated_products if node_id in selected_node_ids)

        return CollectionResult(
            request=request,
            terminal_outcome=TerminalOutcome.READY,
            observations=observations,
            normalized_products=normalized_products,
            artifact_refs={"input": profile.source_locator},
        )

    def catalog_nodes(self, profile: SourceProfile) -> tuple[CatalogNode, ...]:
        """Inspect one explicit file profile and return its fully validated catalog nodes."""
        self._require_file_profile(profile)
        document = self._validated_document(profile)
        nodes = self._declared_nodes(profile, document["catalog_nodes"])
        inspection_request = CollectionRequest(
            collection_run_id="local-file-catalog-inspection",
            source_profile=profile,
            catalog_nodes=nodes,
        )
        declared_node_ids = frozenset(node.catalog_node_id for node in nodes)
        self._validate_observed_at(inspection_request, document["observed_at"])
        self._validated_products(
            inspection_request,
            document["products"],
            declared_node_ids,
            document["observed_at"],
        )
        return nodes

    @staticmethod
    def _require_file_profile(profile: SourceProfile) -> None:
        if profile.source_kind is not SourceKind.FILE:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_KIND_MISMATCH",
                "SOURCE_ADAPTER_KIND_MISMATCH: The local JSON adapter requires a file SourceProfile.",
            )
        if (
            profile.adapter_id != LocalJsonFileSourceAdapter.adapter_id
            or profile.adapter_version != LocalJsonFileSourceAdapter.adapter_version
        ):
            raise ApplicationContractError(
                "SOURCE_ADAPTER_IDENTITY_MISMATCH",
                "SOURCE_ADAPTER_IDENTITY_MISMATCH: SourceProfile adapter identity does not match the local JSON adapter.",
            )

    def _validated_document(self, profile: SourceProfile) -> Mapping[str, Any]:
        document = self._read_document(profile.source_locator)
        if set(document) != self._DOCUMENT_KEYS:
            raise ApplicationContractError(
                "LOCAL_FILE_DOCUMENT_INVALID",
                "LOCAL_FILE_DOCUMENT_INVALID: The local JSON document has missing or unsupported fields.",
            )
        if not isinstance(document["catalog_nodes"], list) or not isinstance(document["products"], list):
            raise ApplicationContractError(
                "LOCAL_FILE_DOCUMENT_INVALID",
                "LOCAL_FILE_DOCUMENT_INVALID: catalog_nodes and products must be arrays.",
            )
        if document.get("format") != self._FORMAT:
            raise ApplicationContractError(
                "LOCAL_FILE_FORMAT_UNSUPPORTED",
                "LOCAL_FILE_FORMAT_UNSUPPORTED: The selected file is not parserriba-local-catalog-v1.",
            )
        return document

    @classmethod
    def _declared_nodes(
        cls,
        profile: SourceProfile,
        records: list[Any],
    ) -> tuple[CatalogNode, ...]:
        nodes: list[CatalogNode] = []
        node_ids: set[str] = set()
        for record in records:
            if not isinstance(record, Mapping):
                raise ApplicationContractError(
                    "LOCAL_FILE_CATALOG_NODE_INVALID",
                    "LOCAL_FILE_CATALOG_NODE_INVALID: Every catalog node record must be an object.",
                )
            keys = set(record)
            if not cls._CATALOG_NODE_REQUIRED_KEYS.issubset(keys) or not keys.issubset(
                cls._CATALOG_NODE_REQUIRED_KEYS | cls._CATALOG_NODE_OPTIONAL_KEYS
            ):
                raise ApplicationContractError(
                    "LOCAL_FILE_CATALOG_NODE_INVALID",
                    "LOCAL_FILE_CATALOG_NODE_INVALID: A catalog node has missing or unsupported fields.",
                )
            try:
                node = CatalogNode(
                    source_profile_id=profile.source_profile_id,
                    catalog_node_id=record["catalog_node_id"],
                    display_name=record["display_name"],
                    parent_catalog_node_id=record.get("parent_catalog_node_id"),
                )
            except (KeyError, TypeError, ValidationError) as error:
                raise ApplicationContractError(
                    "LOCAL_FILE_CATALOG_NODE_INVALID",
                    "LOCAL_FILE_CATALOG_NODE_INVALID: Catalog node identity and labels must be valid safe text.",
                ) from error
            if node.catalog_node_id in node_ids:
                raise ApplicationContractError(
                    "LOCAL_FILE_CATALOG_NODE_INVALID",
                    "LOCAL_FILE_CATALOG_NODE_INVALID: Catalog node IDs must be unique.",
                )
            node_ids.add(node.catalog_node_id)
            nodes.append(node)
        if not nodes:
            raise ApplicationContractError(
                "LOCAL_FILE_CATALOG_NODE_INVALID",
                "LOCAL_FILE_CATALOG_NODE_INVALID: The local catalog must declare at least one node.",
            )
        by_id = {node.catalog_node_id: node for node in nodes}
        for node in nodes:
            parent_id = node.parent_catalog_node_id
            if parent_id is not None and (parent_id not in by_id or parent_id == node.catalog_node_id):
                raise ApplicationContractError(
                    "LOCAL_FILE_CATALOG_NODE_INVALID",
                    "LOCAL_FILE_CATALOG_NODE_INVALID: Every parent must name another declared catalog node.",
                )
            trail: set[str] = set()
            current = node
            while current.parent_catalog_node_id is not None:
                if current.catalog_node_id in trail:
                    raise ApplicationContractError(
                        "LOCAL_FILE_CATALOG_NODE_INVALID",
                        "LOCAL_FILE_CATALOG_NODE_INVALID: Catalog node parent links must be acyclic.",
                    )
                trail.add(current.catalog_node_id)
                current = by_id[current.parent_catalog_node_id]
        return tuple(nodes)

    def _validate_observed_at(self, request: CollectionRequest, observed_at: Any) -> None:
        try:
            self._provenance(request, request.catalog_nodes[0].catalog_node_id, observed_at)
        except ValidationError as error:
            raise ApplicationContractError(
                "LOCAL_FILE_DOCUMENT_INVALID",
                "LOCAL_FILE_DOCUMENT_INVALID: observed_at must be a timezone-bearing ISO-8601 timestamp.",
            ) from error

    def _validated_products(
        self,
        request: CollectionRequest,
        records: list[Any],
        declared_node_ids: frozenset[str],
        observed_at: Any,
    ) -> tuple[tuple[str, ProductObservation, NormalizedProduct], ...]:
        validated: list[tuple[str, ProductObservation, NormalizedProduct]] = []
        for record in records:
            if not isinstance(record, Mapping):
                raise ApplicationContractError(
                    "LOCAL_FILE_PRODUCT_INVALID",
                    "LOCAL_FILE_PRODUCT_INVALID: Every imported product record must be an object.",
                )
            catalog_node_id = record.get("catalog_node_id")
            if not isinstance(catalog_node_id, str) or not catalog_node_id.strip():
                raise ApplicationContractError(
                    "LOCAL_FILE_PRODUCT_NODE_INVALID",
                    "LOCAL_FILE_PRODUCT_NODE_INVALID: Every imported product must name a catalog node.",
                )
            if catalog_node_id not in declared_node_ids:
                raise ApplicationContractError(
                    "LOCAL_FILE_PRODUCT_NODE_INVALID",
                    "LOCAL_FILE_PRODUCT_NODE_INVALID: Every imported product must name a declared catalog node.",
                )
            if not self._PRODUCT_REQUIRED_KEYS.issubset(record) or not set(record).issubset(
                self._PRODUCT_REQUIRED_KEYS | self._PRODUCT_OPTIONAL_KEYS
            ):
                raise ApplicationContractError(
                    "LOCAL_FILE_PRODUCT_INVALID",
                    "LOCAL_FILE_PRODUCT_INVALID: An imported product record has missing or unsupported fields.",
                )
            try:
                provenance = self._provenance(request, catalog_node_id, observed_at)
                observation = ProductObservation(
                    observation_id=record["observation_id"],
                    source_product_id=record["source_product_id"],
                    source_fields=record["source_fields"],
                    provenance=provenance,
                )
                product = NormalizedProduct(
                    normalized_product_id=record["normalized_product_id"],
                    observation_id=observation.observation_id,
                    name=record["name"],
                    provenance=provenance,
                    category=record.get("category"),
                    price=record.get("price"),
                    availability=record.get("availability"),
                    brand=record.get("brand"),
                    supplier=record.get("supplier"),
                    country=record.get("country"),
                    attributes=record.get("attributes", {}),
                )
            except (KeyError, TypeError, ValidationError) as error:
                raise ApplicationContractError(
                    "LOCAL_FILE_PRODUCT_INVALID",
                    "LOCAL_FILE_PRODUCT_INVALID: An imported product record does not match local JSON v1.",
                ) from error
            validated.append((catalog_node_id, observation, product))
        return tuple(validated)

    def _provenance(self, request: CollectionRequest, catalog_node_id: str, observed_at: Any) -> Provenance:
        profile = request.source_profile
        return Provenance(
            source_profile_id=profile.source_profile_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            collection_run_id=request.collection_run_id,
            catalog_node_id=catalog_node_id,
            observed_at=observed_at,
            evidence_ref=profile.source_locator,
            transformation_status="imported_without_inference",
        )

    @staticmethod
    def _read_document(source_locator: str) -> Mapping[str, Any]:
        parsed = urlsplit(source_locator)
        source_path = Path(unquote(parsed.path))
        canonical = source_path.as_uri() if source_path.is_absolute() else ""
        if (
            not source_locator.startswith("file:///")
            or parsed.scheme != "file"
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or not source_path.is_absolute()
            or source_locator != canonical
        ):
            raise ApplicationContractError(
                "LOCAL_FILE_LOCATOR_INVALID",
                "LOCAL_FILE_LOCATOR_INVALID: A local JSON source must use a canonical hostless absolute file URI.",
            )
        if source_path.suffix.lower() != ".json" or not source_path.is_file():
            raise ApplicationContractError(
                "LOCAL_FILE_UNAVAILABLE",
                "LOCAL_FILE_UNAVAILABLE: The selected local JSON file is unavailable.",
            )
        try:
            document = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ApplicationContractError(
                "LOCAL_FILE_READ_FAILED",
                "LOCAL_FILE_READ_FAILED: The selected local JSON file cannot be read.",
            ) from error
        if not isinstance(document, Mapping):
            raise ApplicationContractError(
                "LOCAL_FILE_DOCUMENT_INVALID",
                "LOCAL_FILE_DOCUMENT_INVALID: The local JSON document must be an object.",
            )
        return document
