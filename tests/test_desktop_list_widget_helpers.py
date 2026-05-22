from launcher.desktop_list_widget_helpers import clear_multi_select_widgets, set_all_items_selected


class _DummyItem:
    def __init__(self) -> None:
        self.selected = False

    def setSelected(self, value: bool) -> None:
        self.selected = value


class _DummyListWidget:
    def __init__(self, count: int) -> None:
        self._items = [_DummyItem() for _ in range(count)]

    def count(self) -> int:
        return len(self._items)

    def item(self, index: int) -> _DummyItem:
        return self._items[index]


def test_set_all_items_selected_marks_every_item() -> None:
    widget = _DummyListWidget(3)

    set_all_items_selected(widget, True)

    assert all(item.selected is True for item in widget._items)


def test_clear_multi_select_widgets_clears_every_widget() -> None:
    widgets = [_DummyListWidget(2), _DummyListWidget(1)]
    for widget in widgets:
        set_all_items_selected(widget, True)

    clear_multi_select_widgets(widgets)

    assert all(item.selected is False for widget in widgets for item in widget._items)
