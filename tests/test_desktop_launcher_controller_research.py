from pathlib import Path

from launcher.desktop_controller import DesktopLauncherController
from launcher.desktop_user_messages import task_running_message
from models.task_actor import RunManifest
from utils.local_task_adapter import build_local_task_process_result


def test_desktop_launcher_controller_running_message_is_localized(tmp_path: Path) -> None:
    seen_message = ""

    def fake_report_runner(**kwargs):
        nonlocal seen_message
        controller = kwargs.pop("_controller_ref")
        seen_message = controller.state.task.message
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="store_report_export",
                shop="pyaterochka",
                intent="fish_catalog",
                status="ok",
                artifact_paths={},
                summary={},
            ),
            stderr="",
        )

    controller = DesktopLauncherController(root_dir=tmp_path, fish_report_runner=fake_report_runner)
    controller.set_selection(intent="fish_catalog", categories=["Рыба"])
    original_runner = controller.fish_report_runner

    def wrapped_runner(**kwargs):
        return original_runner(_controller_ref=controller, **kwargs)

    controller.fish_report_runner = wrapped_runner
    controller.run_selected_report_export()

    assert seen_message == task_running_message("store_report_export")


def test_desktop_launcher_controller_syncs_live_research_state(tmp_path: Path) -> None:
    def fake_onboarding_runner(**kwargs):
        del kwargs
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="site_onboarding_discovery",
                shop="pyaterochka",
                intent="fish_catalog",
                status="runtime_ready",
                artifact_paths={},
                summary={
                    "research_mode": "live",
                    "current_phase": "build_tree",
                    "active_profile_id": "profile-1",
                    "active_profile_version_id": "version-2",
                    "streamed_categories": ["Рыба", "Морепродукты"],
                    "category_tree": [{"name": "Рыба", "url": "https://example.test/fish"}],
                },
            )
        )

    controller = DesktopLauncherController(root_dir=tmp_path, onboarding_runner=fake_onboarding_runner)
    controller.run_onboarding_discovery(site_url="https://5ka.ru")

    assert controller.state.research.mode == "live"
    assert controller.state.research.current_status == "runtime_ready"
    assert controller.state.research.current_phase == "build_tree"
    assert controller.state.research.active_profile_id == "profile-1"
    assert controller.state.research.active_profile_version_id == "version-2"
    assert controller.state.research.streamed_categories == ["Рыба", "Морепродукты"]


def test_desktop_launcher_controller_syncs_quiet_research_state_without_stream(tmp_path: Path) -> None:
    def fake_onboarding_runner(**kwargs):
        del kwargs
        return build_local_task_process_result(
            manifest=RunManifest(
                task_name="site_onboarding_discovery",
                shop="pyaterochka",
                intent="fish_catalog",
                status="discovery_only",
                artifact_paths={},
                summary={
                    "research_mode": "quiet",
                    "current_phase": "persist_profile",
                    "active_profile_id": "profile-9",
                    "active_profile_version_id": "version-10",
                    "streamed_categories": [],
                },
            )
        )

    controller = DesktopLauncherController(root_dir=tmp_path, onboarding_runner=fake_onboarding_runner)
    controller.run_onboarding_discovery(site_url="https://5ka.ru")

    assert controller.state.research.mode == "quiet"
    assert controller.state.research.current_status == "discovery_only"
    assert controller.state.research.current_phase == "persist_profile"
    assert controller.state.research.active_profile_id == "profile-9"
    assert controller.state.research.active_profile_version_id == "version-10"
    assert controller.state.research.streamed_categories == []
