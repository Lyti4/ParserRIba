from scripts.run_local_task import _render_summary


def test_render_summary_includes_report_export_details() -> None:
    manifest = {
        "task_name": "store_report_export",
        "status": "ok",
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "artifact_paths": {
            "excel_path": "C:/tmp/ParserRIba-clean/data/reports/wine_free_feather.xlsx",
        },
        "summary": {
            "products_count": 1,
            "categories": ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            "filters_applied": {
                "suppliers": ["Free Feather"],
                "brands": [],
                "categories": [],
                "min_price": None,
                "max_price": None,
                "in_stock": None,
                "wine_styles": [],
                "alcohol_types": [],
                "sugar_classes": [],
                "colors": [],
                "strict_missing": False,
            },
        },
    }

    rendered = _render_summary(manifest)

    assert "Task: store_report_export" in rendered
    assert "Products: 1" in rendered
    assert "Categories: \u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455" in rendered
    assert "Suppliers: Free Feather" in rendered
    assert "Report: C:/tmp/ParserRIba-clean/data/reports/wine_free_feather.xlsx" in rendered


def test_render_summary_includes_filter_option_counts() -> None:
    manifest = {
        "task_name": "store_report_filter_options",
        "status": "ok",
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "summary": {
            "products_count": 2,
            "categories": ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            "available_filter_counts": {
                "suppliers": {"Free Feather": 1, "OddBird": 1},
                "brands": {"Free Feather": 1, "OddBird": 1},
                "wine_styles": {"\u0420\u0098\u0420\u0456\u0421\u0402\u0420\u0451\u0421\u0403\u0421\u201a\u0420\u0455\u0420\u00b5": 1, "\u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5": 1},
            },
        },
    }

    rendered = _render_summary(manifest)

    assert "Suppliers: Free Feather=1, OddBird=1" in rendered
    assert "Brands: Free Feather=1, OddBird=1" in rendered
    assert "Subcategories: \u0420\u0098\u0420\u0456\u0421\u0402\u0420\u0451\u0421\u0403\u0421\u201a\u0420\u0455\u0420\u00b5=1, \u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5=1" in rendered


def test_render_summary_includes_report_summary_breakdown() -> None:
    manifest = {
        "task_name": "store_report_export",
        "status": "ok",
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "summary": {
            "products_count": 1,
            "categories": ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            "report_summary": {
                "products_count": 1,
                "categories": ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
                "category_counts": {"\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455": 1},
                "supplier_counts": {"Free Feather": 1},
                "brand_counts": {"Free Feather": 1},
                "wine_breakdown": {
                    "style_counts": {"\u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5": 1},
                    "alcohol_type_counts": {"\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5": 1},
                    "sugar_class_counts": {"\u0420\u045f\u0420\u0455\u0420\u00bb\u0421\u0453\u0421\u0403\u0420\u00bb\u0420\u00b0\u0420\u0491\u0420\u0454\u0420\u0455\u0420\u00b5": 1},
                    "color_counts": {"\u0420\u2018\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5": 1},
                },
            },
        },
    }

    rendered = _render_summary(manifest)

    assert "Category counts: \u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455=1" in rendered
    assert "Supplier counts: Free Feather=1" in rendered
    assert "Brand counts: Free Feather=1" in rendered
    assert "Report subcategories: \u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5=1" in rendered
    assert "Report alcohol types: \u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5=1" in rendered
    assert "Report sugar classes: \u0420\u045f\u0420\u0455\u0420\u00bb\u0421\u0453\u0421\u0403\u0420\u00bb\u0420\u00b0\u0420\u0491\u0420\u0454\u0420\u0455\u0420\u00b5=1" in rendered
    assert "Report colors: \u0420\u2018\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5=1" in rendered
