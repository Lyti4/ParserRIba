"""Source-neutral local task projection for explicit adapter collection."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping
from urllib.parse import urlsplit

from pydantic import ValidationError

from application.browser_source_adapter import BrowserSourceAdapter
from application.recorded_legacy_fixture_adapter import (
    RecordedLegacyFixtureSourceAdapter,
    recorded_legacy_fixture_document,
)
from application.contracts import (
    ApplicationContractError,
    CatalogNode,
    CollectionRequest,
    SourceProfile,
    TerminalOutcome,
    require_artifact_run_id,
)
from application.source_profile_catalog import build_declared_source_profile, catalog_node_display_name
from application.workspace import ProductWorkspace
from application.source_adapters import (
    LocalJsonFileSourceAdapter,
    SourceAdapterRegistry,
    SyntheticFixtureSourceAdapter,
)
from models.task_actor import RunManifest, TaskStatus

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
    browser_adapter: BrowserSourceAdapter | None = None,
) -> RunManifest:
    """Collect one explicitly selected source through its dependency-light adapter seam."""
    del discover_func
    if browser_adapter is None:
        request = build_source_adapter_collection_request(task_input)
        result = SourceAdapterRegistry(
            (
                SyntheticFixtureSourceAdapter(),
                LocalJsonFileSourceAdapter(),
                RecordedLegacyFixtureSourceAdapter(recorded_legacy_fixture_document()),
            )
        ).collect(request)
    else:
        request = _build_injected_browser_collection_request(task_input)
        result = await browser_adapter.collect(request)
    workspace_path = _workspace_artifact_path(root_dir, request.collection_run_id)
    ProductWorkspace.from_collection_results((result,)).write_json(workspace_path)
    artifact_paths = {**result.artifact_refs, "workspace_json": str(workspace_path)}
    return _collection_manifest(
        request=request,
        terminal_outcome=result.terminal_outcome,
        result=result,
        artifact_paths=artifact_paths,
    )


def _build_injected_browser_collection_request(task_input: Mapping[str, Any]) -> CollectionRequest:
    allowed_keys = {"collection_run_id", "source_profile", "catalog_nodes"}
    if set(task_input) != allowed_keys:
        raise ApplicationContractError(
            "BROWSER_COLLECTION_INPUT_INVALID",
            "BROWSER_COLLECTION_INPUT_INVALID: Browser collection requires only an explicit run, profile and nodes.",
        )
    raw_profile = task_input.get("source_profile")
    raw_nodes = task_input.get("catalog_nodes")
    if not isinstance(raw_profile, Mapping) or not isinstance(raw_nodes, (list, tuple)) or not raw_nodes:
        raise ApplicationContractError(
            "BROWSER_COLLECTION_INPUT_INVALID",
            "BROWSER_COLLECTION_INPUT_INVALID: Browser collection requires an explicit SourceProfile and CatalogNodes.",
        )
    if any(not isinstance(node, Mapping) for node in raw_nodes):
        raise ApplicationContractError(
            "BROWSER_COLLECTION_INPUT_INVALID",
            "BROWSER_COLLECTION_INPUT_INVALID: Browser CatalogNodes must be explicit contract objects.",
        )

    raw_locators = [raw_profile.get("source_locator")]
    raw_locators.extend(node.get("locator") for node in raw_nodes)
    for raw_locator in raw_locators:
        if isinstance(raw_locator, str):
            _require_fragment_free_browser_locator(raw_locator)

    try:
        request = CollectionRequest(
            collection_run_id=require_artifact_run_id(task_input.get("collection_run_id")),
            source_profile=SourceProfile.model_validate(raw_profile),
            catalog_nodes=tuple(CatalogNode.model_validate(node) for node in raw_nodes),
        )
    except ValidationError:
        raise ApplicationContractError(
            "BROWSER_COLLECTION_INPUT_INVALID",
            "BROWSER_COLLECTION_INPUT_INVALID: Browser collection contracts are invalid.",
        ) from None
    _require_fragment_free_browser_locator(request.source_profile.source_locator)
    for node in request.catalog_nodes:
        if node.locator is not None:
            _require_fragment_free_browser_locator(node.locator)
    return request


def _require_fragment_free_browser_locator(value: str) -> None:
    try:
        fragment = urlsplit(value).fragment
    except ValueError as error:
        raise ApplicationContractError(
            "BROWSER_COLLECTION_LOCATOR_INVALID",
            "BROWSER_COLLECTION_LOCATOR_INVALID: Browser locator is not safely parseable.",
        ) from error
    if fragment:
        raise ApplicationContractError(
            "BROWSER_COLLECTION_LOCATOR_INVALID",
            "BROWSER_COLLECTION_LOCATOR_INVALID: Browser locators must not contain fragments.",
        )


def build_source_adapter_collection_request(task_input: Mapping[str, Any]) -> CollectionRequest:
    """Build the single U2 collection request without profile, locator or node fallbacks."""
    input_keys = set(task_input)
    if not input_keys.issubset(_DECLARED_SOURCE_ALLOWED_KEYS):
        raise ApplicationContractError(
            "SOURCE_COLLECTION_INPUT_INVALID",
            "SOURCE_COLLECTION_INPUT_INVALID: Source collection accepts only explicit declared fields.",
        )
    profile = _selected_source_profile(task_input)
    node_ids = _selected_catalog_node_ids(task_input)
    return CollectionRequest(
        collection_run_id=require_artifact_run_id(task_input.get("collection_run_id")),
        source_profile=profile,
        catalog_nodes=tuple(
            CatalogNode(
                source_profile_id=profile.source_profile_id,
                catalog_node_id=node_id,
                display_name=_catalog_node_display_name(profile, node_id),
                locator=profile.source_locator,
            )
            for node_id in node_ids
        ),
    )


def _selected_source_profile(task_input: Mapping[str, Any]):
    return build_declared_source_profile(
        task_input.get("source_profile_id"),
        task_input.get("source_locator"),
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


def _catalog_node_display_name(profile, node_id: str) -> str:
    return catalog_node_display_name(profile.source_profile_id, node_id)


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
