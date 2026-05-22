from models.report_request import ExportSelection, ProductFilter, ReportRequest


def test_report_request_keeps_selection_and_filters() -> None:
    request = ReportRequest(
        selection=ExportSelection(
            shop="pyaterochka",
            intent="wine_catalog",
            categories=["Безалкогольное вино"],
            selected_product_ids=["wine-1"],
        ),
        filters=ProductFilter(
            suppliers=["Free Feather"],
            min_price=500,
            max_price=900,
            in_stock=True,
            wine_styles=["Тихое"],
            alcohol_types=["Безалкогольное"],
            sugar_classes=["Полусладкое"],
            colors=["Белое"],
        ),
        output_name="wine_filtered",
    )

    assert request.selection.shop == "pyaterochka"
    assert request.selection.intent == "wine_catalog"
    assert request.selection.categories == ["Безалкогольное вино"]
    assert request.selection.selected_product_ids == ["wine-1"]
    assert request.filters.suppliers == ["Free Feather"]
    assert request.filters.strict_missing is False
    assert request.output_name == "wine_filtered"
