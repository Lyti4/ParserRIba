"""Generic store catalog export entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.kb_loader import KBLoader
from utils.store_catalog_registry import get_store_export_backend
from utils.store_export_runtime import build_store_export_payload, write_store_export


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export store catalog products")
    parser.add_argument("--shop", default="pyaterochka")
    parser.add_argument("--intent", default="fish_catalog")
    parser.add_argument("--category", default="")
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
    backend = get_store_export_backend(args.shop, args.intent)
    if args.intent != backend.intent:
        raise ValueError(f"Unsupported intent for {backend.shop}: {args.intent}")
    kb = KBLoader(str(ROOT_DIR / "knowledge_base")).load_shop(backend.shop)
    export_payload = asyncio.run(
        build_store_export_payload(
            backend=backend,
            category_name=args.category or backend.default_category,
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
