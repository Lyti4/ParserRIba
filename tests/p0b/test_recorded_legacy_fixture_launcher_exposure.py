from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
import unittest

from application.workspace import ProductWorkspace
from launcher.desktop_controller import DesktopLauncherController
from utils.local_task_registry import run_local_task


class RecordedLegacyFixtureLauncherExposureTests(unittest.TestCase):
    def test_explicit_recorded_dom_profile_collects_through_local_task_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest = asyncio.run(
                run_local_task(
                    "source_adapter_collection",
                    {
                        "collection_run_id": "u13-recorded-dom-001",
                        "source_profile_id": "recorded-legacy-fixture",
                        "catalog_node_ids": ["recorded-dom-example"],
                    },
                    root_dir=Path(temp_dir),
                )
            )
            workspace = ProductWorkspace.load_json(Path(manifest.artifact_paths["workspace_json"]))

        self.assertEqual(manifest.status, "ok")
        self.assertEqual(manifest.summary["active_profile_id"], "recorded-legacy-fixture")
        self.assertEqual(manifest.summary["adapter_id"], "recorded-legacy-fixture-v1")
        self.assertEqual(manifest.summary["selected_catalog_node_ids"], ["recorded-dom-example"])
        self.assertEqual([item.source_product_id for item in workspace.observations], ["recorded-dom-example-001"])
        self.assertEqual([item.name for item in workspace.normalized_products], ["Recorded DOM example"])
        self.assertEqual(
            workspace.normalized_products[0].provenance.source_profile_id,
            "recorded-legacy-fixture",
        )

    def test_explicit_recorded_api_profile_collects_through_launcher_controller_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = DesktopLauncherController(root_dir=Path(temp_dir))
            result = controller.run_source_adapter_collection(
                collection_run_id="u13-recorded-api-001",
                source_profile_id="recorded-legacy-fixture",
                catalog_node_ids=["recorded-api-example"],
            )
            workspace = ProductWorkspace.load_json(Path(result.manifest.artifact_paths["workspace_json"]))

        self.assertEqual(result.manifest.status, "ok")
        self.assertEqual(result.manifest.summary["active_profile_id"], "recorded-legacy-fixture")
        self.assertEqual(result.manifest.summary["selected_catalog_node_ids"], ["recorded-api-example"])
        self.assertEqual([item.source_product_id for item in workspace.observations], ["recorded-api-example-001"])
        self.assertEqual(controller.state.result.source_profile_id, "recorded-legacy-fixture")


if __name__ == "__main__":
    unittest.main()
