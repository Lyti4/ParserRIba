"""Application-workflow task adapters kept outside the generic task registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from models.task_actor import RunManifest

DiscoverFunc = Callable[..., Awaitable[Any]]


async def run_application_workflow_fixture_task(
    *, task_input: dict[str, Any], root_dir: Path, discover_func: DiscoverFunc | None = None
) -> RunManifest:
    del discover_func
    from application.contracts import RunApplicationFixtureCommand
    from application.lifecycle import project_legacy_manifest
    from application.workflow import ApplicationWorkflow

    command = RunApplicationFixtureCommand(
        run_id=str(task_input.get("run_id", "fixture-run-0001")),
        workspace_id=str(task_input.get("workspace_id", "fixture-workspace")),
        profile_id=str(task_input.get("profile_id", "fixture-profile")),
        client_id=str(task_input.get("client_id", "fixture-client")),
        clock_iso=str(task_input.get("clock_iso", "2026-08-09T00:00:00Z")),
        artifact_dir=str(root_dir / ".p0a_fixture"),
        root_dir=str(root_dir),
    )
    result = await ApplicationWorkflow().run_fixture(command)
    return project_legacy_manifest(result, task_name="application_workflow_fixture", shop="fixture-store", intent="fixture-report", task_input=task_input)


async def run_pyaterochka_application_fixture_task(
    *, task_input: dict[str, Any], root_dir: Path, discover_func: DiscoverFunc | None = None
) -> RunManifest:
    del discover_func
    from application.contracts import CollectProductsCommand, RunApplicationFixtureCommand
    from application.lifecycle import project_legacy_manifest
    from application.pyaterochka_fixture import PyaterochkaFixtureAdapter
    from application.workflow import ApplicationWorkflow

    command = RunApplicationFixtureCommand(
        run_id=str(task_input.get("run_id", "pyaterochka-fixture-run-0001")),
        workspace_id=str(task_input.get("workspace_id", "pyaterochka-fixture-workspace")),
        profile_id=str(task_input.get("profile_id", "pyaterochka-fixture-profile")),
        client_id=str(task_input.get("client_id", "pyaterochka-fixture-client")),
        clock_iso=str(task_input.get("clock_iso", "2026-08-09T00:00:00Z")),
        artifact_dir=str(root_dir / ".p0b_fixture"),
        root_dir=str(root_dir),
    )
    selection = CollectProductsCommand(
        run_id=command.run_id,
        catalog_node_ids=tuple(str(node_id) for node_id in task_input.get("catalog_node_ids", ())),
    )
    data = PyaterochkaFixtureAdapter().collect(selection.catalog_node_ids)
    result = await ApplicationWorkflow(fixture_data_provider=lambda: data).run_fixture(command)
    manifest = project_legacy_manifest(
        result,
        task_name="pyaterochka_application_fixture",
        shop="pyaterochka",
        intent="catalog-collection",
        task_input=task_input,
    )
    return manifest.model_copy(update={"summary": _pyaterochka_launcher_summary(manifest.summary, data)})


def _pyaterochka_launcher_summary(summary: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Project fixture-only product cards into the Launcher V2 summary contract."""
    products = [_launcher_product_card(product) for product in data["products"]]
    catalog_nodes = data["catalog_nodes"]
    return {
        **summary,
        "products": products,
        "products_count": len(products),
        "categories": [str(node["name"]) for node in catalog_nodes],
        "source_catalog_node_ids": list(data["source_catalog_node_ids"]),
    }


def _launcher_product_card(product: dict[str, Any]) -> dict[str, Any]:
    card = dict(product)
    raw_data = dict(card.get("raw_data") or {})
    for field_name in ("supplier", "country"):
        if card.get(field_name) is not None:
            raw_data.setdefault(field_name, card[field_name])
    card["raw_data"] = raw_data
    if not isinstance(card.get("price"), dict):
        card["price"] = {"current": card.get("price")}
    return card
