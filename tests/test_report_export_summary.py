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
                name="\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 Free Feather Chardonnay \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0457\u0420\u0455\u0420\u00bb\u0421\u0453\u0421\u0403\u0420\u00bb\u0420\u00b0\u0420\u0491\u0420\u0454\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                brand="Free Feather",
                price=699.99,
                image_url="https://img.example/wine-1.webp",
                product_link="https://5ka.ru/product/wine--wine-1/",
                category="\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
                subcategory="\u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5",
                in_stock=True,
                raw_data={
                    "supplier": "Free Feather",
                    "alcohol_type": "Безалкогольное",
                },
            ),
            Product(
                id="wine-2",
                name="\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 OddBird Spumante \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb",
                brand="OddBird",
                price=899.99,
                image_url="https://img.example/wine-2.webp",
                product_link="https://5ka.ru/product/wine--wine-2/",
                category="\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455",
                subcategory="\u0420\u0098\u0420\u0456\u0421\u0402\u0420\u0451\u0421\u0403\u0421\u201a\u0420\u0455\u0420\u00b5",
                in_stock=True,
                raw_data={
                    "supplier": "OddBird",
                    "alcohol_type": "Безалкогольное",
                },
            ),
        ],
    )

    result = build_excel_report_from_storage(
        ReportRequest(
            selection=ExportSelection(
                shop="pyaterochka",
                intent="wine_catalog",
                categories=["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            ),
            filters=ProductFilter(suppliers=["Free Feather"]),
            output_name="wine_supplier_report",
        ),
        db_path=tmp_path / "products.db",
        output_dir=tmp_path,
    )

    assert result.products_count == 1
    assert result.report_summary["products_count"] == 1
    assert result.report_summary["categories"] == ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"]
    assert result.report_summary["category_counts"] == {"\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455": 1}
    assert result.report_summary["supplier_counts"] == {"Free Feather": 1}
    assert result.report_summary["brand_counts"] == {"Free Feather": 1}
    assert result.report_summary["wine_breakdown"]["style_counts"] == {"\u0420\u045e\u0420\u0451\u0421\u2026\u0420\u0455\u0420\u00b5": 1}
    breakdown = result.report_summary["product_breakdown"]
    assert breakdown["alcohol_type_counts"] == {"Безалкогольное": 1}
    assert result.report_summary["wine_breakdown"] == breakdown
