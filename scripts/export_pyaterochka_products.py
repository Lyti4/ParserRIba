"""Retry Pyaterochka discovery and export normalized products."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models.schemas import Product
from scripts.discover_pyaterochka_api import DEFAULT_CATEGORY, OUTPUT_DIR
from utils.kb_loader import KBLoader
from utils.pyaterochka_catalog_capture import capture_pyaterochka_catalog
from utils.pyaterochka_export import (
    build_products_from_discovery_result,
    build_products_from_product_items,
    build_products_from_result,
    extract_product_items_from_payload,
    resolve_export_category_names,
)
from utils.store_catalog_registry import get_store_export_backend
from utils.store_export_runtime import build_store_export_payload, write_store_export

DiscoverFunc = Callable[..., Awaitable[dict[str, Any]]]


async def export_pyaterochka_products(
    *,
    category_name: str = DEFAULT_CATEGORY,
    attempts: int = 3,
    listen_seconds: int = 15,
    headless: bool | str | None = None,
    manual_wait: bool = False,
    discover_func: DiscoverFunc = capture_pyaterochka_catalog,
) -> dict[str, Any]:
    """Retry discovery until products are captured and return export payload."""
    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop("pyaterochka")
    backend = get_store_export_backend("pyaterochka")
    return await build_store_export_payload(
        backend=backend,
        category_name=category_name,
        attempts=attempts,
        listen_seconds=listen_seconds,
        headless=headless,
        manual_wait=manual_wait,
        kb_categories=kb.categories,
        discover_func=discover_func,
    )


def write_products_export(payload: dict[str, Any], output_dir: Path | str = OUTPUT_DIR) -> tuple[Path, Path]:
    """Write exported products payload to JSON and SQLite."""
    return write_store_export(payload, output_dir)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Pyaterochka products after successful discovery")
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
    export_payload = asyncio.run(
        export_pyaterochka_products(
            category_name=args.category,
            attempts=args.attempts,
            listen_seconds=args.listen_seconds,
            headless=args.headless,
            manual_wait=args.manual_wait,
        )
    )
    output_path, db_path = write_products_export(export_payload)
    logger.info("Pyaterochka products export saved: {}", output_path)
    logger.info("Pyaterochka products sqlite saved: {}", db_path)
