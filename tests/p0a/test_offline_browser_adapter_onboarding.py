from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys
import unittest

from application.browser_source_adapter import BrowserSourceAdapter
from application.browser_source_registration import BrowserSourceRegistration
from application.contracts import ApplicationContractError, CollectionRequest, SourceKind
from application.source_profile_catalog import (
    DeclaredCatalogNode,
    DeclaredSourceProfile,
    declared_source_profiles,
)
from utils.local_task_registry import run_local_task
from utils.source_adapter_tasks import run_source_adapter_collection_task


class _RecordingBrowserRunner:
    def __init__(
        self,
        *,
        terminal_outcome: str = "ready",
        include_products: bool = True,
        include_unknown_metadata: bool = False,
    ) -> None:
        self.requests: list[CollectionRequest] = []
        self.terminal_outcome = terminal_outcome
        self.include_products = include_products
        self.include_unknown_metadata = include_unknown_metadata

    async def collect(self, request: CollectionRequest) -> dict[str, object]:
        self.requests.append(request)
        evidence: dict[str, object] = {
            "format": "parserriba-browser-evidence-v1",
            "terminal_outcome": self.terminal_outcome,
            "products": [
                {
                    "observation_id": "example-browser-observation-001",
                    "source_product_id": "example-browser-product-001",
                    "normalized_product_id": "example-browser-normalized-001",
                    "catalog_node_id": "example-browser-items",
                    "observed_at": "2026-08-15T00:00:00Z",
                    "evidence_ref": "https://catalog.example.test/products/example-browser-product-001",
                    "name": "Example browser product",
                    "source_fields": {"title": "Example browser product"},
                }
            ]
            if self.include_products
            else [],
            "artifact_refs": {},
            "diagnostics": [],
        }
        if self.include_unknown_metadata:
            evidence["unknown_metadata"] = "not-allowed"
        return evidence


def _browser_registration(runner: _RecordingBrowserRunner) -> BrowserSourceRegistration:
    return BrowserSourceRegistration(
        declared_profile=DeclaredSourceProfile(
            source_profile_id="example-browser-catalog",
            display_name="Example browser catalog",
            source_kind=SourceKind.BROWSER,
            adapter_id=BrowserSourceAdapter.adapter_id,
            adapter_version=BrowserSourceAdapter.adapter_version,
            fixed_source_locator="https://catalog.example.test/catalog",
            catalog_node_options=(
                DeclaredCatalogNode("example-browser-items", "Example browser items"),
            ),
        ),
        adapter=BrowserSourceAdapter(runner),
    )


