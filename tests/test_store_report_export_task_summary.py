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
        ],
    )

    manifest = await run_local_task(
        "store_report_export",
        {
            "selection": {
                "shop": "pyaterochka",
                "intent": "wine_catalog",
                "categories": ["Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ"],
            },
            "filters": {"suppliers": ["Free Feather"]},
            "output_name": "wine_free_feather",
        },
        root_dir=tmp_path,
    )

    assert manifest.status == "ok"
    assert manifest.summary["report_summary"]["products_count"] == 1
    assert manifest.summary["report_summary"]["category_counts"] == {
        "Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ": 1
    }
    assert manifest.summary["report_summary"]["supplier_counts"] == {"Free Feather": 1}
    assert manifest.summary["report_summary"]["brand_counts"] == {"Free Feather": 1}
