from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

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
    SourceKind,
    SourceProfile,
    TerminalOutcome,
)
from application.workspace import (
    ProductWorkspace,
    WorkspaceExportRequest,
    WorkspaceFilter,
)


class ProductWorkspaceTests(unittest.TestCase):
    def _result(
        self,
        *,
        source_profile_id: str,
        run_id: str,
        observation_id: str,
        product_id: str,
        attributes: dict[str, object],
        source_fields: dict[str, object],
        field_definitions: tuple[FieldDefinition, ...] = (),
    ) -> CollectionResult:
        source = SourceProfile(
            source_profile_id=source_profile_id,
            display_name=f"{source_profile_id} fixture",
            source_kind=SourceKind.FIXTURE,
            source_locator=f"fixture://{source_profile_id}",
            adapter_id=f"{source_profile_id}-adapter",
            adapter_version="1",
        )
        node = CatalogNode(
            source_profile_id=source_profile_id,
            catalog_node_id=f"{source_profile_id}-node",
            display_name=f"{source_profile_id} node",
        )
        request = CollectionRequest(
            collection_run_id=run_id,
            source_profile=source,
            catalog_nodes=(node,),
        )
        provenance = Provenance(
            source_profile_id=source_profile_id,
            adapter_id=source.adapter_id,
            adapter_version="1",
            collection_run_id=run_id,
            catalog_node_id=node.catalog_node_id,
            observed_at="2026-08-10T00:00:00Z",
            evidence_ref=f"fixture://{source_profile_id}/products/{product_id}",
            transformation_status="normalized_without_inference",
        )
        observation = ProductObservation(
            observation_id=observation_id,
            source_product_id=f"source-{product_id}",
            source_fields=source_fields,
            provenance=provenance,
        )
        product = NormalizedProduct(
            normalized_product_id=product_id,
            observation_id=observation_id,
            name=f"Product {product_id}",
            provenance=provenance,
            attributes=attributes,
        )
        return CollectionResult(
            request=request,
            terminal_outcome=TerminalOutcome.READY,
            observations=(observation,),
            normalized_products=(product,),
            field_definitions=field_definitions,
        )

    def test_workspace_keeps_two_sources_and_their_distinct_optional_fields(self) -> None:
        notebook = self._result(
            source_profile_id="notebook-source",
            run_id="workspace-notebook-run",
            observation_id="notebook-observation",
            product_id="notebook-product",
            attributes={"sheet_count": 80},
            source_fields={"title": "Grid notebook"},
        )
        lamp = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"wattage": 8},
            source_fields={"title": "Desk lamp"},
        )

        workspace = ProductWorkspace.from_collection_results((notebook, lamp))

        self.assertEqual(
            {product.normalized_product_id for product in workspace.normalized_products},
            {"notebook-product", "lamp-product"},
        )
        self.assertEqual(
            {observation.provenance.source_profile_id for observation in workspace.observations},
            {"notebook-source", "lamp-source"},
        )
        self.assertEqual(
            {field.field_id for field in workspace.discovered_fields()},
            {"attributes.sheet_count", "attributes.wattage", "source_fields.title"},
        )
        self.assertEqual(workspace.observations[0].source_fields["title"], "Grid notebook")

    def test_workspace_filters_a_discovered_attribute_without_mutating_stored_products(self) -> None:
        notebook = self._result(
            source_profile_id="notebook-source",
            run_id="workspace-notebook-run",
            observation_id="notebook-observation",
            product_id="notebook-product",
            attributes={"sheet_count": 80},
            source_fields={"title": "Grid notebook"},
        )
        lamp = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"wattage": 8},
            source_fields={"title": "Desk lamp"},
        )
        workspace = ProductWorkspace.from_collection_results((notebook, lamp))

        visible_by_default = workspace.filter(
            WorkspaceFilter(facet_filters={"attributes.sheet_count": (80,)})
        )
        selected = workspace.filter(
            WorkspaceFilter(
                facet_filters={"attributes.sheet_count": (80,)},
                strict=True,
            )
        )

        self.assertEqual(
            [product.normalized_product_id for product in visible_by_default],
            ["notebook-product", "lamp-product"],
        )
        self.assertEqual(
            [product.normalized_product_id for product in selected], ["notebook-product"]
        )
        self.assertEqual(
            [product.normalized_product_id for product in workspace.normalized_products],
            ["notebook-product", "lamp-product"],
        )

    def test_workspace_builds_selected_export_with_requested_provenance(self) -> None:
        result = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"wattage": 8},
            source_fields={"title": "Desk lamp"},
        )
        workspace = ProductWorkspace.from_collection_results((result,))

        exported = workspace.build_export(
            WorkspaceExportRequest(
                product_ids=("lamp-product",), include_provenance=True
            )
        )

        self.assertEqual(exported.product_ids, ("lamp-product",))
        self.assertEqual(exported.rows[0]["attributes.wattage"], 8)
        self.assertEqual(
            exported.rows[0]["provenance.source_profile_id"], "lamp-source"
        )

    def test_workspace_round_trips_canonical_records_to_an_explicit_local_json_path(self) -> None:
        result = self._result(
            source_profile_id="notebook-source",
            run_id="workspace-notebook-run",
            observation_id="notebook-observation",
            product_id="notebook-product",
            attributes={"sheet_count": 80},
            source_fields={"title": "Grid notebook"},
        )
        workspace = ProductWorkspace.from_collection_results((result,))

        with TemporaryDirectory() as directory:
            workspace_path = Path(directory) / "workspace.json"
            workspace.write_json(workspace_path)
            restored = ProductWorkspace.load_json(workspace_path)

        self.assertEqual(
            restored.observations[0].source_fields, workspace.observations[0].source_fields
        )
        self.assertEqual(
            restored.normalized_products[0].provenance,
            workspace.normalized_products[0].provenance,
        )
        self.assertEqual(
            [field.field_id for field in restored.discovered_fields()],
            ["attributes.sheet_count", "source_fields.title"],
        )

    def test_workspace_exposes_declared_facets_and_rejects_conflicting_definitions(self) -> None:
        declared = FieldDefinition(
            field_id="attributes.material",
            display_label="Material",
            value_type=FieldValueType.TEXT,
            is_filterable=True,
        )
        notebook = self._result(
            source_profile_id="notebook-source",
            run_id="workspace-notebook-run",
            observation_id="notebook-observation",
            product_id="notebook-product",
            attributes={"material": "paper"},
            source_fields={"title": "Grid notebook"},
            field_definitions=(declared,),
        )
        workspace = ProductWorkspace.from_collection_results((notebook,))
        fields = {field.field_id: field for field in workspace.discovered_fields()}
        self.assertEqual(fields["attributes.material"], declared)
        unavailable_workspace = ProductWorkspace.from_collection_results(
            (
                self._result(
                    source_profile_id="unavailable-source",
                    run_id="workspace-unavailable-run",
                    observation_id="unavailable-observation",
                    product_id="unavailable-product",
                    attributes={"material": "wood"},
                    source_fields={"title": "Wood fixture"},
                    field_definitions=(
                        FieldDefinition(
                            field_id="attributes.material",
                            display_label="Material",
                            value_type=FieldValueType.TEXT,
                            is_filterable=False,
                        ),
                    ),
                ),
            )
        )
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_FILTER_FIELD_UNAVAILABLE"):
            unavailable_workspace.filter(
                WorkspaceFilter(facet_filters={"attributes.material": ("wood",)})
            )

        conflicting = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"material": "metal"},
            source_fields={"title": "Desk lamp"},
            field_definitions=(
                FieldDefinition(
                    field_id="attributes.material",
                    display_label="Construction material",
                    value_type=FieldValueType.TEXT,
                    is_filterable=True,
                ),
            ),
        )
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_FIELD_DEFINITION_CONFLICT"):
            ProductWorkspace.from_collection_results((notebook, conflicting))

    def test_workspace_discovers_nested_facets_and_preserves_nested_export_values(self) -> None:
        result = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"specification": {"finish": "matte"}, "tags": ["portable", "led"]},
            source_fields={"measurements": {"wattage": 8}},
        )
        workspace = ProductWorkspace.from_collection_results((result,))
        field_ids = {field.field_id for field in workspace.discovered_fields()}
        self.assertTrue(
            {
                "attributes.specification.finish",
                "attributes.tags",
                "source_fields.measurements.wattage",
            }.issubset(field_ids)
        )
        selected = workspace.filter(
            WorkspaceFilter(facet_filters={"attributes.tags": ("LED",)}, strict=True)
        )
        self.assertEqual([product.normalized_product_id for product in selected], ["lamp-product"])
        exported = workspace.build_export(
            WorkspaceExportRequest(product_ids=("lamp-product",))
        )
        self.assertEqual(exported.rows[0]["attributes.specification"], {"finish": "matte"})

    def test_workspace_exports_an_explicit_filtered_selection(self) -> None:
        notebook = self._result(
            source_profile_id="notebook-source",
            run_id="workspace-notebook-run",
            observation_id="notebook-observation",
            product_id="notebook-product",
            attributes={"sheet_count": 80},
            source_fields={"title": "Grid notebook"},
        )
        lamp = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"wattage": 8},
            source_fields={"title": "Desk lamp"},
        )
        workspace = ProductWorkspace.from_collection_results((notebook, lamp))
        exported = workspace.build_export(
            WorkspaceExportRequest(
                filter_selection=WorkspaceFilter(
                    facet_filters={"attributes.sheet_count": (80,)},
                    strict=True,
                )
            )
        )
        self.assertEqual(exported.product_ids, ("notebook-product",))

    def test_workspace_writes_an_explicit_selected_export_to_local_json(self) -> None:
        result = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"wattage": 8},
            source_fields={"title": "Desk lamp"},
        )
        workspace = ProductWorkspace.from_collection_results((result,))

        with TemporaryDirectory() as directory:
            export_path = Path(directory) / "selected-products.json"
            workspace.write_export_json(
                export_path,
                WorkspaceExportRequest(
                    product_ids=("lamp-product",), include_provenance=True
                ),
            )
            payload = json.loads(export_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["format"], "parserriba-product-export-v1")
        self.assertEqual(payload["product_ids"], ["lamp-product"])
        self.assertEqual(
            payload["rows"][0]["provenance.source_profile_id"], "lamp-source"
        )

    def test_workspace_rejects_implicit_export_selection_and_relative_output_path(self) -> None:
        result = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"wattage": 8},
            source_fields={"title": "Desk lamp"},
        )
        workspace = ProductWorkspace.from_collection_results((result,))

        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_EXPORT_SELECTION_REQUIRED"):
            WorkspaceExportRequest()
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_FILTER_REQUIRED"):
            WorkspaceFilter(facet_filters={})
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_FILTER_INVALID"):
            WorkspaceFilter(facet_filters={1: ("paper",)})  # type: ignore[arg-type]
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_COLLECTION_REQUIRED"):
            ProductWorkspace.from_collection_results(())
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_FILTER_FIELD_UNKNOWN"):
            workspace.filter(WorkspaceFilter(facet_filters={"attributes.unknown": ("x",)}))
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_EXPORT_PRODUCT_UNKNOWN"):
            workspace.build_export(WorkspaceExportRequest(product_ids=("unknown-product",)))
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_EXPORT_SELECTION_INVALID"):
            WorkspaceExportRequest(product_ids=(" lamp-product ",))
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_EXPORT_PATH_INVALID"):
            workspace.write_export_json(
                Path("relative-export.json"),
                WorkspaceExportRequest(product_ids=("lamp-product",)),
            )

    def test_workspace_rejects_invalid_record_identity(self) -> None:
        result = self._result(
            source_profile_id="lamp-source",
            run_id="workspace-lamp-run",
            observation_id="lamp-observation",
            product_id="lamp-product",
            attributes={"wattage": 8},
            source_fields={"title": "Desk lamp"},
        )
        observation = result.observations[0]
        product = result.normalized_products[0]
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_OBSERVATION_DUPLICATE"):
            ProductWorkspace((observation, observation), (product,), ())
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_PRODUCT_DUPLICATE"):
            ProductWorkspace((observation,), (product, product), ())
        mismatched = product.model_copy(
            update={"provenance": product.provenance.model_copy(update={"catalog_node_id": "other-node"})}
        )
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_PRODUCT_PROVENANCE_INVALID"):
            ProductWorkspace((observation,), (mismatched,), ())
        definition = FieldDefinition(
            field_id="attributes.wattage",
            display_label="Wattage",
            value_type=FieldValueType.NUMBER,
        )
        with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_FIELD_DEFINITION_DUPLICATE"):
            ProductWorkspace((observation,), (product,), (definition, definition))

    def test_workspace_rejects_invalid_local_documents(self) -> None:
        with TemporaryDirectory() as directory:
            workspace_path = Path(directory) / "workspace.json"
            workspace_path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_READ_FAILED"):
                ProductWorkspace.load_json(workspace_path)
            workspace_path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_DOCUMENT_INVALID"):
                ProductWorkspace.load_json(workspace_path)
            workspace_path.write_text(
                json.dumps(
                    {"format": "unsupported", "observations": [], "normalized_products": [], "field_definitions": []}
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ApplicationContractError, "WORKSPACE_FORMAT_UNSUPPORTED"):
                ProductWorkspace.load_json(workspace_path)


if __name__ == "__main__":
    unittest.main()
