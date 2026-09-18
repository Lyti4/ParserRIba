import json
import subprocess
import sys
from pathlib import Path

from models.schemas import Product
from utils.product_storage import ProductStorage


def test_export_store_report_cli_builds_filtered_excel(tmp_path: Path) -> None:
    storage = ProductStorage(tmp_path / "products.db")
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
            Product(
                id="4225898",
                name="\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 OddBird Spumante \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                brand="OddBird",
                price=899.99,
                image_url="https://img.example/4225898.webp",
                product_link="https://5ka.ru/product/vino-oddbird--4225898/",
                category="\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
                subcategory="\u0420\u0098\u0420\u0456\u0421\u0402\u0420\u0451\u0421\u0403\u0421\u201a\u0420\u0455\u0420\u00b5",
                in_stock=True,
                raw_data={
                    "supplier": "OddBird",
                    "alcohol_type": "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5",
                },
            ),
        ],
    )
    output_dir = tmp_path / "reports"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_store_report.py",
            "--shop",
            "pyaterochka",
            "--intent",
            "wine_catalog",
            "--category",
            "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
            "--supplier",
            "Free Feather",
            "--output-name",
            "wine_free_feather",
            "--db-path",
            str(tmp_path / "products.db"),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)
    assert payload["products_count"] == 1
    assert payload["categories"] == ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"]
    assert payload["report_summary"]["products_count"] == 1
    assert payload["report_summary"]["supplier_counts"] == {"Free Feather": 1}
    assert Path(payload["report_path"]).exists()
    assert Path(payload["report_path"]).name == "wine_free_feather.xlsx"
