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
