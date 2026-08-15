from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, cast
import json
import unittest

from application.contracts import ApplicationContractError
from launcher.desktop_controller import DesktopLauncherController
from launcher.desktop_launcher import DesktopLauncherShell
from launcher.desktop_source_catalog_tree import (
    collect_checked_source_catalog_node_ids,
    populate_source_catalog_tree_widget,
)
from utils.source_adapter_tasks import build_source_adapter_collection_request


class _CheckState:
    Unchecked = 0
    Checked = 2


class _ItemFlag:
    ItemIsUserCheckable = 1


class _Qt:
    CheckState = _CheckState
    ItemFlag = _ItemFlag


class _TreeItem:
    def __init__(self, labels: list[str]) -> None:
        self.labels = labels
        self.children: list[_TreeItem] = []
        self._flags = 0
        self._check_state = _CheckState.Unchecked
        self._data: dict[tuple[int, int], object] = {}

    def flags(self) -> int:
        return self._flags

    def setFlags(self, value: int) -> None:
        self._flags = value

    def setCheckState(self, _column: int, state: int) -> None:
        self._check_state = state

    def checkState(self, _column: int) -> int:
        return self._check_state

    def setData(self, column: int, role: int, value: object) -> None:
        self._data[(column, role)] = value

    def data(self, column: int, role: int) -> object:
        return self._data.get((column, role))

    def addChild(self, item: _TreeItem) -> None:
        self.children.append(item)

    def childCount(self) -> int:
        return len(self.children)

    def child(self, index: int) -> _TreeItem:
        return self.children[index]


class _ResizeMode:
    Stretch = 1
    ResizeToContents = 2


class _QHeaderView:
    ResizeMode = _ResizeMode


class _Header:
    def setSectionResizeMode(self, _column: int, _mode: int) -> None:
        pass


class _Tree:
    def __init__(self) -> None:
        self.items: list[_TreeItem] = []
        self.headers: list[str] = []

    def blockSignals(self, _value: bool) -> None:
        pass

    def clear(self) -> None:
        self.items.clear()

    def setColumnCount(self, _value: int) -> None:
        pass

    def setHeaderLabels(self, labels: list[str]) -> None:
        self.headers = labels

    def addTopLevelItem(self, item: _TreeItem) -> None:
        self.items.append(item)

    def topLevelItemCount(self) -> int:
        return len(self.items)

    def topLevelItem(self, index: int) -> _TreeItem:
        return self.items[index]

    def expandToDepth(self, _depth: int) -> None:
        pass

    def header(self) -> _Header:
        return _Header()


class _QtWidgets:
    QTreeWidgetItem = _TreeItem
    QHeaderView = _QHeaderView


class _Combo:
    def currentData(self) -> str:
        return "local-json-file"


class _LineEdit:
    def __init__(self) -> None:
        self.value = ""

    def setText(self, value: str) -> None:
        self.value = value

    def text(self) -> str:
        return self.value


class _InspectionController:
    def __init__(self) -> None:
        self.events: list[str] = []

    def source_catalog_inspection_worker_action(
        self,
        source_profile_id: str,
        source_locator: str | None = None,
    ):
        self.events.append(f"build:{source_profile_id}:{source_locator}")

        def action() -> dict[str, object]:
            self.events.append("worker")
            return {
                "status": "finished",
                "source_profile_id": source_profile_id,
                "source_locator": source_locator or "",
                "source_nodes": [],
            }

        return action

    def begin_source_catalog_inspection(self, source_profile_id: str) -> None:
        self.events.append(f"begin:{source_profile_id}")

    def apply_source_catalog_inspection_worker_outcome(
        self,
        _outcome: object,
        source_profile_id: str,
    ) -> None:
        self.events.append(f"apply:{source_profile_id}")

    def fail_source_catalog_inspection_worker(
        self,
        _error: object,
        source_profile_id: str,
    ) -> None:
        self.events.append(f"fail:{source_profile_id}")


