"""Explicit offline launcher exposure for the retained Pyaterochka browser source."""

from __future__ import annotations

from typing import Any

from application.browser_source_adapter import BrowserSourceAdapter
from application.browser_source_registration import BrowserSourceRegistration
from application.contracts import ApplicationContractError, CollectionRequest, SourceKind
from application.source_profile_catalog import DeclaredCatalogNode, DeclaredSourceProfile

PYATEROCHKA_LIVE_SOURCE_PROFILE_ID = "pyaterochka-live-catalog"


class _ActivationRequiredBrowserRunner:
    async def collect(self, request: CollectionRequest) -> dict[str, Any]:
        del request
        raise ApplicationContractError(
            "BROWSER_SOURCE_ACTIVATION_REQUIRED",
            "BROWSER_SOURCE_ACTIVATION_REQUIRED: Live browser collection requires separate approval and activation.",
        )


def build_offline_pyaterochka_browser_registration() -> BrowserSourceRegistration:
    """Build the exact visible-but-inactive Pyaterochka browser registration."""
    return BrowserSourceRegistration(
        declared_profile=DeclaredSourceProfile(
            source_profile_id=PYATEROCHKA_LIVE_SOURCE_PROFILE_ID,
            display_name="Пятёрочка — live (требуется активация)",
            source_kind=SourceKind.BROWSER,
            adapter_id=BrowserSourceAdapter.adapter_id,
            adapter_version=BrowserSourceAdapter.adapter_version,
            fixed_source_locator="https://5ka.ru",
            catalog_node_options=(
                DeclaredCatalogNode("pyaterochka-fish", "Рыба"),
                DeclaredCatalogNode("pyaterochka-seafood", "Морепродукты"),
                DeclaredCatalogNode("pyaterochka-cutlets-mince", "Котлеты и фарш"),
                DeclaredCatalogNode("pyaterochka-caviar-snacks", "Икра и закуски"),
                DeclaredCatalogNode("pyaterochka-beer-wine-energy", "Пиво, вино, энергетики"),
                DeclaredCatalogNode("pyaterochka-nonalcoholic-wine", "Безалкогольное вино"),
            ),
        ),
        adapter=BrowserSourceAdapter(_ActivationRequiredBrowserRunner()),
    )
