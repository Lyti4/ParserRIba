from launcher.desktop_catalog_tree_widget import (
    collect_checked_catalog_nodes,
    populate_catalog_tree_widget,
    set_all_catalog_tree_items_checked,
)
from launcher.desktop_launcher import load_pyside6


def test_catalog_tree_widget_collects_checked_nodes_without_root() -> None:
    QApplication, qtwidgets, qt = load_pyside6()
    app = QApplication.instance() or QApplication([])
    tree = qtwidgets.QTreeWidget()

    populate_catalog_tree_widget(
        tree,
        qtwidgets,
        qt,
        [
            {
                "name": "Каталог",
                "url": "https://5ka.ru/catalog/",
                "children": [
                    {"name": "Рыба", "url": "https://5ka.ru/catalog/fish/", "children": []},
                    {"name": "Вино", "url": "https://5ka.ru/catalog/wine/", "children": []},
                ],
            }
        ],
        ["Рыба"],
    )

    selected = collect_checked_catalog_nodes(tree, qt)

    assert app is not None
    assert tree.topLevelItemCount() == 1
    assert selected == [{"name": "Рыба", "url": "https://5ka.ru/catalog/fish/"}]
    tree.deleteLater()


def test_catalog_tree_widget_selects_all_catalog_nodes_without_exporting_root() -> None:
    QApplication, qtwidgets, qt = load_pyside6()
    app = QApplication.instance() or QApplication([])
    tree = qtwidgets.QTreeWidget()
    populate_catalog_tree_widget(
        tree,
        qtwidgets,
        qt,
        [
            {
                "name": "Каталог",
                "url": "https://5ka.ru/catalog/",
                "children": [
                    {"name": "Рыба", "url": "https://5ka.ru/catalog/fish/", "children": []},
                    {"name": "Вино", "url": "https://5ka.ru/catalog/wine/", "children": []},
                ],
            }
        ],
        [],
    )

    set_all_catalog_tree_items_checked(tree, qt, True)

    assert app is not None
    assert collect_checked_catalog_nodes(tree, qt) == [
        {"name": "Рыба", "url": "https://5ka.ru/catalog/fish/"},
        {"name": "Вино", "url": "https://5ka.ru/catalog/wine/"},
    ]
    tree.deleteLater()
