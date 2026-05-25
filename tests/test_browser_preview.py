from launcher.browser_preview import build_browser_preview_html
from models.launcher_state import LauncherAppState


def test_build_browser_preview_html_renders_filters_and_table() -> None:
    state = LauncherAppState()
    state.selection.categories = ["Рыба", "Морепродукты"]
    state.task.message = "Готово"
    state.result.launcher_view = {
        "report_summary": {
            "products_count": 12,
            "categories": ["Рыба", "Морепродукты"],
            "category_counts": {"Рыба": 10},
            "supplier_counts": {"Море": 7},
            "brand_counts": {"Русское море": 5},
        },
        "available_filter_counts": {
            "suppliers": {"Море": 7},
            "brands": {"Русское море": 5},
        },
    }

    html = build_browser_preview_html(state)

    assert "ParserRIba Browser Preview" in html
    assert "Suppliers" in html
    assert "Русское море (5)" in html
    assert "Report products: 12" in html
    assert "Рыба" in html
