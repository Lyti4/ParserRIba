from __future__ import annotations

import os
import subprocess

import pytest

from utils.local_task_adapter import run_local_task_subprocess


def test_local_task_subprocess_scopes_operation_env_without_mutating_parent(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(args[0], 0, stdout='{"task_name":"x","shop":"","intent":"","status":"ok","started_at":"2026-01-01T00:00:00","finished_at":"2026-01-01T00:00:00","summary":{}}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.delenv("CLOAKBROWSER_LICENSE_KEY", raising=False)
    run_local_task_subprocess(task_name="x", task_input={}, root_dir=tmp_path, operation_env={"CLOAKBROWSER_LICENSE_KEY": "sentinel"})
    assert captured["env"]["CLOAKBROWSER_LICENSE_KEY"] == "sentinel"
    assert "CLOAKBROWSER_LICENSE_KEY" not in os.environ
    assert "sentinel" not in captured["input"]


@pytest.mark.parametrize("operation_env", [None, {"NON_SECRET_FLAG": "ok"}])
def test_local_task_failure_redacts_inherited_sensitive_child_env(monkeypatch, tmp_path, operation_env) -> None:
    secret = "synthetic-license-sentinel"
    proxy = "http://synthetic-proxy-sentinel"

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(9, args[0], output=f"stdout {secret}", stderr=f"stderr {proxy}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("CLOAKBROWSER_LICENSE_KEY", secret)
    monkeypatch.setenv("HTTPS_PROXY", proxy)

    with pytest.raises(RuntimeError) as caught:
        run_local_task_subprocess(task_name="x", task_input={}, root_dir=tmp_path, operation_env=operation_env)

    message = str(caught.value)
    assert secret not in message
    assert proxy not in message
    assert "[redacted]" in message


def test_local_task_failure_redacts_explicit_neutral_operation_env(monkeypatch, tmp_path) -> None:
    secret = "synthetic-neutral-sentinel"

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(9, args[0], stderr=f"failure {secret}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError) as caught:
        run_local_task_subprocess(task_name="x", task_input={}, root_dir=tmp_path, operation_env={"CUSTOM_OPTION": secret})

    assert secret not in str(caught.value)
    assert "[redacted]" in str(caught.value)


def test_zero_exit_invalid_manifest_does_not_echo_effective_secret(monkeypatch, tmp_path) -> None:
    secret = "synthetic-zero-exit-secret"

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=secret, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("CLOAKBROWSER_LICENSE_KEY", secret)
    with pytest.raises(ValueError) as caught:
        run_local_task_subprocess(task_name="x", task_input={}, root_dir=tmp_path)
    assert secret not in str(caught.value)
