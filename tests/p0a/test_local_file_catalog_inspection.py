from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.contracts import ApplicationContractError, SourceKind, SourceProfile
from application.source_adapters import LocalJsonFileSourceAdapter
from application.source_profile_catalog import inspect_declared_source_catalog


class LocalFileCatalogInspectionTests(unittest.TestCase):
    def test_direct_adapter_rejects_mismatched_adapter_identity(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "catalog.json"
            source_path.write_text(
                json.dumps(
                    _catalog_document(
                        catalog_nodes=[{"catalog_node_id": "home", "display_name": "Home"}],
                        products=[],
                    )
                ),
                encoding="utf-8",
            )
            cases = (
                ("other-file-adapter", LocalJsonFileSourceAdapter.adapter_version),
                (LocalJsonFileSourceAdapter.adapter_id, "999"),
            )
            for adapter_id, adapter_version in cases:
                with self.subTest(adapter_id=adapter_id, adapter_version=adapter_version):
                    profile = SourceProfile(
                        source_profile_id="local-json-file",
                        display_name="Local JSON",
                        source_kind=SourceKind.FILE,
                        source_locator=source_path.as_uri(),
                        adapter_id=adapter_id,
                        adapter_version=adapter_version,
                    )

                    with self.assertRaises(ApplicationContractError) as error:
                        LocalJsonFileSourceAdapter().catalog_nodes(profile)

                    self.assertEqual(error.exception.code, "SOURCE_ADAPTER_IDENTITY_MISMATCH")

    def test_direct_adapter_rejects_noncanonical_file_uri_query_or_fragment(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "catalog.json"
            source_path.write_text(
                json.dumps(
                    _catalog_document(
                        catalog_nodes=[{"catalog_node_id": "home", "display_name": "Home"}],
                        products=[],
                    )
                ),
                encoding="utf-8",
            )
            for suffix in ("?revision=1", "#catalog"):
                with self.subTest(suffix=suffix):
                    profile = SourceProfile(
                        source_profile_id="local-json-file",
                        display_name="Local JSON",
                        source_kind=SourceKind.FILE,
                        source_locator=f"{source_path.as_uri()}{suffix}",
                        adapter_id=LocalJsonFileSourceAdapter.adapter_id,
                        adapter_version=LocalJsonFileSourceAdapter.adapter_version,
                    )

                    with self.assertRaises(ApplicationContractError) as error:
                        LocalJsonFileSourceAdapter().catalog_nodes(profile)

                    self.assertEqual(error.exception.code, "LOCAL_FILE_LOCATOR_INVALID")

    def test_inspection_returns_parent_linked_nodes_after_validating_the_complete_document(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "catalog.json"
            source_path.write_text(
                json.dumps(
                    _catalog_document(
                        catalog_nodes=[
                            {"catalog_node_id": "home", "display_name": "Home"},
                            {
                                "catalog_node_id": "lighting",
                                "display_name": "Lighting",
                                "parent_catalog_node_id": "home",
                            },
                        ],
                        products=[_product("lamp-001", "lighting")],
                    )
                ),
                encoding="utf-8",
            )

            inspected = inspect_declared_source_catalog("local-json-file", source_path.as_uri())

        self.assertEqual(inspected.source_profile.source_locator, source_path.as_uri())
        self.assertEqual(
            [
                (
                    node.catalog_node_id,
                    node.display_name,
                    node.parent_catalog_node_id,
                )
                for node in inspected.catalog_nodes
            ],
            [("home", "Home", None), ("lighting", "Lighting", "home")],
        )

    def test_collection_request_preserves_inspected_label_and_parent_link(self) -> None:
        from utils.source_adapter_tasks import build_source_adapter_collection_request

        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "catalog.json"
            source_path.write_text(
                json.dumps(
                    _catalog_document(
                        catalog_nodes=[
                            {"catalog_node_id": "home", "display_name": "Home"},
                            {
                                "catalog_node_id": "lighting",
                                "display_name": "Lighting",
                                "parent_catalog_node_id": "home",
                            },
                        ],
                        products=[_product("lamp-001", "lighting")],
                    )
                ),
                encoding="utf-8",
            )

            request = build_source_adapter_collection_request(
                {
                    "collection_run_id": "tree-selection-run",
                    "source_profile_id": "local-json-file",
                    "source_locator": source_path.as_uri(),
                    "catalog_node_ids": ["lighting"],
                }
            )

        self.assertEqual(len(request.catalog_nodes), 1)
        self.assertEqual(request.catalog_nodes[0].display_name, "Lighting")
        self.assertEqual(request.catalog_nodes[0].parent_catalog_node_id, "home")

    def test_inspection_rejects_malformed_missing_self_or_cyclic_nodes(self) -> None:
        cases: tuple[list[dict[str, object]], ...] = (
            [{"catalog_node_id": "missing-display-name"}],
            [{"catalog_node_id": "wrong-display-type", "display_name": 123}],
            [
                {
                    "catalog_node_id": "unexpected-field",
                    "display_name": "Unexpected",
                    "source_url": "file:///must-not-be-accepted",
                }
            ],
            [
                {
                    "catalog_node_id": "lighting",
                    "display_name": "Lighting",
                    "parent_catalog_node_id": "missing",
                }
            ],
            [
                {
                    "catalog_node_id": "self-parent",
                    "display_name": "Self parent",
                    "parent_catalog_node_id": "self-parent",
                }
            ],
            [
                {
                    "catalog_node_id": "home",
                    "display_name": "Home",
                    "parent_catalog_node_id": "lighting",
                },
                {
                    "catalog_node_id": "lighting",
                    "display_name": "Lighting",
                    "parent_catalog_node_id": "home",
                },
            ],
        )
        for catalog_nodes in cases:
            with self.subTest(catalog_nodes=catalog_nodes), TemporaryDirectory() as directory:
                source_path = Path(directory) / "invalid-tree.json"
                source_path.write_text(
                    json.dumps(_catalog_document(catalog_nodes=catalog_nodes, products=[])),
                    encoding="utf-8",
                )

                with self.assertRaises(ApplicationContractError) as error:
                    inspect_declared_source_catalog("local-json-file", source_path.as_uri())

                self.assertEqual(error.exception.code, "LOCAL_FILE_CATALOG_NODE_INVALID")

    def test_inspection_rejects_missing_or_malformed_document_boundaries(self) -> None:
        cases: tuple[dict[str, object], ...] = (
            {
                "format": "parserriba-local-catalog-v1",
                "observed_at": "2026-08-15T00:00:00Z",
                "catalog_nodes": [],
            },
            {
                "format": "parserriba-local-catalog-v1",
                "observed_at": "2026-08-15T00:00:00Z",
                "catalog_nodes": {},
                "products": [],
            },
        )
        for document in cases:
            with self.subTest(document=document), TemporaryDirectory() as directory:
                source_path = Path(directory) / "invalid-document.json"
                source_path.write_text(json.dumps(document), encoding="utf-8")

                with self.assertRaises(ApplicationContractError) as error:
                    inspect_declared_source_catalog("local-json-file", source_path.as_uri())

                self.assertEqual(error.exception.code, "LOCAL_FILE_DOCUMENT_INVALID")

    def test_inspection_validates_products_before_exposing_catalog_nodes(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "unsafe-product.json"
            unsafe_product = _product("lamp-001", "lighting")
            unsafe_product["session_token"] = "must-not-be-accepted"
            source_path.write_text(
                json.dumps(
                    _catalog_document(
                        catalog_nodes=[
                            {"catalog_node_id": "home", "display_name": "Home"},
                            {
                                "catalog_node_id": "lighting",
                                "display_name": "Lighting",
                                "parent_catalog_node_id": "home",
                            },
                        ],
                        products=[unsafe_product],
                    )
                ),
                encoding="utf-8",
            )

            with self.assertRaises(ApplicationContractError) as error:
                inspect_declared_source_catalog("local-json-file", source_path.as_uri())

        self.assertEqual(error.exception.code, "LOCAL_FILE_PRODUCT_INVALID")

    def test_inspection_rejects_nested_restricted_material_before_exposing_nodes(self) -> None:
        cases = (
            ("source_fields", {"details": {"session_token": "must-not-be-accepted"}}),
            ("attributes", {"transport": {"proxy": "must-not-be-accepted"}}),
        )
        for field_name, nested_value in cases:
            with self.subTest(field_name=field_name), TemporaryDirectory() as directory:
                source_path = Path(directory) / "nested-unsafe-product.json"
                unsafe_product = _product("lamp-001", "lighting")
                unsafe_product[field_name] = nested_value
                source_path.write_text(
                    json.dumps(
                        _catalog_document(
                            catalog_nodes=[
                                {"catalog_node_id": "home", "display_name": "Home"},
                                {
                                    "catalog_node_id": "lighting",
                                    "display_name": "Lighting",
                                    "parent_catalog_node_id": "home",
                                },
                            ],
                            products=[unsafe_product],
                        )
                    ),
                    encoding="utf-8",
                )

                with self.assertRaises(ApplicationContractError) as error:
                    inspect_declared_source_catalog("local-json-file", source_path.as_uri())

                self.assertEqual(error.exception.code, "LOCAL_FILE_PRODUCT_INVALID")


def _catalog_document(*, catalog_nodes: list[dict[str, object]], products: list[dict[str, object]]) -> dict[str, object]:
    return {
        "format": "parserriba-local-catalog-v1",
        "observed_at": "2026-08-15T00:00:00Z",
        "catalog_nodes": catalog_nodes,
        "products": products,
    }


def _product(product_id: str, catalog_node_id: str) -> dict[str, object]:
    return {
        "observation_id": f"{product_id}-observation",
        "source_product_id": f"{product_id}-source",
        "normalized_product_id": f"{product_id}-normalized",
        "catalog_node_id": catalog_node_id,
        "name": "Example lamp",
        "source_fields": {"title": "Example lamp"},
    }


if __name__ == "__main__":
    unittest.main()
