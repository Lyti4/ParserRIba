from pathlib import Path

from launcher.desktop_result_table import build_result_table
from models.launcher_state import LauncherAppState


def test_build_result_table_reads_export_json(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        (
            '{"products":[{"id":"wine-1","category":"Вино","name":"OddBird Spumante","brand":"OddBird",'
            '"subcategory":"Игристое","raw_data":{"supplier":"OddBird","alcohol_type":"Безалкогольное"},'
            '"price":{"current":699.99},"in_stock":true,"product_link":"https://example/item"}]}'
        ),
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)

    table = build_result_table(state)

    assert table["headers"] == [
        "Категория",
        "Товар",
        "Бренд",
        "Поставщик",
        "Тип",
        "Алкогольный тип",
        "Цена",
        "В наличии",
        "Ссылка",
    ]
    assert table["rows"] == [[
        "Вино",
        "OddBird Spumante",
        "OddBird",
        "OddBird",
        "Игристое",
        "Безалкогольное",
        "699.99",
        "В наличии",
        "https://example/item",
    ]]
    assert table["product_ids"] == ["wine-1"]


def test_build_result_table_falls_back_to_report_summary() -> None:
    state = LauncherAppState()
    state.result.summary = {
        "report_summary": {
            "category_counts": {"Рыба": 10},
            "supplier_counts": {"Море": 7},
            "brand_counts": {"Русское море": 5},
        }
    }

    table = build_result_table(state)

    assert table["headers"] == ["Категория", "Товаров", "Топ поставщик", "Топ бренд"]
    assert table["rows"] == [["Рыба", "10", "Море (7)", "Русское море (5)"]]
    assert table["product_ids"] == []


def test_build_result_table_skips_blank_and_duplicate_catalog_rows() -> None:
    state = LauncherAppState()
    state.catalog.full_tree = [
        {
            "name": "",
            "url": "",
            "children": [
                {"name": "Napekli vam skidok", "url": "https://5ka.ru/catalog/napekli/", "children": []},
                {"name": "Napekli vam skidok", "url": "https://5ka.ru/catalog/napekli/", "children": []},
                {"name": "", "url": "", "children": []},
            ],
        }
    ]

    table = build_result_table(state)

    assert table["rows"] == [["1", "Napekli vam skidok", "https://5ka.ru/catalog/napekli/", "0"]]


def test_build_result_table_reads_full_catalog_tree_from_summary() -> None:
    state = LauncherAppState()
    state.result.summary = {
        "full_catalog_tree": [
            {
                "name": "Каталог",
                "url": "https://example.test/catalog/",
                "children": [{"name": "Рыба", "url": "https://example.test/catalog/fish/"}],
            }
        ]
    }

    table = build_result_table(state)

    assert table["rows"] == [
        ["0", "Каталог", "https://example.test/catalog/", "1"],
        ["1", "Рыба", "https://example.test/catalog/fish/", "0"],
    ]


def test_build_result_table_applies_selected_export_filters(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        (
            '{"products":['
            '{"id":"wine-1","category":"Вино","name":"OddBird Spumante","brand":"OddBird",'
            '"subcategory":"Игристое","raw_data":{"supplier":"OddBird","alcohol_type":"Безалкогольное","color":"Белое","sugar_class":"Сухое"},'
            '"price":{"current":699.99},"in_stock":true,"product_link":"https://example/item-1"},'
            '{"id":"wine-2","category":"Вино","name":"Free Feather Red","brand":"Free Feather",'
            '"subcategory":"Тихое","raw_data":{"supplier":"Free Feather","alcohol_type":"Безалкогольное","color":"Красное","sugar_class":"Полусладкое"},'
            '"price":{"current":499.99},"in_stock":false,"product_link":"https://example/item-2"}'
            ']}'
        ),
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)
    state.filters.suppliers = ["OddBird"]
    state.filters.wine_styles = ["Игристое"]
    state.filters.colors = ["Белое"]
    state.filters.min_price = 600.0
    state.filters.in_stock = True

    table = build_result_table(state)

    assert len(table["rows"]) == 1
    assert table["rows"][0][1] == "OddBird Spumante"
    assert table["product_ids"] == ["wine-1"]


def test_build_result_table_keeps_missing_filtered_field_when_not_strict(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        (
            '{"products":['
            '{"id":"wine-1","category":"Вино","name":"Unknown Supplier Wine","brand":"Brand A",'
            '"subcategory":"Тихое","raw_data":{"alcohol_type":"Безалкогольное"},'
            '"price":{"current":299.99},"in_stock":true}'
            ']}'
        ),
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)
    state.filters.suppliers = ["OddBird"]

    table = build_result_table(state)

    assert len(table["rows"]) == 1


def test_build_result_table_excludes_missing_filtered_field_when_strict(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        (
            '{"products":['
            '{"id":"wine-1","category":"Вино","name":"Unknown Supplier Wine","brand":"Brand A",'
            '"subcategory":"Тихое","raw_data":{"alcohol_type":"Безалкогольное"},'
            '"price":{"current":299.99},"in_stock":true}'
            ']}'
        ),
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)
    state.filters.suppliers = ["OddBird"]
    state.filters.strict_missing = True

    table = build_result_table(state)

    assert table["rows"] == []


def test_build_result_table_keeps_product_ids_for_explicit_selection(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        (
            '{"products":['
            '{"id":"fish-1","category":"Рыба","name":"Треска","brand":"Nord",'
            '"raw_data":{"supplier":"Nord"},"price":{"current":199.99},"in_stock":true},'
            '{"product_id":"fish-2","category":"Рыба","name":"Лосось","brand":"Nord",'
            '"raw_data":{"supplier":"Nord"},"price":{"current":299.99},"in_stock":true}'
            ']}'
        ),
        encoding="utf-8",
    )
    state = LauncherAppState()
    state.result.json_path = str(json_path)

    table = build_result_table(state)

    assert [row[1] for row in table["rows"]] == ["Треска", "Лосось"]
    assert table["product_ids"] == ["fish-1", "fish-2"]
