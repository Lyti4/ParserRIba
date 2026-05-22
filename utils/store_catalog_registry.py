"""Registry for store catalog export backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Literal
from urllib.parse import urlparse

from utils.category_intents import CategoryIntentResolver, get_category_intent_resolver
from utils.pyaterochka_catalog_capture import capture_pyaterochka_catalog

DiscoverFunc = Callable[..., Awaitable[dict]]
KnownStoreStatus = Literal["discovery_only", "runtime_ready"]

PYATEROCHKA_FISH_DEFAULT_CATEGORY = "Рыба"
PYATEROCHKA_WINE_DEFAULT_CATEGORY = "Вино"


@dataclass(frozen=True)
class StoreExportBackend:
    """Store-specific backend for a catalog export intent."""

    shop: str
    intent: str
    default_category: str
    discover_func: DiscoverFunc
    resolve_categories: CategoryIntentResolver
    site_hosts: tuple[str, ...]


@dataclass(frozen=True)
class KnownStoreSite:
    """Known store site profile used by generic onboarding."""

    shop: str
    site_hosts: tuple[str, ...]
    onboarding_status: KnownStoreStatus
    kb_shop: str | None = None
    export_backend_shop: str | None = None


def resolve_catalog_research_site(site_url: str, shop: str | None = None) -> KnownStoreSite | None:
    """Resolve one research target by explicit shop hint or URL match."""
    normalized_shop = str(shop or "").strip().casefold()
    if normalized_shop:
        try:
            return get_known_store_site(normalized_shop)
        except ValueError:
            return None
    return match_known_store_site(site_url)


def get_store_export_backend(shop: str, intent: str = "fish_catalog") -> StoreExportBackend:
    """Return backend configuration for one supported store and intent."""
    normalized_shop = str(shop or "").strip().casefold()
    normalized_intent = str(intent or "").strip().casefold()
    if normalized_shop == "pyaterochka":
        if normalized_intent == "fish_catalog":
            return StoreExportBackend(
                shop="pyaterochka",
                intent="fish_catalog",
                default_category=PYATEROCHKA_FISH_DEFAULT_CATEGORY,
                discover_func=capture_pyaterochka_catalog,
                resolve_categories=get_category_intent_resolver("fish_catalog"),
                site_hosts=("5ka.ru", "www.5ka.ru"),
            )
        if normalized_intent == "wine_catalog":
            return StoreExportBackend(
                shop="pyaterochka",
                intent="wine_catalog",
                default_category=PYATEROCHKA_WINE_DEFAULT_CATEGORY,
                discover_func=capture_pyaterochka_catalog,
                resolve_categories=get_category_intent_resolver("wine_catalog"),
                site_hosts=("5ka.ru", "www.5ka.ru"),
            )
    raise ValueError(f"Unsupported store export backend: {shop}/{intent}")


def get_known_store_site(shop: str) -> KnownStoreSite:
    """Return known site profile for one store."""
    normalized = str(shop or "").strip().casefold()
    if normalized == "pyaterochka":
        return KnownStoreSite(
            shop="pyaterochka",
            site_hosts=("5ka.ru", "www.5ka.ru"),
            onboarding_status="runtime_ready",
            kb_shop="pyaterochka",
            export_backend_shop="pyaterochka",
        )
    if normalized == "verny":
        return KnownStoreSite(
            shop="verny",
            site_hosts=("verno-info.ru", "www.verno-info.ru"),
            onboarding_status="discovery_only",
            kb_shop="verny",
            export_backend_shop=None,
        )
    if normalized == "auchan":
        return KnownStoreSite(
            shop="auchan",
            site_hosts=("auchan.ru", "www.auchan.ru"),
            onboarding_status="discovery_only",
            kb_shop="auchan",
            export_backend_shop=None,
        )
    if normalized == "perekrestok":
        return KnownStoreSite(
            shop="perekrestok",
            site_hosts=("perekrestok.ru", "www.perekrestok.ru"),
            onboarding_status="discovery_only",
            kb_shop="perekrestok",
            export_backend_shop=None,
        )
    if normalized == "metro":
        return KnownStoreSite(
            shop="metro",
            site_hosts=("metro-cc.ru", "www.metro-cc.ru", "online.metro-cc.ru"),
            onboarding_status="discovery_only",
            kb_shop=None,
            export_backend_shop=None,
        )
    if normalized == "krasnoeibeloe":
        return KnownStoreSite(
            shop="krasnoeibeloe",
            site_hosts=("krasnoeibeloe.ru", "www.krasnoeibeloe.ru"),
            onboarding_status="discovery_only",
            kb_shop=None,
            export_backend_shop=None,
        )
    if normalized == "azbukavkusa":
        return KnownStoreSite(
            shop="azbukavkusa",
            site_hosts=("av.ru", "www.av.ru"),
            onboarding_status="discovery_only",
            kb_shop=None,
            export_backend_shop=None,
        )
    raise ValueError(f"Unsupported known store site: {shop}")


def match_known_store_site(site_url: str) -> KnownStoreSite | None:
    """Match a known store site by site URL host."""
    host = urlparse(site_url).netloc.casefold()
    if not host:
        return None
    for shop in ("pyaterochka", "verny", "auchan", "perekrestok", "metro", "krasnoeibeloe", "azbukavkusa"):
        profile = get_known_store_site(shop)
        if host in profile.site_hosts:
            return profile
    return None


def match_store_export_backend(site_url: str, intent: str = "fish_catalog") -> StoreExportBackend | None:
    """Match a known store backend by site URL host."""
    profile = match_known_store_site(site_url)
    if not profile or not profile.export_backend_shop:
        return None
    return get_store_export_backend(profile.export_backend_shop, intent)
