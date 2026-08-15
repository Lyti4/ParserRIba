"""Source-neutral local task projection for explicit adapter collection."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Mapping

from application.recorded_legacy_fixture_adapter import (
    RecordedLegacyFixtureSourceAdapter,
    recorded_legacy_fixture_document,
)
from application.contracts import (
    ApplicationContractError,
    CollectionRequest,
    SourceKind,
    TerminalOutcome,
    require_artifact_run_id,
)
from application.source_profile_catalog import inspect_declared_source_catalog
from application.workspace import ProductWorkspace
from application.source_adapters import (
    LocalJsonFileSourceAdapter,
    SourceAdapterRegistry,
    SyntheticFixtureSourceAdapter,
)
from models.task_actor import RunManifest, TaskStatus

if TYPE_CHECKING:
    from application.browser_source_registration import BrowserSourceRegistration

DiscoverFunc = Callable[..., Awaitable[Any]]
_DECLARED_SOURCE_REQUIRED_KEYS = frozenset(
    {"collection_run_id", "source_profile_id", "catalog_node_ids"}
)
_DECLARED_SOURCE_ALLOWED_KEYS = _DECLARED_SOURCE_REQUIRED_KEYS | {"source_locator"}


async def run_source_adapter_collection_task(
    *,
    task_input: dict[str, Any],
    root_dir: Path,
    discover_func: DiscoverFunc | None = None,
    browser_registration: BrowserSourceRegistration | None = None,
) -> RunManifest:
    """Collect one explicitly selected source through its dependency-light adapter seam."""
    del discover_func
    request = build_source_adapter_collection_request(
        task_input,
        browser_registration=browser_registration,
    )
    if request.source_profile.source_kind is SourceKind.BROWSER:
        if (
            browser_registration is None
            or request.source_profile.source_profile_id
            != browser_registration.declared_profile.source_profile_id
        ):
            raise ApplicationContractError(
                "SOURCE_ADAPTER_UNAVAILABLE",
                "SOURCE_ADAPTER_UNAVAILABLE: No selected browser adapter is registered.",
            )
        result = await browser_registration.adapter.collect(request)
    else:
        result = SourceAdapterRegistry(
            (
                SyntheticFixtureSourceAdapter(),
                LocalJsonFileSourceAdapter(),
                RecordedLegacyFixtureSourceAdapter(recorded_legacy_fixture_document()),
            )
        ).collect(request)
    workspace_path = _workspace_artifact_path(root_dir, request.collection_run_id)
    ProductWorkspace.from_collection_results((result,)).write_json(workspace_path)
    artifact_paths = {**result.artifact_refs, "workspace_json": str(workspace_path)}
    return _collection_manifest(
        request=request,
        terminal_outcome=result.terminal_outcome,
        result=result,
        artifact_paths=artifact_paths,
    )


def build_source_adapter_collection_request(
    task_input: Mapping[str, Any],
    *,
    browser_registration: BrowserSourceRegistration | None = None,
) -> CollectionRequest:
    """Build one request without profile, locator or node fallbacks."""
    input_keys = set(task_input)
    if not input_keys.issubset(_DECLARED_SOURCE_ALLOWED_KEYS):
        raise ApplicationContractError(
            "SOURCE_COLLECTION_INPUT_INVALID",
            "SOURCE_COLLECTION_INPUT_INVALID: Source collection accepts only explicit declared fields.",
        )
    collection_run_id = require_artifact_run_id(task_input.get("collection_run_id"))
    node_ids = _selected_catalog_node_ids(task_input)
    if (
        browser_registration is not None
        and task_input.get("source_profile_id")
        == browser_registration.declared_profile.source_profile_id
        and "source_locator" in input_keys
    ):
        raise ApplicationContractError(
            "BROWSER_SOURCE_LOCATOR_FIXED",
            "BROWSER_SOURCE_LOCATOR_FIXED: Browser registration owns its fixed source locator.",
        )
    inspected = inspect_declared_source_catalog(
        task_input.get("source_profile_id"),
        task_input.get("source_locator"),
        browser_registration=browser_registration,
    )
    profile = inspected.source_profile
    nodes_by_id = {node.catalog_node_id: node for node in inspected.catalog_nodes}
    unavailable = next((node_id for node_id in node_ids if node_id not in nodes_by_id), None)
    if unavailable is not None:
        raise ApplicationContractError(
            "SOURCE_CATALOG_NODE_UNAVAILABLE",
            f"SOURCE_CATALOG_NODE_UNAVAILABLE: The selected catalog node is unavailable: {unavailable}.",
        )
    return CollectionRequest(
        collection_run_id=collection_run_id,
        source_profile=profile,
        catalog_nodes=tuple(
            nodes_by_id[node_id].model_copy(update={"locator": profile.source_locator})
            for node_id in node_ids
        ),
    )


def _selected_catalog_node_ids(task_input: Mapping[str, Any]) -> tuple[str, ...]:
    raw_ids = task_input.get("catalog_node_ids")
    if not isinstance(raw_ids, (list, tuple)) or not raw_ids:
        raise ApplicationContractError(
            "COLLECTION_SCOPE_REQUIRED",
            "COLLECTION_SCOPE_REQUIRED: Select at least one CatalogNode explicitly.",
        )
    node_ids: list[str] = []
    for node_id in raw_ids:
        if not isinstance(node_id, str) or not node_id or node_id != node_id.strip():
            raise ApplicationContractError(
                "COLLECTION_SCOPE_INVALID",
                "COLLECTION_SCOPE_INVALID: Each CatalogNode ID must be an explicit non-empty string.",
            )
        if node_id in node_ids:
            raise ApplicationContractError(
                "COLLECTION_SCOPE_DUPLICATE",
                "COLLECTION_SCOPE_DUPLICATE: A CatalogNode may be selected once only.",
            )
        node_ids.append(node_id)
    return tuple(node_ids)



def _workspace_artifact_path(root_dir: Path, collection_run_id: str) -> Path:
    if not isinstance(root_dir, Path):
        raise ApplicationContractError(
            "WORKSPACE_ARTIFACT_ROOT_INVALID",
            "WORKSPACE_ARTIFACT_ROOT_INVALID: Workspace storage needs a local task root path.",
        )
    task_root = root_dir.resolve()
    declared_workspace_root = task_root / "workspaces"
    if declared_workspace_root.is_symlink():
        raise ApplicationContractError(
            "WORKSPACE_ARTIFACT_ROOT_INVALID",
            "WORKSPACE_ARTIFACT_ROOT_INVALID: Workspace storage root must not be a symbolic link.",
        )
    workspace_root = declared_workspace_root.resolve()
    workspace_path = (workspace_root / f"{collection_run_id}.json").resolve()
    try:
        workspace_root.relative_to(task_root)
        workspace_path.relative_to(workspace_root)
        workspace_path.relative_to(task_root)
    except ValueError as error:
        raise ApplicationContractError(
            "WORKSPACE_ARTIFACT_PATH_INVALID",
            "WORKSPACE_ARTIFACT_PATH_INVALID: Workspace artifact must remain under the task workspace root.",
        ) from error
    return workspace_path


def _collection_manifest(
    *,
    request: CollectionRequest,
    terminal_outcome: TerminalOutcome,
    result: Any,
    artifact_paths: Mapping[str, str],
) -> RunManifest:
    products = [
        {
            "product_id": product.normalized_product_id,
            "name": product.name,
            "category": product.category,
            "price": {"current": product.price},
            "availability": product.availability,
            "brand": product.brand,
            "supplier": product.supplier,
            "country": product.country,
            "raw_data": dict(product.attributes),
            "provenance": product.provenance.model_dump(mode="json"),
        }
        for product in result.normalized_products
    ]
    selected_nodes = [
        {
            "catalog_node_id": node.catalog_node_id,
            "name": node.display_name,
            "locator": node.locator,
        }
        for node in request.catalog_nodes
    ]
    return RunManifest(
        task_name="source_adapter_collection",
        shop="source-profile",
        intent="source-collection",
        input={
            "collection_run_id": request.collection_run_id,
            "source_profile_id": request.source_profile.source_profile_id,
            "catalog_node_ids": [node.catalog_node_id for node in request.catalog_nodes],
        },
        status=_collection_manifest_status(terminal_outcome, has_products=bool(products)),
        artifact_paths=dict(artifact_paths),
        summary={
            "active_profile_id": request.source_profile.source_profile_id,
            "display_name": request.source_profile.display_name,
            "source_locator": request.source_profile.source_locator,
            "adapter_id": request.source_profile.adapter_id,
            "adapter_version": request.source_profile.adapter_version,
            "terminal_outcome": terminal_outcome.value,
            "selected_catalog_node_ids": [node.catalog_node_id for node in request.catalog_nodes],
            "selected_catalog_nodes": selected_nodes,
            "categories": [node.display_name for node in request.catalog_nodes],
            "products_count": len(products),
            "products": products,
        },
    )


def _collection_manifest_status(terminal_outcome: TerminalOutcome, *, has_products: bool) -> TaskStatus:
    if terminal_outcome is TerminalOutcome.READY:
        return "ok" if has_products else "empty"
    if terminal_outcome is TerminalOutcome.MANUAL_ACTION_REQUIRED:
        return "needs_operator"
    return "failed"