class _FileDialog:
    selected_path = ""

    @classmethod
    def getOpenFileName(cls, *_args: object) -> tuple[str, str]:
        return cls.selected_path, "JSON (*.json)"


class _PickerQtWidgets:
    QFileDialog = _FileDialog


class _PickerShell:
    def __init__(self) -> None:
        self.source_profile_combo = _Combo()
        self.source_locator_input = _LineEdit()
        self.controller = _InspectionController()
        self._qtwidgets = _PickerQtWidgets
        self.window = object()
        self.root_dir = Path("/tmp/parserriba-picker-test")
        self._active_task_thread = None
        self.background_action = None
        self.finished_callback = None
        self.failed_callback = None

    @staticmethod
    def _current_combo_value(combo: _Combo) -> str:
        return combo.currentData()

    def _run_ui_action(self, _action: object) -> None:
        raise AssertionError("catalog inspection must use its dedicated pure-worker handoff")

    def _refresh_ui(self) -> None:
        self.controller.events.append("refresh")

    def _start_background_action(
        self,
        action: object,
        *,
        on_finished: object | None = None,
        on_failed: object | None = None,
    ) -> None:
        self.controller.events.append("submit-worker")
        self.background_action = action
        self.finished_callback = on_finished
        self.failed_callback = on_failed

    def _start_source_catalog_inspection(
        self,
        source_profile_id: str,
        source_locator: str | None = None,
    ) -> None:
        DesktopLauncherShell._start_source_catalog_inspection(
            cast(DesktopLauncherShell, self),
            source_profile_id,
            source_locator,
        )

    def _on_source_catalog_inspection_finished(
        self,
        outcome: object,
        source_profile_id: str,
    ) -> None:
        self.controller.apply_source_catalog_inspection_worker_outcome(
            outcome,
            source_profile_id,
        )
        self._refresh_ui()

    def _on_source_catalog_inspection_failed(
        self,
        error: object,
        source_profile_id: str,
    ) -> None:
        self.controller.fail_source_catalog_inspection_worker(error, source_profile_id)
        self._refresh_ui()


class _AsyncCollectionController:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def source_adapter_collection_worker_action(self, **_kwargs: object):
        self.events.append("build-action")

        def action() -> dict[str, object]:
            self.events.append("worker")
            return {"status": "finished", "result": {"manifest": {}}}

        return action

    def begin_source_adapter_collection(self) -> None:
        self.events.append("begin-on-gui")

    def apply_source_adapter_collection_worker_outcome(
        self, _outcome: object, _source_profile_id: str
    ) -> None:
        self.events.append("apply-on-gui")

    def fail_source_adapter_collection_worker(
        self, _error: object, _source_profile_id: str
    ) -> None:
        self.events.append("fail-on-gui")


class _AsyncCollectionShell:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.controller = _AsyncCollectionController(self.events)
        self.source_profile_combo = _Combo()
        self.source_locator_input = _LineEdit()
        self.source_locator_input.setText("file:///tmp/catalog.json")
        self.source_catalog_tree = _Tree()
        populate_source_catalog_tree_widget(
            self.source_catalog_tree,
            _QtWidgets,
            _Qt,
            [
                {
                    "source_profile_id": "local-json-file",
                    "catalog_node_id": "lighting",
                    "display_name": "Lighting",
                    "parent_catalog_node_id": None,
                    "locator": None,
                }
            ],
            ["lighting"],
        )
        self._qt = _Qt
        self._active_task_thread = None
        self.source_collection_run_sequence = 0
        self.category_list = None
        self.background_action = None
        self.finished_callback = None
        self.failed_callback = None

    @staticmethod
    def _current_combo_value(combo: _Combo) -> str:
        return combo.currentData()

    def _next_source_collection_run_id(self) -> str:
        return DesktopLauncherShell._next_source_collection_run_id(cast(DesktopLauncherShell, self))

    def _run_ui_action(self, _action: object) -> None:
        raise AssertionError("source collection must use its dedicated pure-worker handoff")

    def _refresh_ui(self) -> None:
        self.events.append("refresh-on-gui")

    def _start_background_action(
        self,
        action: object,
        *,
        on_finished: object | None = None,
        on_failed: object | None = None,
    ) -> None:
        self.events.append("submit-worker")
        self.background_action = action
        self.finished_callback = on_finished
        self.failed_callback = on_failed

    def _on_source_adapter_collection_finished(
        self,
        outcome: object,
        source_profile_id: str,
    ) -> None:
        self.controller.apply_source_adapter_collection_worker_outcome(
            outcome,
            source_profile_id,
        )
        self._refresh_ui()

    def _on_source_adapter_collection_failed(
        self,
        error: object,
        source_profile_id: str,
    ) -> None:
        self.controller.fail_source_adapter_collection_worker(error, source_profile_id)
        self._refresh_ui()


