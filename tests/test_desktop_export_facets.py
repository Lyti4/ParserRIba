from pathlib import Path

from launcher.desktop_export_facets import build_available_filter_counts_from_export_json


def test_build_available_filter_counts_from_export_json_reads_fresh_facets(tmp_path: Path) -> None:
    json_path = tmp_path / "products.json"
    json_path.write_text(
        (
            '{"products":['
            '{"category":"Вино","name":"OddBird Spumante","brand":"OddBird",'
            '"subcategory":"Игристое","raw_data":{"supplier":"OddBird","alcohol_type":"Безалкогольное","color":"Белое","sugar_class":"Сухое"}},'
            '{"category":"Вино","name":"Free Feather Red","brand":"Free Feather",'
            '"subcategory":"Тихое","raw_data":{"supplier":"Free Feather","alcohol_type":"Безалкогольное","color":"Красное","sugar_class":"Полусладкое"}}'
            ']}'
        ),
        encoding="utf-8",
    )

    counts = build_available_filter_counts_from_export_json(str(json_path))

    assert counts["suppliers"] == {"Free Feather": 1, "OddBird": 1}
    assert counts["brands"] == {"Free Feather": 1, "OddBird": 1}
    assert counts["categories"] == {"Вино": 2}
    assert counts["wine_styles"] == {"Игристое": 1, "Тихое": 1}
    assert counts["alcohol_types"] == {"Безалкогольное": 2}
    assert counts["colors"] == {"Белое": 1, "Красное": 1}


def test_build_available_filter_counts_from_export_json_handles_missing_file(tmp_path: Path) -> None:
    counts = build_available_filter_counts_from_export_json(str(tmp_path / "missing.json"))

    assert counts == {}
