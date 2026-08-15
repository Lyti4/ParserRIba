from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from application.contracts import (
    ApplicationContractError,
    CatalogNode,
    CollectionRequest,
    CollectionResult,
    NormalizedProduct,
    ProductObservation,
    Provenance,
    SourceKind,
    SourceProfile,
    TerminalOutcome,
)
from application.workspace import ProductWorkspace
from launcher.desktop_action_state import build_action_enabled_map
from launcher.desktop_controller import DesktopLauncherController
from launcher.desktop_controller_workspace import sync_workspace_state
from launcher.desktop_launcher import DesktopLauncherShell
from launcher.desktop_product_details import build_product_detail_text
from launcher.desktop_result_table import build_result_table
from models.task_actor import RunManifest
from utils.local_task_adapter import LocalTaskProcessResult


def _synthetic_workspace_controller(tmp_path: Path) -> tuple[DesktopLauncherController, Path]:
    source = SourceProfile(
        source_profile_id="synthetic-example-catalog",
        display_name="Synthetic example catalog",
        source_kind=SourceKind.FIXTURE,
        source_locator="fixture://synthetic-example-catalog",
        adapter_id="synthetic-example-adapter",
        adapter_version="1",
    )
    nodes = (
        CatalogNode(
            source_profile_id=source.source_profile_id,
            catalog_node_id="example-lamps",
            display_name="Example lamps",
        ),
        CatalogNode(
            source_profile_id=source.source_profile_id,
            catalog_node_id="example-notebooks",
            display_name="Example notebooks",
        ),
    )
    request = CollectionRequest(
        collection_run_id="stage1-synthetic-workspace-001",
        source_profile=source,
        catalog_nodes=nodes,
    )

    def provenance(node: CatalogNode, product_id: str) -> Provenance:
        return Provenance(
            source_profile_id=source.source_profile_id,
            adapter_id=source.adapter_id,
            adapter_version=source.adapter_version,
            collection_run_id=request.collection_run_id,
            catalog_node_id=node.catalog_node_id,
            observed_at="2026-08-14T00:00:00Z",
            evidence_ref=f"fixture://synthetic-example-catalog/products/{product_id}",
            transformation_status="normalized_without_inference",
        )

    lamp_provenance = provenance(nodes[0], "example-lamp-001")
    notebook_provenance = provenance(nodes[1], "example-notebook-001")
    observations = (
        ProductObservation(
            observation_id="example-observation-lamp-001",
            source_product_id="example-source-lamp-001",
            source_fields={
                "request_kind": "document",
                "typed_code": 1,
                "typed_plain": 1,
                "typed_flag": True,
                "case_text": "Blue",
            },
            provenance=lamp_provenance,
        ),
        ProductObservation(
            observation_id="example-observation-notebook-001",
            source_product_id="example-source-notebook-001",
            source_fields={
                "request_kind": "api",
                "typed_code": "1 [number]",
                "typed_plain": "1",
                "typed_flag": "true",
                "case_text": "blue",
            },
            provenance=notebook_provenance,
        ),
    )
    products = (
        NormalizedProduct(
            normalized_product_id="example-lamp-001",
            observation_id=observations[0].observation_id,
            name="Example lamp",
            category="Lighting",
            price="100.00",
            availability=True,
            supplier="Example Supplier",
            attributes={"record_shape": "document-v1"},
            provenance=lamp_provenance,
        ),
        NormalizedProduct(
            normalized_product_id="example-notebook-001",
            observation_id=observations[1].observation_id,
            name="Example notebook",
            category="Stationery",
            price="200.00",
            availability=None,
            brand="Example Brand",
            attributes={"record_shape": "api-v1"},
            provenance=notebook_provenance,
        ),
    )
    workspace = ProductWorkspace.from_collection_results(
        (
            CollectionResult(
                request=request,
                terminal_outcome=TerminalOutcome.READY,
                observations=observations,
                normalized_products=products,
            ),
        )
    )
    workspace_path = workspace.write_json(tmp_path / "artifacts" / "synthetic-workspace.json")
    result = LocalTaskProcessResult(
        manifest=RunManifest(
            task_name="source_adapter_collection",
            shop=source.source_profile_id,
            status="ok",
            artifact_paths={"workspace_json": str(workspace_path)},
            summary={"products_count": 2, "active_profile_id": source.source_profile_id},
        )
    )
    controller = DesktopLauncherController(root_dir=tmp_path)
    sync_workspace_state(controller.state, result)
    return controller, workspace_path