class SourceAdapterFilePickerTreeTests(unittest.TestCase):
    def test_launcher_source_collection_uses_pure_worker_and_gui_apply_callback(self) -> None:
        shell = _AsyncCollectionShell()

        DesktopLauncherShell._on_run_source_adapter_collection(
            cast(DesktopLauncherShell, shell)
        )

        self.assertEqual(
            shell.events,
            ["build-action", "begin-on-gui", "refresh-on-gui", "submit-worker"],
        )
        background_action = cast(Callable[[], object], shell.background_action)
        self.assertTrue(callable(background_action))
        outcome = background_action()
        json.dumps(outcome)
        self.assertNotIn("apply-on-gui", shell.events)
        finished_callback = cast(Callable[[object], None], shell.finished_callback)
        self.assertTrue(callable(finished_callback))
        finished_callback(outcome)
        self.assertEqual(shell.events[-2:], ["apply-on-gui", "refresh-on-gui"])

    def test_production_inspection_worker_is_json_safe_and_state_neutral_until_apply(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            controller = DesktopLauncherController(root_dir=root)
            action = controller.source_catalog_inspection_worker_action(
                "local-json-file",
                source_path.as_uri(),
            )
            controller.begin_source_catalog_inspection("local-json-file")

            outcome = action()

            json.dumps(outcome)
            self.assertEqual(controller.state.task.status, "running")
            self.assertEqual(controller.state.catalog.source_nodes, [])
            nodes = controller.apply_source_catalog_inspection_worker_outcome(
                outcome,
                "local-json-file",
            )
            self.assertIsNotNone(nodes)
            self.assertEqual(controller.state.task.status, "succeeded")
            self.assertEqual(
                [node["catalog_node_id"] for node in controller.state.catalog.source_nodes],
                ["home", "lighting"],
            )

    def test_production_collection_worker_is_json_safe_and_state_neutral_until_apply(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            controller = DesktopLauncherController(root_dir=root)
            nodes = controller.inspect_source_adapter_catalog(
                "local-json-file", source_path.as_uri()
            )
            controller.set_source_adapter_catalog_selection(["lighting"])
            action = controller.source_adapter_collection_worker_action(
                collection_run_id="picker-tree-json-worker-001",
                source_profile_id="local-json-file",
                source_locator=source_path.as_uri(),
                catalog_node_ids=["lighting"],
            )
            controller.begin_source_adapter_collection()

            outcome = action()

            json.dumps(outcome)
            self.assertEqual(controller.state.task.status, "running")
            self.assertEqual(controller.state.catalog.source_nodes, nodes)
            self.assertEqual(controller.state.catalog.selected_source_node_ids, ["lighting"])
            result = controller.apply_source_adapter_collection_worker_outcome(
                outcome,
                "local-json-file",
            )
            self.assertIsNotNone(result)
            self.assertEqual(controller.state.task.status, "succeeded")

    def test_controller_inspection_persists_serializable_parent_linked_catalog_state(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            controller = DesktopLauncherController(root_dir=Path(directory))

            nodes = controller.inspect_source_adapter_catalog("local-json-file", source_path.as_uri())

            self.assertEqual([node["catalog_node_id"] for node in nodes], ["home", "lighting"])
            self.assertEqual(nodes[1]["parent_catalog_node_id"], "home")
            self.assertEqual(controller.state.catalog.source_profile_id, "local-json-file")
            self.assertEqual(controller.state.catalog.source_locator, source_path.as_uri())
            self.assertEqual(controller.state.catalog.source_nodes, nodes)
            self.assertEqual(controller.state.catalog.selected_source_node_ids, [])
            self.assertEqual(controller.state.task.status, "succeeded")

    def test_failed_reinspection_clears_previously_valid_source_tree(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            valid_path = root / "valid.json"
            valid_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            invalid_path = root / "invalid.json"
            invalid_document = _catalog_document()
            invalid_product = cast(list[dict[str, object]], invalid_document["products"])[0]
            invalid_product["session_token"] = "must-not-be-accepted"
            invalid_path.write_text(json.dumps(invalid_document), encoding="utf-8")
            controller = DesktopLauncherController(root_dir=root)
            controller.inspect_source_adapter_catalog("local-json-file", valid_path.as_uri())

            with self.assertRaises(ApplicationContractError):
                controller.inspect_source_adapter_catalog("local-json-file", invalid_path.as_uri())

            self.assertEqual(controller.state.catalog.source_profile_id, "local-json-file")
            self.assertEqual(controller.state.catalog.source_locator, "")
            self.assertEqual(controller.state.catalog.source_nodes, [])
            self.assertEqual(controller.state.catalog.selected_source_node_ids, [])
            self.assertEqual(controller.state.task.status, "failed")

    def test_collection_preflight_failure_clears_stale_inspected_tree(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            controller = DesktopLauncherController(root_dir=root)
            controller.inspect_source_adapter_catalog("local-json-file", source_path.as_uri())
            controller.set_source_adapter_catalog_selection(["lighting"])
            invalid_document = _catalog_document()
            invalid_product = cast(list[dict[str, object]], invalid_document["products"])[0]
            invalid_product["session_token"] = "must-not-be-accepted"
            source_path.write_text(json.dumps(invalid_document), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Проверьте источник"):
                controller.run_source_adapter_collection(
                    collection_run_id="picker-tree-stale-file-001",
                    source_profile_id="local-json-file",
                    source_locator=source_path.as_uri(),
                    catalog_node_ids=["lighting"],
                )

            self.assertEqual(controller.state.catalog.source_profile_id, "local-json-file")
            self.assertEqual(controller.state.catalog.source_locator, "")
            self.assertEqual(controller.state.catalog.source_nodes, [])
            self.assertEqual(controller.state.catalog.selected_source_node_ids, [])
            self.assertEqual(controller.state.task.status, "failed")
            reloaded = DesktopLauncherController(root_dir=root)
            self.assertEqual(reloaded.state.catalog.source_locator, "")
            self.assertEqual(reloaded.state.catalog.source_nodes, [])
            self.assertEqual(reloaded.state.catalog.selected_source_node_ids, [])

    def test_empty_collection_scope_preserves_valid_inspected_tree(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            controller = DesktopLauncherController(root_dir=root)
            expected_nodes = controller.inspect_source_adapter_catalog(
                "local-json-file", source_path.as_uri()
            )
            controller.set_source_adapter_catalog_selection(["lighting"])

            with self.assertRaisesRegex(ValueError, "Проверьте источник"):
                controller.run_source_adapter_collection(
                    collection_run_id="picker-tree-empty-scope-001",
                    source_profile_id="local-json-file",
                    source_locator=source_path.as_uri(),
                    catalog_node_ids=[],
                )

            self.assertEqual(controller.state.catalog.source_locator, source_path.as_uri())
            self.assertEqual(controller.state.catalog.source_nodes, expected_nodes)
            self.assertEqual(controller.state.catalog.selected_source_node_ids, ["lighting"])
            self.assertEqual(controller.state.task.status, "failed")
            reloaded = DesktopLauncherController(root_dir=root)
            self.assertEqual(reloaded.state.catalog.source_locator, source_path.as_uri())
            self.assertEqual(reloaded.state.catalog.source_nodes, expected_nodes)
            self.assertEqual(reloaded.state.catalog.selected_source_node_ids, ["lighting"])

    def test_invalid_run_input_preserves_valid_tree_and_never_dispatches(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            runner_calls: list[dict[str, object]] = []

            def runner(**kwargs: object):
                runner_calls.append(kwargs)
                raise AssertionError("invalid run input must not reach the worker runner")

            controller = DesktopLauncherController(
                root_dir=root,
                source_adapter_collection_runner=runner,
            )
            expected_nodes = controller.inspect_source_adapter_catalog(
                "local-json-file", source_path.as_uri()
            )
            controller.set_source_adapter_catalog_selection(["lighting"])

            with self.assertRaisesRegex(ValueError, "Проверьте источник"):
                controller.run_source_adapter_collection(
                    collection_run_id="../invalid-run",
                    source_profile_id="local-json-file",
                    source_locator=source_path.as_uri(),
                    catalog_node_ids=["lighting"],
                )

            self.assertEqual(runner_calls, [])
            self.assertEqual(controller.state.catalog.source_locator, source_path.as_uri())
            self.assertEqual(controller.state.catalog.source_nodes, expected_nodes)
            self.assertEqual(controller.state.catalog.selected_source_node_ids, ["lighting"])

    def test_worker_reinspection_failure_clears_and_persists_stale_tree(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")

            def racing_runner(**kwargs: object):
                source_path.unlink()
                task_input = cast(dict[str, object], kwargs["task_input"])
                build_source_adapter_collection_request(task_input)
                raise AssertionError("worker reinspection must fail closed")

            controller = DesktopLauncherController(
                root_dir=root,
                source_adapter_collection_runner=racing_runner,
            )
            controller.inspect_source_adapter_catalog("local-json-file", source_path.as_uri())
            controller.set_source_adapter_catalog_selection(["lighting"])

            with self.assertRaises(ValueError):
                controller.run_source_adapter_collection(
                    collection_run_id="picker-tree-worker-race-001",
                    source_profile_id="local-json-file",
                    source_locator=source_path.as_uri(),
                    catalog_node_ids=["lighting"],
                )

            self.assertEqual(controller.state.catalog.source_locator, "")
            self.assertEqual(controller.state.catalog.source_nodes, [])
            self.assertEqual(controller.state.catalog.selected_source_node_ids, [])
            reloaded = DesktopLauncherController(root_dir=root)
            self.assertEqual(reloaded.state.catalog.source_locator, "")
            self.assertEqual(reloaded.state.catalog.source_nodes, [])
            self.assertEqual(reloaded.state.catalog.selected_source_node_ids, [])

    def test_post_dispatch_scope_named_error_still_clears_and_persists_tree(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")

            def dispatched_runner(**_kwargs: object):
                raise ApplicationContractError(
                    "COLLECTION_SCOPE_REQUIRED",
                    "synthetic post-dispatch failure",
                )

            controller = DesktopLauncherController(
                root_dir=root,
                source_adapter_collection_runner=dispatched_runner,
            )
            controller.inspect_source_adapter_catalog("local-json-file", source_path.as_uri())
            controller.set_source_adapter_catalog_selection(["lighting"])

            with self.assertRaises(ValueError):
                controller.run_source_adapter_collection(
                    collection_run_id="picker-tree-post-dispatch-001",
                    source_profile_id="local-json-file",
                    source_locator=source_path.as_uri(),
                    catalog_node_ids=["lighting"],
                )

            self.assertEqual(controller.state.catalog.source_locator, "")
            self.assertEqual(controller.state.catalog.source_nodes, [])
            self.assertEqual(controller.state.catalog.selected_source_node_ids, [])
            reloaded = DesktopLauncherController(root_dir=root)
            self.assertEqual(reloaded.state.catalog.source_locator, "")
            self.assertEqual(reloaded.state.catalog.source_nodes, [])
            self.assertEqual(reloaded.state.catalog.selected_source_node_ids, [])

    def test_controller_runs_selected_tree_node_through_real_local_task_chain(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            controller = DesktopLauncherController(root_dir=root)
            controller.inspect_source_adapter_catalog("local-json-file", source_path.as_uri())
            controller.set_source_adapter_catalog_selection(["lighting"])

            result = controller.run_source_adapter_collection(
                collection_run_id="picker-tree-real-chain-001",
                source_profile_id="local-json-file",
                source_locator=source_path.as_uri(),
                catalog_node_ids=["lighting"],
            )

            self.assertEqual(result.manifest.task_name, "source_adapter_collection")
            self.assertEqual(result.manifest.summary["adapter_id"], "local-json-file-v1")
            self.assertEqual(result.manifest.summary["selected_catalog_node_ids"], ["lighting"])
            self.assertEqual(result.manifest.summary["products"][0]["name"], "Example lamp")
            self.assertEqual(controller.state.task.status, "succeeded")
            self.assertEqual(controller.state.result.source_profile_id, "local-json-file")

    def test_tree_renders_labels_and_returns_only_checked_internal_ids(self) -> None:
        tree = _Tree()
        nodes = [
            {
                "source_profile_id": "local-json-file",
                "catalog_node_id": "home",
                "display_name": "Home",
                "parent_catalog_node_id": None,
                "locator": None,
            },
            {
                "source_profile_id": "local-json-file",
                "catalog_node_id": "lighting",
                "display_name": "Lighting",
                "parent_catalog_node_id": "home",
                "locator": None,
            },
        ]

        populate_source_catalog_tree_widget(tree, _QtWidgets, _Qt, nodes, [])

        self.assertEqual(tree.headers, ["Раздел каталога", "Вложенность"])
        self.assertEqual([item.labels[0] for item in tree.items], ["Home"])
        self.assertEqual(tree.items[0].children[0].labels[0], "Lighting")
        tree.items[0].children[0].setCheckState(0, _CheckState.Checked)
        self.assertEqual(collect_checked_source_catalog_node_ids(tree, _Qt), ["lighting"])

    def test_file_picker_uses_canonical_uri_and_pure_inspection_handoff(self) -> None:
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "catalog.json"
            source_path.write_text(json.dumps(_catalog_document()), encoding="utf-8")
            _FileDialog.selected_path = str(source_path)
            shell = _PickerShell()

            DesktopLauncherShell._on_choose_source_file(cast(DesktopLauncherShell, shell))

        self.assertEqual(shell.source_locator_input.text(), source_path.as_uri())
        self.assertEqual(
            shell.controller.events,
            [
                f"build:local-json-file:{source_path.as_uri()}",
                "begin:local-json-file",
                "refresh",
                "submit-worker",
            ],
        )
        background_action = cast(Callable[[], object], shell.background_action)
        outcome = background_action()
        json.dumps(outcome)
        self.assertNotIn("apply:local-json-file", shell.controller.events)
        finished_callback = cast(Callable[[object], None], shell.finished_callback)
        finished_callback(outcome)
        self.assertEqual(
            shell.controller.events[-2:],
            ["apply:local-json-file", "refresh"],
        )


def _catalog_document() -> dict[str, object]:
    return {
        "format": "parserriba-local-catalog-v1",
        "observed_at": "2026-08-15T00:00:00Z",
        "catalog_nodes": [
            {"catalog_node_id": "home", "display_name": "Home"},
            {
                "catalog_node_id": "lighting",
                "display_name": "Lighting",
                "parent_catalog_node_id": "home",
            },
        ],
        "products": [
            {
                "observation_id": "lamp-observation",
                "source_product_id": "lamp-source",
                "normalized_product_id": "lamp-normalized",
                "catalog_node_id": "lighting",
                "name": "Example lamp",
                "source_fields": {"title": "Example lamp"},
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
