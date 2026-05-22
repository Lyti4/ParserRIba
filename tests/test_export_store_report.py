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
                name="Р’РёРЅРѕ Free Feather Chardonnay Р±РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РїРѕР»СѓСЃР»Р°РґРєРѕРµ Р±РµР»РѕРµ 750РјР»",
                brand="Free Feather",
                price=699.99,
                image_url="https://img.example/4225897.webp",
                product_link="https://5ka.ru/product/vino-free-feather--4225897/",
                category="Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ",
                subcategory="РўРёС…РѕРµ",
                in_stock=True,
                raw_data={
                    "supplier": "Free Feather",
                    "alcohol_type": "Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ",
                },
            ),
            Product(
                id="4225898",
                name="Р’РёРЅРѕ OddBird Spumante Р±РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ Р±РµР»РѕРµ 750РјР»",
                brand="OddBird",
                price=899.99,
                image_url="https://img.example/4225898.webp",
                product_link="https://5ka.ru/product/vino-oddbird--4225898/",
                category="Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ",
                subcategory="РРіСЂРёСЃС‚РѕРµ",
                in_stock=True,
                raw_data={
                    "supplier": "OddBird",
                    "alcohol_type": "Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ",
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
            "Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ",
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
    assert payload["categories"] == ["Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ"]
    assert payload["report_summary"]["products_count"] == 1
    assert payload["report_summary"]["supplier_counts"] == {"Free Feather": 1}
    assert Path(payload["report_path"]).exists()
    assert Path(payload["report_path"]).name == "wine_free_feather.xlsx"
