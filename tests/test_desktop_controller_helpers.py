from launcher.desktop_controller_helpers import selected_export_targets


def test_selected_export_targets_prefers_structured_nodes_over_stale_categories() -> None:
    targets = selected_export_targets(
        categories=["Рыба", "Морепродукты"],
        selected_catalog_nodes=[
            {"name": "Завтраки", "url": "https://5ka.ru/catalog/zavtraki--251C12891/"},
            {"name": "Комбо", "url": "https://5ka.ru/catalog/kombo--251C14820/"},
        ],
        intent="fish_catalog",
    )

    assert targets == [
        {"name": "Завтраки", "url": "https://5ka.ru/catalog/zavtraki--251C12891/"},
        {"name": "Комбо", "url": "https://5ka.ru/catalog/kombo--251C14820/"},
    ]


def test_selected_export_targets_falls_back_to_category_names_without_nodes() -> None:
    targets = selected_export_targets(
        categories=[" Рыба ", "", "Рыба", "Морепродукты"],
        selected_catalog_nodes=[],
        intent="fish_catalog",
    )

    assert targets == [
        {"name": "Рыба", "url": ""},
        {"name": "Морепродукты", "url": ""},
    ]