class OfflineBrowserAdapterOnboardingTests(unittest.IsolatedAsyncioTestCase):
    def test_default_source_task_import_path_is_browser_free(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    "import application.source_profile_catalog; "
                    "import utils.source_adapter_tasks; "
                    "import utils.local_task_registry; "
                    "raise SystemExit(int('application.browser_source_adapter' in sys.modules))"
                ),
            ],
            cwd=Path(__file__).resolve().parents[2],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    async def test_registered_browser_adapter_is_unreachable_for_an_unrelated_explicit_source(self) -> None:
        runner = _RecordingBrowserRunner()
        registration = _browser_registration(runner)

        with TemporaryDirectory() as directory:
            manifest = await run_source_adapter_collection_task(
                task_input={
                    "collection_run_id": "fixture-selection-run",
                    "source_profile_id": "synthetic-example-catalog",
                    "catalog_node_ids": ["example-notebooks"],
                },
                root_dir=Path(directory),
                browser_registration=registration,
            )

        self.assertNotIn(
            registration.declared_profile.source_profile_id,
            {profile.source_profile_id for profile in declared_source_profiles()},
        )
        self.assertIn(
            registration.declared_profile.source_profile_id,
            {
                profile.source_profile_id
                for profile in declared_source_profiles(registration)
            },
        )
        self.assertEqual(runner.requests, [])
        self.assertEqual(manifest.summary["active_profile_id"], "synthetic-example-catalog")
        self.assertEqual(manifest.summary["products_count"], 1)

    async def test_exact_registered_browser_profile_dispatches_the_injected_adapter(self) -> None:
        runner = _RecordingBrowserRunner()
        registration = _browser_registration(runner)

        with TemporaryDirectory() as directory:
            manifest = await run_local_task(
                "source_adapter_collection",
                {
                    "collection_run_id": "browser-selection-run",
                    "source_profile_id": "example-browser-catalog",
                    "catalog_node_ids": ["example-browser-items"],
                },
                root_dir=Path(directory),
                browser_registration=registration,
            )
            workspace_path = Path(manifest.artifact_paths["workspace_json"])
            self.assertTrue(workspace_path.is_file())

        self.assertEqual(len(runner.requests), 1)
        request = runner.requests[0]
        self.assertEqual(request.source_profile.source_profile_id, "example-browser-catalog")
        self.assertEqual(request.source_profile.adapter_id, BrowserSourceAdapter.adapter_id)
        self.assertEqual(
            [node.catalog_node_id for node in request.catalog_nodes],
            ["example-browser-items"],
        )
        self.assertEqual(manifest.status, "ok")
        self.assertEqual(manifest.summary["products_count"], 1)
        self.assertEqual(
            manifest.summary["products"][0]["name"],
            "Example browser product",
        )

    async def test_browser_profile_is_unavailable_without_its_registration(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(ApplicationContractError) as raised:
                await run_source_adapter_collection_task(
                    task_input={
                        "collection_run_id": "unregistered-browser-run",
                        "source_profile_id": "example-browser-catalog",
                        "catalog_node_ids": ["example-browser-items"],
                    },
                    root_dir=Path(directory),
                )

        self.assertEqual(raised.exception.code, "SOURCE_PROFILE_UNAVAILABLE")

    async def test_registered_browser_locator_cannot_be_supplied_per_run(self) -> None:
        for source_locator in (None, "", "https://catalog.example.test/other"):
            with self.subTest(source_locator=source_locator):
                runner = _RecordingBrowserRunner()
                registration = _browser_registration(runner)
                with TemporaryDirectory() as directory:
                    with self.assertRaises(ApplicationContractError) as raised:
                        await run_source_adapter_collection_task(
                            task_input={
                                "collection_run_id": "browser-locator-override-run",
                                "source_profile_id": "example-browser-catalog",
                                "source_locator": source_locator,
                                "catalog_node_ids": ["example-browser-items"],
                            },
                            root_dir=Path(directory),
                            browser_registration=registration,
                        )

                self.assertEqual(
                    raised.exception.code,
                    "BROWSER_SOURCE_LOCATOR_FIXED",
                )
                self.assertEqual(runner.requests, [])

    async def test_manual_browser_outcome_publishes_no_products(self) -> None:
        runner = _RecordingBrowserRunner(
            terminal_outcome="manual_action_required",
            include_products=False,
        )
        registration = _browser_registration(runner)

        with TemporaryDirectory() as directory:
            manifest = await run_source_adapter_collection_task(
                task_input={
                    "collection_run_id": "manual-browser-run",
                    "source_profile_id": "example-browser-catalog",
                    "catalog_node_ids": ["example-browser-items"],
                },
                root_dir=Path(directory),
                browser_registration=registration,
            )

        self.assertEqual(len(runner.requests), 1)
        self.assertEqual(manifest.status, "needs_operator")
        self.assertEqual(manifest.summary["terminal_outcome"], "manual_action_required")
        self.assertEqual(manifest.summary["products_count"], 0)
        self.assertEqual(manifest.summary["products"], [])

    async def test_unknown_browser_evidence_fails_before_workspace_publication(self) -> None:
        runner = _RecordingBrowserRunner(include_unknown_metadata=True)
        registration = _browser_registration(runner)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ApplicationContractError) as raised:
                await run_source_adapter_collection_task(
                    task_input={
                        "collection_run_id": "unknown-browser-evidence-run",
                        "source_profile_id": "example-browser-catalog",
                        "catalog_node_ids": ["example-browser-items"],
                    },
                    root_dir=root,
                    browser_registration=registration,
                )
            self.assertFalse(
                (root / "workspaces" / "unknown-browser-evidence-run.json").exists()
            )

        self.assertEqual(len(runner.requests), 1)
        self.assertEqual(raised.exception.code, "BROWSER_EVIDENCE_INVALID")


if __name__ == "__main__":
    unittest.main()
