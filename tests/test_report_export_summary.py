from pathlib import Path

from models.report_request import ExportSelection, ProductFilter, ReportRequest
from models.schemas import Product
from utils.product_storage import ProductStorage
from utils.storage_report_builder import build_excel_report_from_storage


def test_build_excel_report_from_storage_includes_report_summary(tmp_path: Path) -> None:
    storage = ProductStorage(tmp_path / "products.db")
    storage.save_products(
        "pyaterochka",
        [
            Product(
                id="wine-1",
                name="Р’РёРЅРѕ Free Feather Chardonnay Р±РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РїРѕР»СѓСЃР»Р°РґРєРѕРµ Р±РµР»РѕРµ 750РјР»",
                brand="Free Feather",
                price=699.99,
                image_url="https://img.example/wine-1.webp",
                product_link="https://5ka.ru/product/wine--wine-1/",
                category="Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ",
                subcategory="РўРёС…РѕРµ",
                in_stock=True,
                raw_data={
                    "supplier": "Free Feather",
                    "alcohol_type": "Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ",
                },
            ),
            Product(
                id="wine-2",
                name="Р’РёРЅРѕ OddBird Spumante Р±РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ Р±РµР»РѕРµ 750РјР»",
                brand="OddBird",
                price=899.99,
                image_url="https://img.example/wine-2.webp",
                product_link="https://5ka.ru/product/wine--wine-2/",
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

    result = build_excel_report_from_storage(
        ReportRequest(
            selection=ExportSelection(
                shop="pyaterochka",
                intent="wine_catalog",
                categories=["Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ"],
            ),
            filters=ProductFilter(suppliers=["Free Feather"]),
            output_name="wine_supplier_report",
        ),
        db_path=tmp_path / "products.db",
        output_dir=tmp_path,
    )

    assert result.products_count == 1
    assert result.report_summary["products_count"] == 1
    assert result.report_summary["categories"] == ["Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ"]
    assert result.report_summary["category_counts"] == {"Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ РІРёРЅРѕ": 1}
    assert result.report_summary["supplier_counts"] == {"Free Feather": 1}
    assert result.report_summary["brand_counts"] == {"Free Feather": 1}
    assert result.report_summary["wine_breakdown"]["style_counts"] == {"РўРёС…РѕРµ": 1}
    assert result.report_summary["wine_breakdown"]["alcohol_type_counts"] == {
        "Р‘РµР·Р°Р»РєРѕРіРѕР»СЊРЅРѕРµ": 1
    }