def test_desktop_exports_exact_selected_products_from_current_workspace(tmp_path: Path) -> None:
    controller, workspace_path = _synthetic_workspace_controller(tmp_path)
    selected_product_id = "example-notebook-001"
    assert workspace_path.is_file()
    assert [item["id"] for item in controller.state.products.items] == [
        "example-lamp-001",
        selected_product_id,
    ]

    controller.set_selection(selected_product_ids=[selected_product_id])
    export_path = tmp_path / "exports" / "selected-products.json"

    written_path = controller.export_selected_workspace_products(export_path)

    assert written_path == export_path
    assert json.loads(export_path.read_text(encoding="utf-8")) == {
        "format": "parserriba-product-export-v1",
        "product_ids": [selected_product_id],
        "rows": [
            {
                "attributes.record_shape": "api-v1",
                "name": "Example notebook",
                "normalized.brand": "Example Brand",
                "normalized.category": "Stationery",
                "normalized.price": "200.00",
                "normalized_product_id": selected_product_id,
                "observation_id": "example-observation-notebook-001",
                "source_fields.request_kind": "api",
                "source_fields.case_text": "blue",
                "source_fields.typed_code": "1 [number]",
                "source_fields.typed_plain": "1",
                "source_fields.typed_flag": "true",
            }
        ],
    }


def test_workspace_export_actions_require_their_explicit_selection(tmp_path: Path) -> None:
    controller, _workspace_path = _synthetic_workspace_controller(tmp_path)

    enabled = build_action_enabled_map(controller.state)
    assert enabled["export_workspace_selected"] is False
    assert enabled["export_workspace_filtered"] is False
    assert enabled["export_workspace_all"] is True

    controller.set_selection(selected_product_ids=["example-notebook-001"])
    controller.set_filters({"found_filters": {"source_fields.request_kind": ["api"]}})

    enabled = build_action_enabled_map(controller.state)
    assert enabled["export_workspace_selected"] is True
    assert enabled["export_workspace_filtered"] is True
    assert enabled["export_workspace_all"] is True


def test_desktop_exports_exact_filtered_and_explicit_whole_workspace(tmp_path: Path) -> None:
    controller, _workspace_path = _synthetic_workspace_controller(tmp_path)
    assert controller.state.products.discovered_fields["attributes.record_shape"] == {
        '"api-v1"': 1,
        '"document-v1"': 1,
    }

    controller.set_filters(
        {
            "categories": ["legacy-category-must-not-drive-workspace-export"],
            "found_filters": {"attributes.record_shape": ['"document-v1"']},
        }
    )
    filtered_path = tmp_path / "exports" / "filtered-products.json"
    controller.export_filtered_workspace(filtered_path)
    filtered = json.loads(filtered_path.read_text(encoding="utf-8"))
    assert filtered["product_ids"] == ["example-lamp-001"]
    assert all("provenance" not in row for row in filtered["rows"])

    whole_path = tmp_path / "exports" / "whole-workspace.json"
    controller.export_whole_workspace(whole_path)
    whole = json.loads(whole_path.read_text(encoding="utf-8"))
    assert whole["product_ids"] == ["example-lamp-001", "example-notebook-001"]


def test_workspace_export_rejects_implicit_or_unsafe_requests(tmp_path: Path) -> None:
    controller, _workspace_path = _synthetic_workspace_controller(tmp_path)

    empty_selection_path = tmp_path / "exports" / "empty-selection.json"
    with pytest.raises(ApplicationContractError, match="WORKSPACE_EXPORT_SELECTION_REQUIRED"):
        controller.export_selected_workspace_products(empty_selection_path)
    assert not empty_selection_path.exists()

    empty_filter_path = tmp_path / "exports" / "empty-filter.json"
    with pytest.raises(ApplicationContractError, match="WORKSPACE_FILTER_REQUIRED"):
        controller.export_filtered_workspace(empty_filter_path)
    assert not empty_filter_path.exists()

    with pytest.raises(ApplicationContractError, match="WORKSPACE_EXPORT_PATH_INVALID"):
        controller.export_whole_workspace(Path("relative-export.json"))
    assert not (tmp_path / "relative-export.json").exists()


def test_desktop_exports_exact_normalized_workspace_facet(tmp_path: Path) -> None:
    controller, _workspace_path = _synthetic_workspace_controller(tmp_path)

    assert controller.state.products.discovered_fields["normalized.price"] == {
        '"100.00"': 1,
        '"200.00"': 1,
    }
    controller.set_filters({"found_filters": {"normalized.price": ['"200.00"']}})
    output_path = tmp_path / "exports" / "normalized-price.json"

    controller.export_filtered_workspace(output_path)

    assert json.loads(output_path.read_text(encoding="utf-8"))["product_ids"] == [
        "example-notebook-001"
    ]


