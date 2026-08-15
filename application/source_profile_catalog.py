"""Declared local SourceProfile choices shared by launcher selection and task collection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from application.contracts import ApplicationContractError, SourceKind, SourceProfile


@dataclass(frozen=True)
class DeclaredSourceProfile:
    """One user-selectable local source choice with no selected default."""

    source_profile_id: str
    display_name: str
    source_kind: SourceKind
    adapter_id: str
    adapter_version: str
    fixed_source_locator: str | None
    catalog_node_options: tuple[tuple[str, str], ...] = ()

    @property
    def requires_source_locator(self) -> bool:
        return self.fixed_source_locator is None


_DECLARED_SOURCE_PROFILES = (
    DeclaredSourceProfile(
        source_profile_id="synthetic-example-catalog",
        display_name="Примерный каталог (fixture)",
        source_kind=SourceKind.FIXTURE,
        adapter_id="synthetic-fixture-v1",
        adapter_version="1",
        fixed_source_locator="fixture://example-catalog-v1",
        catalog_node_options=(
            ("example-notebooks", "Пример: тетради"),
            ("example-lamps", "Пример: лампы"),
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
            ("recorded-dom-example", "Записанный пример DOM"),
            ("recorded-api-example", "Записанный пример API"),
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


def catalog_node_display_name(source_profile_id: str, catalog_node_id: str) -> str:
    """Return a declared display name; file node IDs remain explicit user input."""
    declared = _BY_ID.get(source_profile_id)
    if declared is not None:
        for node_id, display_name in declared.catalog_node_options:
            if node_id == catalog_node_id:
                return display_name
    return catalog_node_id


def _required_text(value: Any, code: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ApplicationContractError(code, f"{code}: Make an explicit selection before collection.")
    return text
