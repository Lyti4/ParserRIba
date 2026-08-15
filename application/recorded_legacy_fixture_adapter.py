"""Deterministic recorded legacy evidence behind the source-neutral adapter seam.

This module is fixture-only. It intentionally has no browser, network, proxy,
launcher, challenge, or legacy-parser imports.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import math
import re
from typing import Any

from pydantic import ValidationError

from application.contracts import (
    ApplicationContractError,
    CollectionRequest,
    CollectionResult,
    NormalizedProduct,
    ProductObservation,
    Provenance,
    SourceKind,
    TerminalOutcome,
)


def recorded_legacy_fixture_document() -> dict[str, Any]:
    """Return a fresh, fixed, non-secret fixture document for explicit local demos."""
    locator = RecordedLegacyFixtureSourceAdapter.source_locator
    return {
        "format": "parserriba-recorded-legacy-fixture-v1",
        "observed_at": "2026-08-13T00:00:00Z",
        "catalog_nodes": [
            {"catalog_node_id": "recorded-dom-example", "display_name": "Recorded DOM example"},
            {"catalog_node_id": "recorded-api-example", "display_name": "Recorded API example"},
        ],
        "records": [
            {
                "shape": "dom-v1",
                "catalog_node_id": "recorded-dom-example",
                "source_product_id": "recorded-dom-example-001",
                "evidence_ref": f"{locator}/evidence/recorded-dom-example-001",
                "fields": {"name": "Recorded DOM example", "price": "100.00", "availability": True},
            },
            {
                "shape": "api-v1",
                "catalog_node_id": "recorded-api-example",
                "evidence_ref": f"{locator}/evidence/recorded-api-example-001",
                "payload": {
                    "plu": "recorded-api-example-001",
                    "name": "Recorded API example",
                    "prices": {"current": "200.00"},
                },
            },
        ],
        "terminal": {"outcome": "ready", "reason": "recorded_fixture_ready"},
    }


class RecordedLegacyFixtureSourceAdapter:
    """Normalize strict recorded DOM/API evidence for an explicit fixture profile."""

    adapter_id = "recorded-legacy-fixture-v1"
    adapter_version = "1"
    source_locator = "fixture://recorded-legacy-products-v1"

    _FORMAT = "parserriba-recorded-legacy-fixture-v1"
    _DOCUMENT_KEYS = frozenset({"format", "observed_at", "catalog_nodes", "records", "terminal"})
    _NODE_KEYS = frozenset({"catalog_node_id", "display_name"})
    _TERMINAL_KEYS = frozenset({"outcome", "reason"})
    _DOM_RECORD_KEYS = frozenset(
        {"shape", "catalog_node_id", "source_product_id", "evidence_ref", "fields"}
    )
    _DOM_FIELDS = frozenset(
        {"name", "category", "price", "availability", "brand", "supplier", "country"}
    )
    _API_RECORD_KEYS = frozenset({"shape", "catalog_node_id", "evidence_ref", "payload"})
    _API_FIELDS = frozenset(
        {"plu", "name", "prices", "is_available", "brand", "category", "supplier", "country"}
    )
    _API_PRICE_FIELDS = ("regular", "current", "price")
    _SAFE_REASON_CODE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
    _READY_OUTCOMES = frozenset(
        {
            TerminalOutcome.READY,
            TerminalOutcome.BLOCKED,
            TerminalOutcome.MANUAL_ACTION_REQUIRED,
        }
    )

    def __init__(self, document: Mapping[str, Any]) -> None:
        self._document = document

    def collect(self, request: CollectionRequest) -> CollectionResult:
        profile = request.source_profile
        if profile.source_kind is not SourceKind.FIXTURE:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_KIND_MISMATCH",
                "SOURCE_ADAPTER_KIND_MISMATCH: The recorded adapter requires a fixture SourceProfile.",
            )
        if profile.source_locator != self.source_locator:
            raise ApplicationContractError(
                "SOURCE_ADAPTER_LOCATOR_UNAVAILABLE",
                "SOURCE_ADAPTER_LOCATOR_UNAVAILABLE: The selected recorded fixture locator is unavailable.",
            )

        document = self._document
        if not isinstance(document, Mapping) or set(document) != self._DOCUMENT_KEYS:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_DOCUMENT_INVALID",
                "RECORDED_FIXTURE_DOCUMENT_INVALID: The document has missing or unsupported fields.",
            )
        if document.get("format") != self._FORMAT:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_FORMAT_UNSUPPORTED",
                "RECORDED_FIXTURE_FORMAT_UNSUPPORTED: The document format is unsupported.",
            )

        observed_at = self._observed_at(document.get("observed_at"))
        declared_node_ids = self._declared_node_ids(document.get("catalog_nodes"))
        selected_node_ids = tuple(node.catalog_node_id for node in request.catalog_nodes)
        unavailable = next((node_id for node_id in selected_node_ids if node_id not in declared_node_ids), None)
        if unavailable is not None:
            raise ApplicationContractError(
                "SOURCE_CATALOG_NODE_UNAVAILABLE",
                f"SOURCE_CATALOG_NODE_UNAVAILABLE: The selected catalog node is unavailable: {unavailable}.",
            )

        terminal_outcome, reason = self._terminal(document.get("terminal"))
        records = document.get("records")
        if not isinstance(records, list):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_RECORD_INVALID",
                "RECORDED_FIXTURE_RECORD_INVALID: records must be an array.",
            )
        if terminal_outcome is not TerminalOutcome.READY:
            if records:
                raise ApplicationContractError(
                    "RECORDED_FIXTURE_TERMINAL_INVALID",
                    "RECORDED_FIXTURE_TERMINAL_INVALID: Blocked/manual fixtures must not contain product records.",
                )
            return CollectionResult(
                request=request,
                terminal_outcome=terminal_outcome,
                artifact_refs={"fixture": profile.source_locator},
                diagnostics=(reason,),
            )

        validated: list[tuple[str, str, ProductObservation, NormalizedProduct]] = []
        seen_source_product_ids: set[str] = set()
        for record in records:
            item = self._validate_record(
                request,
                record,
                declared_node_ids,
                observed_at,
            )
            source_product_id = item[1]
            if source_product_id in seen_source_product_ids:
                raise ApplicationContractError(
                    "RECORDED_FIXTURE_PRODUCT_DUPLICATE",
                    "RECORDED_FIXTURE_PRODUCT_DUPLICATE: Source product identity is repeated.",
                )
            seen_source_product_ids.add(source_product_id)
            validated.append(item)

        observations = tuple(item[2] for item in validated if item[0] in selected_node_ids)
        products = tuple(item[3] for item in validated if item[0] in selected_node_ids)
        return CollectionResult(
            request=request,
            terminal_outcome=terminal_outcome,
            observations=observations,
            normalized_products=products,
            artifact_refs={"fixture": profile.source_locator},
            diagnostics=(reason,),
        )

    @classmethod
    def _declared_node_ids(cls, records: Any) -> frozenset[str]:
        if not isinstance(records, list):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_CATALOG_NODE_INVALID",
                "RECORDED_FIXTURE_CATALOG_NODE_INVALID: catalog_nodes must be an array.",
            )
        node_ids: set[str] = set()
        for record in records:
            if not isinstance(record, Mapping) or set(record) != cls._NODE_KEYS:
                raise ApplicationContractError(
                    "RECORDED_FIXTURE_CATALOG_NODE_INVALID",
                    "RECORDED_FIXTURE_CATALOG_NODE_INVALID: Catalog node fields are invalid.",
                )
            node_id = record.get("catalog_node_id")
            display_name = record.get("display_name")
            if (
                not isinstance(node_id, str)
                or not node_id.strip()
                or node_id in node_ids
                or not isinstance(display_name, str)
                or not display_name.strip()
            ):
                raise ApplicationContractError(
                    "RECORDED_FIXTURE_CATALOG_NODE_INVALID",
                    "RECORDED_FIXTURE_CATALOG_NODE_INVALID: Catalog nodes require unique non-empty IDs and names.",
                )
            node_ids.add(node_id)
        return frozenset(node_ids)

    @staticmethod
    def _observed_at(value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ApplicationContractError(
                "RECORDED_FIXTURE_DOCUMENT_INVALID",
                "RECORDED_FIXTURE_DOCUMENT_INVALID: observed_at must be a timezone-bearing ISO-8601 timestamp.",
            )
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_DOCUMENT_INVALID",
                "RECORDED_FIXTURE_DOCUMENT_INVALID: observed_at must be a timezone-bearing ISO-8601 timestamp.",
            ) from error
        if parsed.tzinfo is None:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_DOCUMENT_INVALID",
                "RECORDED_FIXTURE_DOCUMENT_INVALID: observed_at must be a timezone-bearing ISO-8601 timestamp.",
            )
        return value

    @classmethod
    def _terminal(cls, value: Any) -> tuple[TerminalOutcome, str]:
        if not isinstance(value, Mapping) or set(value) != cls._TERMINAL_KEYS:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_TERMINAL_INVALID",
                "RECORDED_FIXTURE_TERMINAL_INVALID: Terminal metadata is invalid.",
            )
        raw_outcome = value.get("outcome")
        reason = value.get("reason")
        try:
            outcome = TerminalOutcome(raw_outcome)
        except (TypeError, ValueError) as error:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_TERMINAL_INVALID",
                "RECORDED_FIXTURE_TERMINAL_INVALID: Terminal outcome is unsupported.",
            ) from error
        if (
            outcome not in cls._READY_OUTCOMES
            or not isinstance(reason, str)
            or cls._SAFE_REASON_CODE.fullmatch(reason) is None
        ):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_TERMINAL_INVALID",
                "RECORDED_FIXTURE_TERMINAL_INVALID: Terminal outcome is unsupported or reason is not a safe code.",
            )
        return outcome, reason

    def _validate_record(
        self,
        request: CollectionRequest,
        record: Any,
        declared_node_ids: frozenset[str],
        observed_at: Any,
    ) -> tuple[str, str, ProductObservation, NormalizedProduct]:
        if not isinstance(record, Mapping):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_RECORD_INVALID",
                "RECORDED_FIXTURE_RECORD_INVALID: Every recorded product must be an object.",
            )
        shape = record.get("shape")
        if shape == "dom-v1":
            return self._validate_dom_record(request, record, declared_node_ids, observed_at)
        if shape == "api-v1":
            return self._validate_api_record(request, record, declared_node_ids, observed_at)
        raise ApplicationContractError(
            "RECORDED_FIXTURE_SHAPE_UNSUPPORTED",
            "RECORDED_FIXTURE_SHAPE_UNSUPPORTED: The record shape is unsupported.",
        )

    def _validate_dom_record(
        self,
        request: CollectionRequest,
        record: Mapping[str, Any],
        declared_node_ids: frozenset[str],
        observed_at: Any,
    ) -> tuple[str, str, ProductObservation, NormalizedProduct]:
        if set(record) != self._DOM_RECORD_KEYS:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_RECORD_INVALID",
                "RECORDED_FIXTURE_RECORD_INVALID: A DOM record has missing or unsupported fields.",
            )
        node_id = self._node_id(record.get("catalog_node_id"), declared_node_ids)
        source_product_id = self._source_product_id(record.get("source_product_id"))
        evidence_ref = self._evidence_ref(record.get("evidence_ref"))
        fields = record.get("fields")
        if not isinstance(fields, Mapping) or set(fields) - self._DOM_FIELDS or "name" not in fields:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: DOM fields are missing or unsupported.",
            )
        self._require_text(fields.get("name"))
        for field_name in ("category", "price", "brand", "supplier", "country"):
            if field_name in fields:
                self._require_text(fields[field_name])
        if "availability" in fields and type(fields["availability"]) is not bool:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: DOM availability must be a boolean.",
            )
        return self._build_product(
            request=request,
            node_id=node_id,
            source_product_id=source_product_id,
            evidence_ref=evidence_ref,
            observed_at=observed_at,
            source_fields=fields,
            name=fields["name"],
            category=fields.get("category"),
            price=fields.get("price"),
            availability=fields.get("availability"),
            brand=fields.get("brand"),
            supplier=fields.get("supplier"),
            country=fields.get("country"),
            shape="dom-v1",
        )

    def _validate_api_record(
        self,
        request: CollectionRequest,
        record: Mapping[str, Any],
        declared_node_ids: frozenset[str],
        observed_at: Any,
    ) -> tuple[str, str, ProductObservation, NormalizedProduct]:
        if set(record) != self._API_RECORD_KEYS:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_RECORD_INVALID",
                "RECORDED_FIXTURE_RECORD_INVALID: An API record has missing or unsupported fields.",
            )
        node_id = self._node_id(record.get("catalog_node_id"), declared_node_ids)
        evidence_ref = self._evidence_ref(record.get("evidence_ref"))
        payload = record.get("payload")
        if (
            not isinstance(payload, Mapping)
            or set(payload) - self._API_FIELDS
            or not {"plu", "name", "prices"}.issubset(payload)
        ):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: API payload fields are missing or unsupported.",
            )
        source_product_id = self._source_product_id(payload.get("plu"))
        name = self._require_text(payload.get("name"))
        price = self._api_price(payload.get("prices"))
        availability = payload.get("is_available")
        if "is_available" in payload and type(availability) is not bool:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: API availability must be a boolean.",
            )
        brand = self._api_brand(payload.get("brand")) if "brand" in payload else None
        for field_name in ("category", "supplier", "country"):
            if field_name in payload:
                self._require_text(payload[field_name])
        return self._build_product(
            request=request,
            node_id=node_id,
            source_product_id=source_product_id,
            evidence_ref=evidence_ref,
            observed_at=observed_at,
            source_fields=payload,
            name=name,
            category=payload.get("category"),
            price=price,
            availability=availability,
            brand=brand,
            supplier=payload.get("supplier"),
            country=payload.get("country"),
            shape="api-v1",
        )

    def _build_product(
        self,
        *,
        request: CollectionRequest,
        node_id: str,
        source_product_id: str,
        evidence_ref: str,
        observed_at: Any,
        source_fields: Mapping[str, Any],
        name: str,
        category: Any,
        price: Any,
        availability: Any,
        brand: Any,
        supplier: Any,
        country: Any,
        shape: str,
    ) -> tuple[str, str, ProductObservation, NormalizedProduct]:
        try:
            provenance = Provenance(
                source_profile_id=request.source_profile.source_profile_id,
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                collection_run_id=request.collection_run_id,
                catalog_node_id=node_id,
                observed_at=observed_at,
                evidence_ref=evidence_ref,
                transformation_status=f"recorded_{shape.removesuffix('-v1')}_normalized_without_inference",
            )
            observation = ProductObservation(
                observation_id=f"recorded-observation-{source_product_id}",
                source_product_id=source_product_id,
                source_fields=source_fields,
                provenance=provenance,
            )
            product = NormalizedProduct(
                normalized_product_id=f"recorded-product-{source_product_id}",
                observation_id=observation.observation_id,
                name=name,
                category=category,
                price=price,
                availability=availability,
                brand=brand,
                supplier=supplier,
                country=country,
                attributes={"record_shape": shape},
                provenance=provenance,
            )
        except (TypeError, ValidationError, ApplicationContractError) as error:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: A recorded product violates its safe versioned shape.",
            ) from error
        return node_id, source_product_id, observation, product

    @staticmethod
    def _node_id(value: Any, declared_node_ids: frozenset[str]) -> str:
        if not isinstance(value, str) or value not in declared_node_ids:
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_NODE_INVALID",
                "RECORDED_FIXTURE_PRODUCT_NODE_INVALID: Every record must name a declared node.",
            )
        return value

    @staticmethod
    def _source_product_id(value: Any) -> str:
        if isinstance(value, int) and not isinstance(value, bool):
            value = str(value)
        if not isinstance(value, str) or not value.strip():
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: Every record requires a source product ID.",
            )
        return value.strip()

    @classmethod
    def _evidence_ref(cls, value: Any) -> str:
        prefix = f"{cls.source_locator}/evidence/"
        if not isinstance(value, str) or not value.startswith(prefix) or len(value) == len(prefix):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: Evidence must use the recorded fixture namespace.",
            )
        return value

    @staticmethod
    def _require_text(value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: Recorded text fields must be non-empty strings.",
            )
        return value

    @classmethod
    def _api_price(cls, value: Any) -> str:
        if not isinstance(value, Mapping) or not value or set(value) - set(cls._API_PRICE_FIELDS):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: API prices must use the recorded v1 price fields.",
            )
        raw = next((value[key] for key in cls._API_PRICE_FIELDS if value.get(key) is not None), None)
        if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: API price must be finite text or a number.",
            )
        if isinstance(raw, float) and not math.isfinite(raw):
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: API price must be finite text or a number.",
            )
        price = str(raw)
        if not price.strip():
            raise ApplicationContractError(
                "RECORDED_FIXTURE_PRODUCT_INVALID",
                "RECORDED_FIXTURE_PRODUCT_INVALID: API price must not be empty.",
            )
        return price

    @classmethod
    def _api_brand(cls, value: Any) -> str:
        if isinstance(value, str):
            return cls._require_text(value)
        if isinstance(value, Mapping) and set(value) == {"name"}:
            return cls._require_text(value.get("name"))
        raise ApplicationContractError(
            "RECORDED_FIXTURE_PRODUCT_INVALID",
            "RECORDED_FIXTURE_PRODUCT_INVALID: API brand must be text or a name object.",
        )
