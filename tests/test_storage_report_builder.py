from pathlib import Path

from openpyxl import load_workbook

from models.report_request import ExportSelection, ProductFilter, ReportRequest
from models.schemas import Product
from utils.product_storage import ProductStorage
from utils.storage_report_builder import (
    build_excel_report_from_storage,
    build_report_filter_options,
)


def test_build_excel_report_from_storage_filters_by_supplier(tmp_path: Path) -> None:
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
    request = ReportRequest(
        selection=ExportSelection(
            shop="pyaterochka",
            intent="wine_catalog",
            categories=["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
        ),
        filters=ProductFilter(suppliers=["Free Feather"]),
        output_name="wine_supplier_report",
    )

    result = build_excel_report_from_storage(
        request,
        db_path=tmp_path / "products.db",
        output_dir=tmp_path,
    )

    assert result.products_count == 1
    assert result.categories == ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"]
    assert result.report_path.exists()

    workbook = load_workbook(result.report_path, read_only=True)
    assert workbook.sheetnames == ["Сводка", "\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406"]
    sheet = workbook["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406"]
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[1][3] == "\u0420\u2019\u0420\u0451\u0420\u0405\u0420\u0455 Free Feather Chardonnay \u0420\u00b1\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0457\u0420\u0455\u0420\u00bb\u0421\u0453\u0421\u0403\u0420\u00bb\u0420\u00b0\u0420\u0491\u0420\u0454\u0420\u0455\u0420\u00b5 \u0420\u00b1\u0420\u00b5\u0420\u00bb\u0420\u0455\u0420\u00b5 750\u0420\u0458\u0420\u00bb"


def test_build_excel_report_from_storage_splits_fish_and_wine_requests(tmp_path: Path) -> None:
    storage = ProductStorage(tmp_path / "products.db")
    storage.save_products(
        "pyaterochka",
        [
            Product(
                id="fish-1",
                name="\u0420\u045e\u0421\u0402\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0 \u0420\u00b0\u0421\u201a\u0420\u00bb\u0420\u00b0\u0420\u0405\u0421\u201a\u0420\u0451\u0421\u2021\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0\u0421\u040f \u0421\u0403\u0421\u201a\u0420\u00b5\u0420\u2116\u0420\u0454 \u0420\u00b7\u0420\u00b0\u0420\u0458\u0420\u0455\u0421\u0402\u0420\u0455\u0420\u00b6\u0420\u00b5\u0420\u0405\u0420\u0405\u0421\u2039\u0420\u2116 600\u0420\u0456",
                price=999.99,
                image_url="https://img.example/fish-1.webp",
                product_link="https://5ka.ru/product/fish--fish-1/",
                category="\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0",
                in_stock=True,
            ),
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
                raw_data={"alcohol_type": "Безалкогольное"},
            ),
        ],
    )

    fish_result = build_excel_report_from_storage(
        ReportRequest(
            selection=ExportSelection(
                shop="pyaterochka",
                intent="fish_catalog",
                categories=["\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0"],
            ),
            output_name="fish_report",
        ),
        db_path=tmp_path / "products.db",
        output_dir=tmp_path,
    )
    wine_result = build_excel_report_from_storage(
        ReportRequest(
            selection=ExportSelection(
                shop="pyaterochka",
                intent="wine_catalog",
                categories=["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            ),
            output_name="wine_report",
        ),
        db_path=tmp_path / "products.db",
        output_dir=tmp_path,
    )

    assert fish_result.products_count == 1
    assert wine_result.products_count == 1
    assert fish_result.report_path.name == "fish_report.xlsx"
    assert wine_result.report_path.name == "wine_report.xlsx"


def test_build_excel_report_from_storage_preserves_cyrillic_output_name(tmp_path: Path) -> None:
    storage = ProductStorage(tmp_path / "products.db")
    storage.save_products(
        "pyaterochka",
        [
            Product(
                id="fish-1",
                name="\u0420\u045e\u0421\u0402\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0 \u0420\u00b0\u0421\u201a\u0420\u00bb\u0420\u00b0\u0420\u0405\u0421\u201a\u0420\u0451\u0421\u2021\u0420\u00b5\u0421\u0403\u0420\u0454\u0420\u00b0\u0421\u040f \u0421\u0403\u0421\u201a\u0420\u00b5\u0420\u2116\u0420\u0454 \u0420\u00b7\u0420\u00b0\u0420\u0458\u0420\u0455\u0421\u0402\u0420\u0455\u0420\u00b6\u0420\u00b5\u0420\u0405\u0420\u0405\u0421\u2039\u0420\u2116 600\u0420\u0456",
                price=999.99,
                image_url="https://img.example/fish-1.webp",
                product_link="https://5ka.ru/product/fish--fish-1/",
                category="\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0",
                in_stock=True,
            ),
        ],
    )

    result = build_excel_report_from_storage(
        ReportRequest(
            selection=ExportSelection(
                shop="pyaterochka",
                intent="fish_catalog",
                categories=["\u0420\u00a0\u0421\u2039\u0420\u00b1\u0420\u00b0"],
            ),
            output_name="\u0420\u0455\u0421\u201a\u0421\u2021\u0420\u00b5\u0421\u201a_\u0421\u0402\u0421\u2039\u0420\u00b1\u0420\u00b0",
        ),
        db_path=tmp_path / "products.db",
        output_dir=tmp_path,
    )

    assert result.report_path.name == "\u0420\u0455\u0421\u201a\u0421\u2021\u0420\u00b5\u0421\u201a_\u0421\u0402\u0421\u2039\u0420\u00b1\u0420\u00b0.xlsx"


def test_build_report_filter_options_collects_supplier_and_wine_facets(tmp_path: Path) -> None:
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

    result = build_report_filter_options(
        ReportRequest(
            selection=ExportSelection(
                shop="pyaterochka",
                intent="wine_catalog",
                categories=["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"],
            )
        ),
        db_path=tmp_path / "products.db",
    )

    assert result.products_count == 2
    assert result.categories == ["\u0420\u2018\u0420\u00b5\u0420\u00b7\u0420\u00b0\u0420\u00bb\u0420\u0454\u0420\u0455\u0420\u0456\u0420\u0455\u0420\u00bb\u0421\u040a\u0420\u0405\u0420\u0455\u0420\u00b5 \u0420\u0406\u0420\u0451\u0420\u0405\u0420\u0455"]
    assert result.available_filters["suppliers"] == ["Free Feather", "OddBird"]
    assert result.available_filters["brands"] == ["Free Feather", "OddBird"]
    assert result.available_filters["alcohol_types"] == ["Безалкогольное"]
    assert result.available_filters["colors"] == ["Белое"]
    assert result.available_filter_counts["suppliers"] == {"Free Feather": 1, "OddBird": 1}
    assert result.available_filter_counts["brands"] == {"Free Feather": 1, "OddBird": 1}
    assert result.available_filter_counts["alcohol_types"] == {"Безалкогольное": 2}
    assert result.available_filter_counts["colors"] == {"Белое": 2}


def test_build_excel_report_from_storage_prefers_selected_product_ids(tmp_path: Path) -> None:
    storage = ProductStorage(tmp_path / "products.db")
    storage.save_products(
        "pyaterochka",
        [
            Product(
                id="fish-1",
                name="Треска",
                price=199.99,
                image_url="https://img.example/fish-1.webp",
                product_link="https://5ka.ru/product/fish-1/",
                category="Рыба",
                in_stock=True,
            ),
            Product(
                id="fish-2",
                name="Лосось",
                price=299.99,
                image_url="https://img.example/fish-2.webp",
                product_link="https://5ka.ru/product/fish-2/",
                category="Рыба",
                in_stock=True,
            ),
        ],
    )

    result = build_excel_report_from_storage(
        ReportRequest(
            selection=ExportSelection(
                shop="pyaterochka",
                intent="fish_catalog",
                categories=["Рыба"],
                selected_product_ids=["fish-2"],
            ),
            output_name="selected_product_report",
        ),
        db_path=tmp_path / "products.db",
        output_dir=tmp_path,
    )

    assert result.products_count == 1
    workbook = load_workbook(result.report_path, read_only=True)
    sheet = workbook["Товары"]
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[1][3] == "Лосось"
