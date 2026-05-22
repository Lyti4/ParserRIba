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
            "categories": ["Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ"],
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
    assert "Categories: Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ" in rendered
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
            "categories": ["Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ"],
            "available_filter_counts": {
                "suppliers": {"Free Feather": 1, "OddBird": 1},
                "brands": {"Free Feather": 1, "OddBird": 1},
                "wine_styles": {"РРіСЂРёСЃС‚РѕРµ": 1, "РўРёС…РѕРµ": 1},
            },
        },
    }

    rendered = _render_summary(manifest)

    assert "Suppliers: Free Feather=1, OddBird=1" in rendered
    assert "Brands: Free Feather=1, OddBird=1" in rendered
    assert "Wine styles: РРіСЂРёСЃС‚РѕРµ=1, РўРёС…РѕРµ=1" in rendered


def test_render_summary_includes_report_summary_breakdown() -> None:
    manifest = {
        "task_name": "store_report_export",
        "status": "ok",
        "shop": "pyaterochka",
        "intent": "wine_catalog",
        "summary": {
            "products_count": 1,
            "categories": ["Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ"],
            "report_summary": {
                "products_count": 1,
                "categories": ["Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ"],
                "category_counts": {"Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ": 1},
                "supplier_counts": {"Free Feather": 1},
                "brand_counts": {"Free Feather": 1},
                "wine_breakdown": {
                    "style_counts": {"РўРёС…РѕРµ": 1},
                    "alcohol_type_counts": {"Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ": 1},
                    "sugar_class_counts": {"РџРѕР»СѓСЃР»Р°РґРєРѕРµ": 1},
                    "color_counts": {"Р‘РµР»РѕРµ": 1},
                },
            },
        },
    }

    rendered = _render_summary(manifest)

    assert "Category counts: Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ=1" in rendered
    assert "Supplier counts: Free Feather=1" in rendered
    assert "Brand counts: Free Feather=1" in rendered
    assert "Report wine styles: РўРёС…РѕРµ=1" in rendered
    assert "Report alcohol types: Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ=1" in rendered
    assert "Report sugar classes: РџРѕР»СѓСЃР»Р°РґРєРѕРµ=1" in rendered
    assert "Report colors: Р‘РµР»РѕРµ=1" in rendered
