from launcher.desktop_action_state import build_action_enabled_map
from models.launcher_state import LauncherAppState


def test_build_action_enabled_map_requires_categories_for_run_actions() -> None:
    state = LauncherAppState()

    enabled = build_action_enabled_map(state)

    assert enabled["onboarding"] is True
    assert enabled["run_export"] is False
    assert enabled["load_filters"] is False
    assert enabled["build_report"] is False
    assert enabled["save_settings"] is True


def test_build_action_enabled_map_enables_open_actions_from_result_paths() -> None:
    state = LauncherAppState()
    state.selection.categories = ["Рыба"]
    state.result.excel_path = "C:/tmp/report.xlsx"
    state.result.report_dir = "C:/tmp/reports"
    state.result.json_path = "C:/tmp/products.json"

    enabled = build_action_enabled_map(state)

    assert enabled["run_export"] is True
    assert enabled["load_filters"] is True
    assert enabled["build_report"] is True
    assert enabled["open_excel"] is True
    assert enabled["open_folder"] is True
    assert "open_json" not in enabled


def test_build_action_enabled_map_disables_buttons_while_task_is_running() -> None:
    state = LauncherAppState()
    state.selection.categories = ["Рыба"]
    state.task.status = "running"
    state.result.excel_path = "C:/tmp/report.xlsx"

    enabled = build_action_enabled_map(state)

    assert all(value is False for value in enabled.values())