def test_typed_facet_options_keep_exact_scalar_identity_in_preview_and_export(
    tmp_path: Path,
) -> None:
    controller, _workspace_path = _synthetic_workspace_controller(tmp_path)
    assert controller.state.products.discovered_fields["source_fields.typed_code"] == {
        "1": 1,
        '"1 [number]"': 1,
    }
    assert controller.state.products.discovered_fields["source_fields.typed_plain"] == {
        "1": 1,
        '"1"': 1,
    }
    assert controller.state.products.discovered_fields["source_fields.typed_flag"] == {
        "true": 1,
        '"true"': 1,
    }

    controller.set_filters(
        {"found_filters": {"source_fields.typed_code": ['"1 [number]"']}}
    )
    assert build_result_table(controller.state)["product_ids"] == ["example-notebook-001"]
    text_path = tmp_path / "exports" / "typed-text.json"
    controller.export_filtered_workspace(text_path)
    assert json.loads(text_path.read_text(encoding="utf-8"))["product_ids"] == [
        "example-notebook-001"
    ]

    controller.set_filters({"found_filters": {"source_fields.typed_flag": ["true"]}})
    assert build_result_table(controller.state)["product_ids"] == ["example-lamp-001"]
    boolean_path = tmp_path / "exports" / "typed-boolean.json"
    controller.export_filtered_workspace(boolean_path)
    assert json.loads(boolean_path.read_text(encoding="utf-8"))["product_ids"] == [
        "example-lamp-001"
    ]

    controller.set_filters({"found_filters": {"source_fields.case_text": ['"Blue"']}})
    assert build_result_table(controller.state)["product_ids"] == ["example-lamp-001"]
    case_path = tmp_path / "exports" / "case-exact.json"
    controller.export_filtered_workspace(case_path)
    assert json.loads(case_path.read_text(encoding="utf-8"))["product_ids"] == [
        "example-lamp-001"
    ]


def test_workspace_table_and_details_preserve_supplier_and_unknown_availability(
    tmp_path: Path,
) -> None:
    controller, _workspace_path = _synthetic_workspace_controller(tmp_path)

    table = build_result_table(controller.state)
    assert table["rows"][0][3] == "Example Supplier"
    assert table["rows"][1][3] == ""
    assert table["rows"][1][7] == "Неизвестно"

    details = build_product_detail_text(
        "",
        ["example-notebook-001"],
        controller.state.products.items,
    )
    assert "Наличие: Неизвестно" in details
    assert "Поставщик/производитель: Example Brand" not in details


@pytest.mark.parametrize("workspace_case", ["missing", "blank", "invalid"])
def test_source_adapter_workspace_sync_clears_stale_state_before_rejecting_invalid_artifact(
    tmp_path: Path,
    workspace_case: str,
) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    controller.state.selection.selected_product_ids = ["stale-product"]
    controller.state.products.items = [{"id": "stale-product"}]
    controller.state.products.products_count = 1
    controller.state.products.selected_product_ids = ["stale-product"]
    controller.state.products.discovered_fields = {"attributes.stale": {"yes": 1}}
    controller.state.filters.found_filters = {"attributes.stale": ["yes"]}
    controller.state.dynamic_filters.available_filters = {
        "attributes.stale": {"kind": "found_field"}
    }
    legacy_path = tmp_path / "legacy-products.json"
    legacy_product = {"id": "legacy-stale", "name": "Legacy stale product"}
    legacy_path.write_text(json.dumps({"products": [legacy_product]}), encoding="utf-8")
    controller.state.result.json_path = str(legacy_path)
    controller.state.products.json_path = str(legacy_path)
    controller.state.result.summary = {"products": [legacy_product]}
    controller.state.result.launcher_view = {"products": [legacy_product]}

    if workspace_case == "missing":
        artifact_paths: dict[str, str] = {}
    elif workspace_case == "blank":
        artifact_paths = {"workspace_json": " "}
    else:
        invalid_path = tmp_path / "invalid-workspace.json"
        invalid_path.write_text("{}", encoding="utf-8")
        artifact_paths = {"workspace_json": str(invalid_path)}
    result = LocalTaskProcessResult(
        manifest=RunManifest(
            task_name="source_adapter_collection",
            shop="synthetic-example-catalog",
            status="ok",
            artifact_paths=artifact_paths,
        )
    )

    with pytest.raises(ApplicationContractError):
        sync_workspace_state(controller.state, result)

    assert controller.state.selection.selected_product_ids == []
    assert controller.state.products.items == []
    assert controller.state.products.products_count == 0
    assert controller.state.products.selected_product_ids == []
    assert controller.state.products.discovered_fields == {}
    assert controller.state.filters.found_filters == {}
    assert controller.state.dynamic_filters.available_filters == {}
    assert controller.state.result.json_path == ""
    assert "products" not in controller.state.result.summary
    assert "products" not in controller.state.result.launcher_view
    assert build_result_table(controller.state)["rows"] == []


