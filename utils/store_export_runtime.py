"""Shared runtime helpers for store catalog export."""

from __future__ import annotations

import json
import inspect
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from models.schemas import Product
from scripts.discover_pyaterochka_api import OUTPUT_DIR
from utils.excel_report import write_products_excel_report
from utils.export_summary import build_export_summary
from utils.product_storage import ProductStorage
from utils.pyaterochka_export import build_products_from_result, filter_products_for_intent, merge_products
from utils.run_manifest import build_store_export_manifest, write_run_manifest
from utils.store_catalog_registry import StoreExportBackend, DiscoverFunc


async def build_store_export_payload(
    *,
    backend: StoreExportBackend,
    category_name: str,
    attempts: int,
    listen_seconds: int,
    headless: bool | str | None,
    manual_wait: bool,
    kb_categories: dict[str, str],
    category_url: str = "",
    discover_func: DiscoverFunc | None = None,
    expand_intent: bool = True,
) -> dict[str, Any]:
    """Build a normalized export payload for one store backend."""
    runner = discover_func or backend.discover_func
    target_categories = (
        backend.resolve_categories(category_name, kb_categories)
        if expand_intent
        else [str(category_name or backend.default_category).strip() or backend.default_category]
    )
    last_result: dict[str, Any] | None = None
    products: list[Product] = []
    category_results: list[dict[str, Any]] = []
    for attempt_number in range(1, attempts + 1):
        category_results = []
        batch_products: list[Product] = []
        for target_category in target_categories:
            target_category_url = str(category_url or "").strip() if not expand_intent else str(kb_categories.get(target_category, "")).strip()
            result = await _run_discover_func(
                runner,
                category_name=target_category,
                category_url=target_category_url,
                listen_seconds=listen_seconds,
                headless=headless,
                manual_wait=manual_wait,
            )
            category_results.append(result)
            last_result = result
            batch_products.extend(build_products_from_result(result))
        products = filter_products_for_intent(merge_products(batch_products), backend.intent)
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
        "export_summary": build_export_summary(
            {
                "intent": backend.intent,
                "categories": target_categories,
                "attempt": {
                    "status": "ok" if products else "empty",
                    "reason": "product_payload_captured" if products else "no_product_payload",
                },
                "products_count": len(products),
                "products": [product.model_dump(mode="json") for product in products],
            }
        ),
    }


async def _run_discover_func(
    runner: DiscoverFunc,
    *,
    category_name: str,
    category_url: str,
    listen_seconds: int,
    headless: bool | str | None,
    manual_wait: bool,
) -> dict[str, Any]:
    """Call a discover function while keeping older test doubles compatible."""
    kwargs: dict[str, Any] = {
        "category_name": category_name,
        "listen_seconds": listen_seconds,
        "headless": headless,
        "manual_wait": manual_wait,
    }
    if category_url and _accepts_keyword(runner, "category_url"):
        kwargs["category_url"] = category_url
    return await runner(**kwargs)


def _accepts_keyword(callable_obj: DiscoverFunc, keyword: str) -> bool:
    """Return whether a callable accepts a named keyword or arbitrary kwargs."""
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return True
    if keyword in signature.parameters:
        return True
    return any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())


def write_store_export(
    payload: dict[str, Any],
    output_dir: Path | str = OUTPUT_DIR,
    *,
    task_name: str = "store_catalog_export",
) -> tuple[Path, Path]:
    """Write exported products payload to JSON and SQLite."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    shop = str(payload.get("shop") or "store")
    path = target_dir / f"{shop}_products.json"
    db_path = target_dir / "products.db"
    manifest_path = target_dir / f"{shop}_run_manifest.json"
    storage = ProductStorage(db_path)
    products = [Product(**item) for item in (payload.get("products") or []) if isinstance(item, dict)]
    storage.initialize()
    storage.save_products(shop, products)
    actual_excel_path = write_products_excel_report(
        products,
        shop=shop,
        output_dir=target_dir,
        exported_at=str(payload.get("exported_at") or ""),
    )
    payload["export_summary"] = build_export_summary(payload)
    payload["db_path"] = str(db_path)
    payload["excel_path"] = str(actual_excel_path)
    payload["stored_products_count"] = len(products)
    manifest = build_store_export_manifest(
        payload=payload,
        export_path=path,
        db_path=db_path,
        manifest_path=manifest_path,
        excel_path=actual_excel_path,
        task_name=task_name,
    )
    write_run_manifest(manifest, manifest_path)
    payload["run_manifest_path"] = str(manifest_path)
    payload["run_manifest"] = manifest.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, db_path
