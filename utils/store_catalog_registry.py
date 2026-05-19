"""Registry for store catalog export backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable
from urllib.parse import urlparse

from scripts.discover_pyaterochka_api import DEFAULT_CATEGORY
from utils.category_intents import CategoryIntentResolver, get_category_intent_resolver
from utils.pyaterochka_catalog_capture import capture_pyaterochka_catalog

DiscoverFunc = Callable[..., Awaitable[dict]]


@dataclass(frozen=True)
class StoreExportBackend:
    """Store-specific backend for a catalog export intent."""

    shop: str
    intent: str
    default_category: str
    discover_func: DiscoverFunc
    resolve_categories: CategoryIntentResolver
    site_hosts: tuple[str, ...]


def get_store_export_backend(shop: str) -> StoreExportBackend:
    """Return backend configuration for one supported store."""
    normalized = str(shop or "").strip().casefold()
    if normalized == "pyaterochka":
        return StoreExportBackend(
            shop="pyaterochka",
            intent="fish_catalog",
            default_category=DEFAULT_CATEGORY,
            discover_func=capture_pyaterochka_catalog,
            resolve_categories=get_category_intent_resolver("fish_catalog"),
            site_hosts=("5ka.ru", "www.5ka.ru"),
        )
    raise ValueError(f"Unsupported store export backend: {shop}")


def match_store_export_backend(site_url: str) -> StoreExportBackend | None:
    """Match a known store backend by site URL host."""
    host = urlparse(site_url).netloc.casefold()
    if not host:
        return None
    for shop in ("pyaterochka",):
        backend = get_store_export_backend(shop)
        if host in backend.site_hosts:
            return backend
    return None
