"""Generic store catalog export entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models.schemas import Product
from scripts.discover_pyaterochka_api import DEFAULT_CATEGORY, OUTPUT_DIR
from utils.category_intents import resolve_fish_catalog_categories
from utils.kb_loader import KBLoader
from utils.product_storage import ProductStorage
from utils.pyaterochka_catalog_capture import capture_pyaterochka_catalog
from utils.pyaterochka_export import build_products_from_result, merge_products

DiscoverFunc = Callable[..., Awaitable[dict[str, Any]]]
ResolveCategoriesFunc = Callable[[str, dict[str, str] | None], list[str]]


@dataclass(frozen=True)
class StoreExportBackend:
    """Store-specific backend for a catalog export intent."""

    shop: str
    intent: str
    default_category: str
    discover_func: DiscoverFunc
    resolve_categories: ResolveCategoriesFunc


def get_store_export_backend(shop: str) -> StoreExportBackend:
    """Return backend configuration for one supported store."""
    normalized = str(shop or "").strip().casefold()
    if normalized == "pyaterochka":
        return StoreExportBackend(
            shop="pyaterochka",
            intent="fish_catalog",
            default_category=DEFAULT_CATEGORY,
            discover_func=capture_pyaterochka_catalog,
            resolve_categories=resolve_fish_catalog_categories,
        )
    raise ValueError(f"Unsupported store export backend: {shop}")


async def build_store_export_payload(
    *,
    backend: StoreExportBackend,
    category_name: str,
    attempts: int,
    listen_seconds: int,
    headless: bool | str | None,
    manual_wait: bool,
    kb_categories: dict[str, str],
    discover_func: DiscoverFunc | None = None,
) -> dict[str, Any]:
    """Build a normalized export payload for one store backend."""
    runner = discover_func or backend.discover_func
    target_categories = backend.resolve_categories(category_name, kb_categories)
    last_result: dict[str, Any] | None = None
    products: list[Product] = []
    category_results: list[dict[str, Any]] = []
    for attempt_number in range(1, attempts + 1):
        category_results = []
        batch_products: list[Product] = []
        for target_category in target_categories:
            result = await runner(
                category_name=target_category,
                listen_seconds=listen_seconds,
                headless=headless,
                manual_wait=manual_wait,
            )
            category_results.append(result)
            last_result = result
            batch_products.extend(build_products_from_result(result))
        products = merge_products(batch_products)
        if products:
            break
        logger.warning(
            "{} export attempt {} returned no ready products: {}",
            backend.shop,
            attempt_number,
            ", ".join(str((item.get("attempt") or {}).get("reason", "unknown")) for item in category_results),
        )
    if last_result is None:
        raise RuntimeError(f"{backend.shop} export did not run")
    category_urls = {
        str(item.get("category") or ""): str(item.get("category_url") or "")
        for item in category_results
        if item.get("category") and item.get("category_url")
    }
    return {
        "shop": backend.shop,
        "intent": backend.intent,
        "category": category_name,
        "category_url": last_result.get("category_url", ""),
        "categories": target_categories,
        "category_urls": category_urls,
        "attempts_requested": attempts,
        "attempts_used": attempt_number,
        "attempt": {
            "status": "ok" if products else "empty",
            "reason": "product_payload_captured" if products else "no_product_payload",
            "categories": [
                {
                    "name": str(item.get("category") or ""),
                    "status": str((item.get("attempt") or {}).get("status") or ""),
                    "reason": str((item.get("attempt") or {}).get("reason") or ""),
                }
                for item in category_results
            ],
        },
        "products_count": len(products),
        "products": [product.model_dump(mode="json") for product in products],
        "exported_at": datetime.now().isoformat(timespec="seconds"),
    }


def write_store_export(payload: dict[str, Any], output_dir: Path | str = OUTPUT_DIR) -> tuple[Path, Path]:
    """Write exported products payload to JSON and SQLite."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    shop = str(payload.get("shop") or "store")
    path = target_dir / f"{shop}_products.json"
    db_path = target_dir / "products.db"
    storage = ProductStorage(db_path)
    products = [Product(**item) for item in (payload.get("products") or []) if isinstance(item, dict)]
    storage.save_products(shop, products)
    payload["db_path"] = str(db_path)
    payload["stored_products_count"] = len(products)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, db_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export store catalog products")
    parser.add_argument("--shop", default="pyaterochka")
    parser.add_argument("--intent", default="fish_catalog")
    parser.add_argument("--category", default=DEFAULT_CATEGORY)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--listen-seconds", type=int, default=15)
    parser.add_argument("--manual-wait", action="store_true", dest="manual_wait")
    parser.add_argument("--no-manual-wait", action="store_false", dest="manual_wait")
    parser.add_argument("--headless", action="store_true", default=None)
    parser.add_argument("--no-headless", action="store_false", dest="headless")
    parser.set_defaults(manual_wait=False)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    backend = get_store_export_backend(args.shop)
    if args.intent != backend.intent:
        raise ValueError(f"Unsupported intent for {backend.shop}: {args.intent}")
    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop(backend.shop)
    export_payload = asyncio.run(
        build_store_export_payload(
            backend=backend,
            category_name=args.category,
            attempts=args.attempts,
            listen_seconds=args.listen_seconds,
            headless=args.headless,
            manual_wait=args.manual_wait,
            kb_categories=kb.categories,
        )
    )
    output_path, db_path = write_store_export(export_payload)
    logger.info("{} products export saved: {}", backend.shop, output_path)
    logger.info("{} products sqlite saved: {}", backend.shop, db_path)