def test_valid_empty_workspace_cannot_repopulate_legacy_products(tmp_path: Path) -> None:
    controller, workspace_path = _synthetic_workspace_controller(tmp_path)
    workspace = ProductWorkspace.load_json(workspace_path)
    empty_workspace = ProductWorkspace(
        observations=(),
        normalized_products=(),
        declared_field_definitions=workspace.declared_field_definitions,
    )
    empty_path = empty_workspace.write_json(tmp_path / "empty-workspace.json")
    legacy_product = {"id": "legacy-stale", "name": "Legacy stale product"}
    legacy_path = tmp_path / "legacy-products.json"
    legacy_path.write_text(json.dumps({"products": [legacy_product]}), encoding="utf-8")
    controller.state.result.json_path = str(legacy_path)
    controller.state.products.json_path = str(legacy_path)
    controller.state.result.summary = {"products": [legacy_product]}
    controller.state.result.launcher_view = {"products": [legacy_product]}
    result = LocalTaskProcessResult(
        manifest=RunManifest(
            task_name="source_adapter_collection",
            shop="synthetic-example-catalog",
            status="ok",
            artifact_paths={"workspace_json": str(empty_path)},
        )
    )

    sync_workspace_state(controller.state, result)

    assert controller.state.products.items == []
    assert controller.state.result.json_path == ""
    assert build_result_table(controller.state)["rows"] == []


def test_workspace_export_actions_reject_existing_non_workspace_json(tmp_path: Path) -> None:
    controller = DesktopLauncherController(root_dir=tmp_path)
    invalid_path = tmp_path / "not-a-workspace.json"
    invalid_path.write_text("{}", encoding="utf-8")
    controller.state.result.artifact_paths["workspace_json"] = str(invalid_path)
    controller.state.selection.selected_product_ids = ["stale-product"]
    controller.state.filters.found_filters = {"attributes.stale": ["yes"]}

    enabled = build_action_enabled_map(controller.state)

    assert enabled["export_workspace_selected"] is False
    assert enabled["export_workspace_filtered"] is False
    assert enabled["export_workspace_all"] is False


def test_controller_persists_failed_terminal_state_when_workspace_application_fails(
    tmp_path: Path,
) -> None:
    invalid_path = tmp_path / "invalid-workspace.json"
    invalid_path.write_text("{}", encoding="utf-8")
    failed_result = LocalTaskProcessResult(
        manifest=RunManifest(
            task_name="source_adapter_collection",
            shop="synthetic-example-catalog",
            status="ok",
            artifact_paths={"workspace_json": str(invalid_path)},
        )
    )
    controller = DesktopLauncherController(
        root_dir=tmp_path,
        source_adapter_collection_runner=lambda **_kwargs: failed_result,
    )

    with pytest.raises(ApplicationContractError):
        controller.run_source_adapter_collection(
            collection_run_id="stage1-invalid-workspace-001",
            source_profile_id="synthetic-example-catalog",
            catalog_node_ids=["example-lamps"],
        )

    assert controller.state.task.status == "failed"
    assert controller.settings_store.load_app_state().task.status == "failed"


def test_workspace_export_dialog_synchronizes_widgets_before_path_selection(tmp_path: Path) -> None:
    events: list[str] = []
    selected_path = tmp_path / "exports" / "selected.json"

    class _FileDialog:
        @staticmethod
        def getSaveFileName(*_args: Any) -> tuple[str, str]:
            events.append("dialog")
            return str(selected_path), "JSON (*.json)"

    class _QtWidgets:
        QFileDialog = _FileDialog

    class _Shell:
        _qtwidgets = _QtWidgets
        window = object()
        root_dir = tmp_path
        category_list = object()

        def _update_state_from_widgets(self) -> None:
            events.append("sync")

        def _run_ui_action(self, _action: Any) -> None:
            events.append("dispatch")

    DesktopLauncherShell._run_workspace_export_dialog(
        cast(DesktopLauncherShell, _Shell()),
        title="Save selected products",
        suggested_name="selected.json",
        action=lambda output_path: output_path,
    )

    assert events == ["sync", "dialog", "dispatch"]
