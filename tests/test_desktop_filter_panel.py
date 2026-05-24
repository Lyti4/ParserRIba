import pytest

from launcher.desktop_filter_panel import build_filter_box, collect_filter_selections, refresh_filter_widgets
from launcher.desktop_launcher import load_pyside6
from models.launcher_state import LauncherAppState


class _DummyShell:
    def __init__(self) -> None:
        self.state = LauncherAppState()
        self._qtwidgets = None
        self.filter_widgets = {}
        self.filter_field_widgets = {}
        self.filter_extra_widgets = []
        self.filter_action_buttons = []

    def _on_clear_filters(self) -> None:
        return None


def test_filter_panel_collects_multi_select_and_value_filters() -> None:
    QApplication, qtwidgets, _ = load_pyside6()
    app = QApplication.instance() or QApplication([])
    shell = _DummyShell()
    shell._qtwidgets = qtwidgets
    shell.state.result.launcher_view = {
        "available_filter_counts": {
            "suppliers": {"Free Feather": 3},
            "brands": {"OddBird": 2},
        }
    }
    shell.state.filters.suppliers = ["Free Feather"]
    box = build_filter_box(shell, qtwidgets)
    refresh_filter_widgets(shell)
    shell.filter_field_widgets["min_price"].setValue(100.0)
    shell.filter_field_widgets["max_price"].setValue(900.0)
    shell.filter_field_widgets["in_stock"].setCurrentText("В наличии")
    shell.filter_field_widgets["strict_missing"].setChecked(True)

    selections = collect_filter_selections(shell)

    assert app is not None
    assert box.title() == "Фильтры"
    assert selections["suppliers"] == ["Free Feather"]
    assert selections["brands"] == []
    assert selections["min_price"] == 100.0
    assert selections["max_price"] == 900.0
    assert selections["in_stock"] is True
    assert selections["strict_missing"] is True
    box.deleteLater()


def test_filter_panel_refreshes_value_widgets_from_state() -> None:
    QApplication, qtwidgets, _ = load_pyside6()
    app = QApplication.instance() or QApplication([])
    shell = _DummyShell()
    shell._qtwidgets = qtwidgets
    shell.state.filters.min_price = 250.0
    shell.state.filters.max_price = 750.0
    shell.state.filters.in_stock = False
    shell.state.filters.strict_missing = True
    box = build_filter_box(shell, qtwidgets)

    refresh_filter_widgets(shell)

    assert app is not None
    assert shell.filter_field_widgets["min_price"].value() == 250.0
    assert shell.filter_field_widgets["max_price"].value() == 750.0
    assert shell.filter_field_widgets["in_stock"].currentText() == "Нет в наличии"
    assert shell.filter_field_widgets["strict_missing"].isChecked() is True
    box.deleteLater()


def test_filter_panel_uses_compact_list_heights() -> None:
    QApplication, qtwidgets, _ = load_pyside6()
    app = QApplication.instance() or QApplication([])
    shell = _DummyShell()
    shell._qtwidgets = qtwidgets
    box = build_filter_box(shell, qtwidgets)

    suppliers_widget = shell.filter_widgets["suppliers"]

    assert app is not None
    assert suppliers_widget.minimumHeight() == 56
    assert suppliers_widget.maximumHeight() == 72
    box.deleteLater()


@pytest.mark.parametrize(
    ("found_filters", "expected_items"),
    (
        ({"supplier_origin": {"Seafood": 3, "Frozen": 1}}, ["Frozen (1)", "Seafood (3)"]),
        ({"supplier_origin": ["Seafood", {"value": "Frozen", "count": 1}]}, ["Seafood", "Frozen (1)"]),
    ),
)
def test_filter_panel_renders_found_filters_scroll_area_when_present(
    found_filters: dict[str, object],
    expected_items: list[str],
) -> None:
    QApplication, qtwidgets, _ = load_pyside6()
    app = QApplication.instance() or QApplication([])
    shell = _DummyShell()
    shell._qtwidgets = qtwidgets
    shell.state.result.launcher_view = {"found_filters": found_filters}

    box = build_filter_box(shell, qtwidgets)
    refresh_filter_widgets(shell)

    found_group = next(
        (group for group in box.findChildren(qtwidgets.QGroupBox) if group.title() == "Найденные фильтры"),
        None,
    )
    scroll_area = box.findChild(qtwidgets.QScrollArea, "launcherFoundFiltersScrollArea")
    widget = shell.found_filter_widgets["supplier_origin"]

    assert app is not None
    assert found_group is not None
    assert scroll_area is not None
    assert [widget.item(index).text() for index in range(widget.count())] == expected_items
    box.deleteLater()


def test_filter_panel_keeps_old_layout_when_found_filters_missing() -> None:
    QApplication, qtwidgets, _ = load_pyside6()
    app = QApplication.instance() or QApplication([])
    shell = _DummyShell()
    shell._qtwidgets = qtwidgets
    shell.state.result.launcher_view = {}

    box = build_filter_box(shell, qtwidgets)
    refresh_filter_widgets(shell)

    assert app is not None
    assert box.title() == "Фильтры"
    assert box.findChild(qtwidgets.QScrollArea, "launcherFoundFiltersScrollArea") is None
    assert shell.filter_widgets["suppliers"].minimumHeight() == 56
    box.deleteLater()
