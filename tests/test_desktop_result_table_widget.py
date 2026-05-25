from launcher.desktop_launcher import load_pyside6
from launcher.desktop_result_table_widget import populate_result_table_widget


def test_populate_result_table_widget_configures_read_only_desktop_table() -> None:
    QApplication, qtwidgets, qt = load_pyside6()
    app = QApplication.instance() or QApplication([])
    table = qtwidgets.QTableWidget()

    populate_result_table_widget(
        table,
        qtwidgets,
        qt,
        ["Category", "Product", "Price"],
        [["Рыба", "Треска", "199.99"]],
        ["fish-1"],
        ["fish-1"],
    )

    assert app is not None
    assert table.columnCount() == 3
    assert table.rowCount() == 1
    assert table.item(0, 1).text() == "Треска"
    assert table.item(0, 0).data(qt.ItemDataRole.UserRole) == "fish-1"
    assert table.editTriggers() == qtwidgets.QAbstractItemView.EditTrigger.NoEditTriggers
    assert table.selectionBehavior() == qtwidgets.QAbstractItemView.SelectionBehavior.SelectRows
    assert table.selectionMode() == qtwidgets.QAbstractItemView.SelectionMode.ExtendedSelection
    assert table.selectionModel().selectedRows()[0].row() == 0
    assert table.alternatingRowColors() is True
    assert table.isSortingEnabled() is True
    assert table.wordWrap() is False
    assert table.verticalHeader().isVisible() is False
    table.deleteLater()


def test_populate_result_table_widget_keeps_rows_intact_with_sorting_enabled() -> None:
    QApplication, qtwidgets, qt = load_pyside6()
    app = QApplication.instance() or QApplication([])
    table = qtwidgets.QTableWidget()

    populate_result_table_widget(
        table,
        qtwidgets,
        qt,
        ["Level", "Category", "URL", "Children"],
        [
            ["1", "Napekli vam skidok", "https://5ka.ru/catalog/napekli/", "0"],
            ["1", "Vygodno", "https://5ka.ru/catalog/vygodno/", "0"],
            ["1", "Gotovaya eda", "https://5ka.ru/catalog/gotovaya-eda/", "0"],
        ],
        [],
        [],
    )

    rows = [
        [table.item(row_index, column_index).text() for column_index in range(table.columnCount())]
        for row_index in range(table.rowCount())
    ]

    assert app is not None
    assert rows == [
        ["1", "Napekli vam skidok", "https://5ka.ru/catalog/napekli/", "0"],
        ["1", "Vygodno", "https://5ka.ru/catalog/vygodno/", "0"],
        ["1", "Gotovaya eda", "https://5ka.ru/catalog/gotovaya-eda/", "0"],
    ]
    assert table.isSortingEnabled() is True
    table.deleteLater()


def test_populate_result_table_widget_repopulates_after_user_sorting() -> None:
    QApplication, qtwidgets, qt = load_pyside6()
    app = QApplication.instance() or QApplication([])
    table = qtwidgets.QTableWidget()
    populate_result_table_widget(
        table,
        qtwidgets,
        qt,
        ["Level", "Category", "URL", "Children"],
        [["1", "Zebra", "https://example.test/zebra", "0"]],
        [],
        [],
    )
    table.sortItems(1)

    populate_result_table_widget(
        table,
        qtwidgets,
        qt,
        ["Level", "Category", "URL", "Children"],
        [
            ["0", "Catalog", "https://5ka.ru/catalog/", "2"],
            ["1", "Napekli vam skidok", "https://5ka.ru/catalog/napekli/", "0"],
            ["1", "Vygodno", "https://5ka.ru/catalog/vygodno/", "0"],
        ],
        [],
        [],
    )
    rows = [
        [
            table.item(row_index, column_index).text()
            if table.item(row_index, column_index)
            else ""
            for column_index in range(table.columnCount())
        ]
        for row_index in range(table.rowCount())
    ]

    assert app is not None
    assert rows == [
        ["0", "Catalog", "https://5ka.ru/catalog/", "2"],
        ["1", "Napekli vam skidok", "https://5ka.ru/catalog/napekli/", "0"],
        ["1", "Vygodno", "https://5ka.ru/catalog/vygodno/", "0"],
    ]
    assert table.isSortingEnabled() is True
    table.deleteLater()


def test_populate_result_table_widget_drops_stale_rows_on_repopulate() -> None:
    QApplication, qtwidgets, qt = load_pyside6()
    app = QApplication.instance() or QApplication([])
    table = qtwidgets.QTableWidget()
    populate_result_table_widget(
        table,
        qtwidgets,
        qt,
        ["Level", "Category", "URL", "Children"],
        [
            ["1", "Old A", "https://example.test/a", "0"],
            ["1", "Old B", "https://example.test/b", "0"],
            ["1", "Old C", "https://example.test/c", "0"],
        ],
        [],
        [],
    )

    populate_result_table_widget(
        table,
        qtwidgets,
        qt,
        ["Level", "Category", "URL", "Children"],
        [["0", "Catalog", "https://5ka.ru/catalog/", "140"]],
        [],
        [],
    )

    assert app is not None
    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "0"
    assert table.item(0, 1).text() == "Catalog"
    assert table.item(0, 2).text() == "https://5ka.ru/catalog/"
    assert table.item(0, 3).text() == "140"
    assert table.isSortingEnabled() is True
    table.deleteLater()
