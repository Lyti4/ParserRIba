from pathlib import Path

from models.schemas import Product
from utils.local_task_registry import run_local_task
from utils.product_storage import ProductStorage


async def test_store_report_export_task_includes_report_summary(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    storage = ProductStorage(tmp_path / "data" / "products.db")
    storage.save_products(
        "pyaterochka",
        [
            Product(
                id="4225897",
                name="\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 Free Feather Chardonnay \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0457\u0420\u0455\u0420\u00bb\u0421\u0453\u0421\u0403\u0420\u00bb\u0420\u00b0\u0420\u0491\u0420\u0454\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                brand="Free Feather",
                price=699.99,
                image_url="https://img.example/4225897.webp",
                product_link="https://5ka.ru/product/vino-free-feather--4225897/",
                category="\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
                subcategory="\u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5",
                in_stock=True,
                raw_data={
                    "supplier": "Free Feather",
                    "alcohol_type": "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5",
                },
            ),
        ],
    )

    manifest = await run_local_task(
        "store_report_export",
        {
            "selection": {
                "shop": "pyaterochka",
                "intent": "wine_catalog",
                "categories": ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            },
            "filters": {"suppliers": ["Free Feather"]},
            "output_name": "wine_free_feather",
        },
        root_dir=tmp_path,
    )

    assert manifest.status == "ok"
    assert manifest.summary["report_summary"]["products_count"] == 1
    assert manifest.summary["report_summary"]["category_counts"] == {
        "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455": 1
    }
    assert manifest.summary["report_summary"]["supplier_counts"] == {"Free Feather": 1}
    assert manifest.summary["report_summary"]["brand_counts"] == {"Free Feather": 1}
