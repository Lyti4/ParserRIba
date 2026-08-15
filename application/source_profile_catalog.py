"""Declared local SourceProfile choices shared by launcher selection and task collection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from application.contracts import ApplicationContractError, CatalogNode, SourceKind, SourceProfile
from application.source_adapters import LocalJsonFileSourceAdapter


@dataclass(frozen=True)
class DeclaredCatalogNode:
    """One source-profile-owned catalog option with an optional parent."""

    catalog_node_id: str
    display_name: str
    parent_catalog_node_id: str | None = None


@dataclass(frozen=True)
class DeclaredSourceProfile:
    """One user-selectable local source choice with no selected default."""

    source_profile_id: str
    display_name: str
    source_kind: SourceKind
    adapter_id: str
    adapter_version: str
    fixed_source_locator: str | None
    catalog_node_options: tuple[DeclaredCatalogNode, ...] = ()

    @property
    def requires_source_locator(self) -> bool:
        return self.fixed_source_locator is None


@dataclass(frozen=True)
class InspectedSourceCatalog:
    """One explicit SourceProfile and its validated selectable CatalogNodes."""

    source_profile: SourceProfile
    catalog_nodes: tuple[CatalogNode, ...]


_DECLARED_SOURCE_PROFILES = (
    DeclaredSourceProfile(
        source_profile_id="synthetic-example-catalog",
        display_name="Примерный каталог (fixture)",
        source_kind=SourceKind.FIXTURE,
        adapter_id="synthetic-fixture-v1",
        adapter_version="1",
        fixed_source_locator="fixture://example-catalog-v1",
        catalog_node_options=(
            DeclaredCatalogNode("example-notebooks", "Пример: тетради"),
            DeclaredCatalogNode("example-lamps", "Пример: лампы"),
        ),
    ),
    DeclaredSourceProfile(
        source_profile_id="local-json-file",
        display_name="Локальный JSON-каталог",
        source_kind=SourceKind.FILE,
        adapter_id="local-json-file-v1",
        adapter_version="1",
        fixed_source_locator=None,
    ),
    DeclaredSourceProfile(
        source_profile_id="recorded-legacy-fixture",
        display_name="Записанный каталог (fixture)",
        source_kind=SourceKind.FIXTURE,
        adapter_id="recorded-legacy-fixture-v1",
        adapter_version="1",
        fixed_source_locator="fixture://recorded-legacy-products-v1",
        catalog_node_options=(
            DeclaredCatalogNode("recorded-dom-example", "Записанный пример DOM"),
            DeclaredCatalogNode("recorded-api-example", "Записанный пример API"),
        ),
    ),
)
_BY_ID = {profile.source_profile_id: profile for profile in _DECLARED_SOURCE_PROFILES}


def declared_source_profiles() -> tuple[DeclaredSourceProfile, ...]:
    """Return all visible source choices; callers must still explicitly select one."""
    return _DECLARED_SOURCE_PROFILES


def build_declared_source_profile(source_profile_id: Any, source_locator: Any = None) -> SourceProfile:
    """Build one explicit non-secret SourceProfile with no profile or locator fallback."""
    profile_id = _required_text(source_profile_id, "SOURCE_PROFILE_REQUIRED")
    declared = _BY_ID.get(profile_id)
    if declared is None:
        raise ApplicationContractError(
            "SOURCE_PROFILE_UNAVAILABLE",
            f"SOURCE_PROFILE_UNAVAILABLE: The selected SourceProfile is not available: {profile_id}.",
        )
    locator = declared.fixed_source_locator or _canonical_local_json_file_uri(source_locator)
    return SourceProfile(
        source_profile_id=declared.source_profile_id,
        display_name=declared.display_name,
        source_kind=declared.source_kind,
        source_locator=locator,
        adapter_id=declared.adapter_id,
        adapter_version=declared.adapter_version,
    )


def inspect_declared_source_catalog(
    source_profile_id: Any,
    source_locator: Any = None,
) -> InspectedSourceCatalog:
    """Return the explicit profile and fully validated source-owned catalog nodes."""
    profile = build_declared_source_profile(source_profile_id, source_locator)
    declared = _BY_ID[profile.source_profile_id]
    if declared.adapter_id == LocalJsonFileSourceAdapter.adapter_id:
        nodes = LocalJsonFileSourceAdapter().catalog_nodes(profile)
    else:
        nodes = tuple(
            CatalogNode(
                source_profile_id=profile.source_profile_id,
                catalog_node_id=option.catalog_node_id,
                display_name=option.display_name,
                parent_catalog_node_id=option.parent_catalog_node_id,
            )
            for option in declared.catalog_node_options
        )
    return InspectedSourceCatalog(source_profile=profile, catalog_nodes=nodes)


def source_profile_uses_local_file_picker(source_profile_id: Any) -> bool:
    """Return whether the declared source is an explicit local-file profile."""
    declared = _BY_ID.get(str(source_profile_id or "").strip())
    return bool(
        declared is not None
        and declared.source_kind is SourceKind.FILE
        and declared.requires_source_locator
    )


def _canonical_local_json_file_uri(value: Any) -> str:
    locator = _required_text(value, "SOURCE_LOCATOR_REQUIRED")
    parsed = urlsplit(locator)
    path = Path(unquote(parsed.path))
    canonical = path.as_uri() if path.is_absolute() else ""
    if (
        parsed.scheme != "file"
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or path.suffix.lower() != ".json"
        or locator != canonical
    ):
        raise ApplicationContractError(
            "SOURCE_LOCATOR_LOCAL_ONLY",
            "SOURCE_LOCATOR_LOCAL_ONLY: Use a canonical hostless absolute file:///…/*.json locator.",
        )
    return canonical


def _required_text(value: Any, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ApplicationContractError(code, f"{code}: Make an explicit selection before collection.")
    return text
