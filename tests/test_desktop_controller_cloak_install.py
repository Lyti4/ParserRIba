from datetime import datetime

from launcher.desktop_controller import DesktopLauncherController
from models.task_actor import RunManifest
from utils.local_task_adapter import LocalTaskProcessResult


def test_controller_runs_cloak_install_without_store_selection(monkeypatch, tmp_path):
    captured = {}

    def fake_run_local_task_subprocess(**kwargs):
        captured.update(kwargs)
        return LocalTaskProcessResult(manifest=RunManifest(task_name="cloak_runtime_install", shop="", intent="", status="ok", started_at=datetime.utcnow(), finished_at=datetime.utcnow(), summary={"runtime": "cloak", "binary_ready": True}))

    monkeypatch.setattr("launcher.desktop_controller.run_local_task_subprocess", fake_run_local_task_subprocess)
    controller = DesktopLauncherController(root_dir=tmp_path)
    result = controller.run_cloak_runtime_install()
    assert result.manifest.task_name == "cloak_runtime_install"
    assert captured["task_name"] == "cloak_runtime_install"
    assert captured["task_input"] == {}
