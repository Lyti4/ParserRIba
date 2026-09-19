from __future__ import annotations

import asyncio
from types import ModuleType

import pytest

from utils import local_task_registry


def test_cloak_install_task_is_registered_and_invokes_installer(monkeypatch, tmp_path) -> None:
    called = []
    module = ModuleType("scripts.install_cloakbrowser_runtime")
    module.provision_cloakbrowser_runtime = lambda: called.append(True) or 0
    monkeypatch.setitem(__import__("sys").modules, "scripts.install_cloakbrowser_runtime", module)

    task = local_task_registry._TASKS["cloak_runtime_install"]
    manifest = asyncio.run(task.run_func(task_input={}, root_dir=tmp_path))

    assert called == [True]
    assert manifest.task_name == "cloak_runtime_install"
    assert manifest.summary == {"runtime": "cloak", "binary_ready": True}


def test_cloak_install_task_fails_without_leaking_sdk_error(monkeypatch, tmp_path) -> None:
    module = ModuleType("scripts.install_cloakbrowser_runtime")
    module.provision_cloakbrowser_runtime = lambda: 2
    monkeypatch.setitem(__import__("sys").modules, "scripts.install_cloakbrowser_runtime", module)

    task = local_task_registry._TASKS["cloak_runtime_install"]
    with pytest.raises(RuntimeError, match="Cloak runtime provisioning failed") as caught:
        asyncio.run(task.run_func(task_input={}, root_dir=tmp_path))
    assert "sentinel" not in str(caught.value)
