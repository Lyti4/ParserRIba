"""Opt-in binding for one explicit browser SourceProfile and injected adapter."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from application.browser_source_adapter import BrowserSourceAdapter
from application.contracts import (
    ApplicationContractError,
    CatalogNode,
    CollectionRequest,
    SourceKind,
    SourceProfile,
)
from application.source_profile_catalog import DeclaredSourceProfile


@dataclass(frozen=True)
class BrowserSourceRegistration:
    """One optional browser profile bound to its exact injected adapter."""

    declared_profile: DeclaredSourceProfile
    adapter: BrowserSourceAdapter

    def __post_init__(self) -> None:
        declared = self.declared_profile
        locator = declared.fixed_source_locator
        try:
            parsed = urlsplit(locator or "")
            parsed.port
            profile = SourceProfile(
                source_profile_id=declared.source_profile_id,
                display_name=declared.display_name,
                source_kind=declared.source_kind,
                source_locator=locator or "",
                adapter_id=declared.adapter_id,
                adapter_version=declared.adapter_version,
            )
            nodes = tuple(
                CatalogNode(
                    source_profile_id=profile.source_profile_id,
                    catalog_node_id=option.catalog_node_id,
                    display_name=option.display_name,
                    parent_catalog_node_id=option.parent_catalog_node_id,
                )
                for option in declared.catalog_node_options
            )
            CollectionRequest(
                collection_run_id="browser-registration-validation",
                source_profile=profile,
                catalog_nodes=nodes,
            )
        except (ApplicationContractError, TypeError, ValueError) as error:
            raise ApplicationContractError(
                "BROWSER_SOURCE_REGISTRATION_INVALID",
                "BROWSER_SOURCE_REGISTRATION_INVALID: Browser registration must contain one valid explicit profile and scope.",
            ) from error
        if (
            declared.source_kind is not SourceKind.BROWSER
            or declared.adapter_id != self.adapter.adapter_id
            or declared.adapter_version != self.adapter.adapter_version
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ApplicationContractError(
                "BROWSER_SOURCE_REGISTRATION_INVALID",
                "BROWSER_SOURCE_REGISTRATION_INVALID: Browser profile and adapter identity must match exactly.",
            )
