"""Run a registered local task and return its run manifest."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.local_task_registry import list_local_tasks, run_local_task


def _configure_stdio() -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local ParserRIba task")
    parser.add_argument("--task", default="")
    parser.add_argument("--input-json", default="{}")
    parser.add_argument("--input-file", default="")
    parser.add_argument("--input-stdin", action="store_true", dest="input_stdin")
    parser.add_argument("--input-base64", default="")
    parser.add_argument("--list", action="store_true", dest="list_tasks")
    parser.add_argument("--summary", action="store_true", dest="show_summary")
    return parser.parse_args(argv)


def _render_summary(manifest: dict) -> str:
    lines = [
        f"Task: {manifest.get('task_name', '')}",
        f"Status: {manifest.get('status', '')}",
        f"Shop: {manifest.get('shop', '')}",
        f"Intent: {manifest.get('intent', '')}",
    ]
    summary = manifest.get("summary") or {}
    products_count = summary.get("products_count")
    if products_count is not None:
        lines.append(f"Products: {products_count}")
    categories = summary.get("categories")
    if isinstance(categories, list) and categories:
        lines.append(f"Categories: {', '.join(str(item) for item in categories)}")
    selected_categories = summary.get("selected_categories")
    if isinstance(selected_categories, list) and selected_categories:
        lines.append(
            f"Selected categories: {', '.join(str(item) for item in selected_categories)}"
        )
    filters_applied = summary.get("filters_applied")
    if isinstance(filters_applied, dict):
        suppliers = filters_applied.get("suppliers")
        if isinstance(suppliers, list) and suppliers:
            lines.append(f"Suppliers: {', '.join(str(item) for item in suppliers)}")
        brands = filters_applied.get("brands")
        if isinstance(brands, list) and brands:
            lines.append(f"Brands: {', '.join(str(item) for item in brands)}")
    artifact_paths = manifest.get("artifact_paths") or {}
    if isinstance(artifact_paths, dict):
        excel_path = artifact_paths.get("excel_path")
        if excel_path:
            lines.append(f"Report: {excel_path}")
    available_filter_counts = summary.get("available_filter_counts")
    if isinstance(available_filter_counts, dict):
        for label, field_name in (
            ("Suppliers", "suppliers"),
            ("Brands", "brands"),
            ("Wine styles", "wine_styles"),
        ):
            counts = available_filter_counts.get(field_name)
            if isinstance(counts, dict) and counts:
                parts = [f"{key}={value}" for key, value in counts.items()]
                lines.append(f"{label}: {', '.join(parts)}")
    report_summary = summary.get("report_summary")
    if isinstance(report_summary, dict):
        for label, field_name in (
            ("Category counts", "category_counts"),
            ("Supplier counts", "supplier_counts"),
            ("Brand counts", "brand_counts"),
        ):
            counts = report_summary.get(field_name)
            if isinstance(counts, dict) and counts:
                parts = [f"{key}={value}" for key, value in counts.items()]
                lines.append(f"{label}: {', '.join(parts)}")
        wine_breakdown = report_summary.get("wine_breakdown")
        if isinstance(wine_breakdown, dict):
            for label, field_name in (
                ("Report wine styles", "style_counts"),
                ("Report alcohol types", "alcohol_type_counts"),
                ("Report sugar classes", "sugar_class_counts"),
                ("Report colors", "color_counts"),
            ):
                counts = wine_breakdown.get(field_name)
                if isinstance(counts, dict) and counts:
                    parts = [f"{key}={value}" for key, value in counts.items()]
                    lines.append(f"{label}: {', '.join(parts)}")
    export_summary = summary.get("export_summary")
    if isinstance(export_summary, dict):
        wine_breakdown = export_summary.get("wine_breakdown")
        if isinstance(wine_breakdown, dict):
            style_counts = wine_breakdown.get("style_counts")
            if isinstance(style_counts, dict) and style_counts:
                parts = [f"{key}={value}" for key, value in style_counts.items()]
                lines.append(f"Wine styles: {', '.join(parts)}")
            alcohol_type_counts = wine_breakdown.get("alcohol_type_counts")
            if isinstance(alcohol_type_counts, dict) and alcohol_type_counts:
                parts = [f"{key}={value}" for key, value in alcohol_type_counts.items()]
                lines.append(f"Alcohol types: {', '.join(parts)}")
            sugar_class_counts = wine_breakdown.get("sugar_class_counts")
            if isinstance(sugar_class_counts, dict) and sugar_class_counts:
                parts = [f"{key}={value}" for key, value in sugar_class_counts.items()]
                lines.append(f"Sugar classes: {', '.join(parts)}")
            color_counts = wine_breakdown.get("color_counts")
            if isinstance(color_counts, dict) and color_counts:
                parts = [f"{key}={value}" for key, value in color_counts.items()]
                lines.append(f"Colors: {', '.join(parts)}")
    return "\n".join(lines)


if __name__ == "__main__":
    _configure_stdio()
    args = _parse_args()
    if args.list_tasks:
        sys.stdout.write(json.dumps({"tasks": list_local_tasks()}, ensure_ascii=False, indent=2))
        raise SystemExit(0)
    if args.input_file:
        task_input = json.loads(Path(args.input_file).read_text(encoding="utf-8-sig"))
    elif args.input_stdin:
        task_input = json.loads(sys.stdin.read())
    elif args.input_base64:
        decoded = base64.b64decode(args.input_base64).decode("utf-8")
        task_input = json.loads(decoded)
    else:
        task_input = json.loads(args.input_json)
    manifest = asyncio.run(run_local_task(args.task, task_input, root_dir=ROOT_DIR))
    if args.show_summary:
        sys.stderr.write(_render_summary(manifest.model_dump()) + "\n")
    sys.stdout.write(manifest.model_dump_json(indent=2))
