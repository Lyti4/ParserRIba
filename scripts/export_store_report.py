"""Build a filtered Excel report from local SQLite product storage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models.report_request import ExportSelection, ProductFilter, ReportRequest
from utils.storage_report_builder import build_excel_report_from_storage


def _configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a filtered store Excel report from SQLite")
    parser.add_argument("--shop", required=True)
    parser.add_argument("--intent", default="fish_catalog")
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--product-id", action="append", default=[])
    parser.add_argument("--supplier", action="append", default=[])
    parser.add_argument("--brand", action="append", default=[])
    parser.add_argument("--wine-style", action="append", default=[])
    parser.add_argument("--alcohol-type", action="append", default=[])
    parser.add_argument("--sugar-class", action="append", default=[])
    parser.add_argument("--color", action="append", default=[])
    parser.add_argument("--min-price", type=float, default=None)
    parser.add_argument("--max-price", type=float, default=None)
    parser.add_argument("--in-stock", action="store_true", dest="in_stock_only")
    parser.add_argument("--strict-missing", action="store_true")
    parser.add_argument("--output-name", default="")
    parser.add_argument("--db-path", default=str(ROOT_DIR / "data" / "products.db"))
    parser.add_argument("--output-dir", default=str(ROOT_DIR / "data" / "reports"))
    return parser.parse_args(argv)


def _build_request(args: argparse.Namespace) -> ReportRequest:
    return ReportRequest(
        selection=ExportSelection(
            shop=args.shop,
            intent=args.intent,
            categories=list(args.category or []),
            selected_product_ids=list(args.product_id or []),
        ),
        filters=ProductFilter(
            suppliers=list(args.supplier or []),
            brands=list(args.brand or []),
            min_price=args.min_price,
            max_price=args.max_price,
            in_stock=True if args.in_stock_only else None,
            wine_styles=list(args.wine_style or []),
            alcohol_types=list(args.alcohol_type or []),
            sugar_classes=list(args.sugar_class or []),
            colors=list(args.color or []),
            strict_missing=bool(args.strict_missing),
        ),
        output_name=args.output_name,
    )


if __name__ == "__main__":
    _configure_stdio()
    parsed = _parse_args()
    request = _build_request(parsed)
    result = build_excel_report_from_storage(
        request,
        db_path=parsed.db_path,
        output_dir=parsed.output_dir,
    ).to_model()
    sys.stdout.write(result.model_dump_json(indent=2))
