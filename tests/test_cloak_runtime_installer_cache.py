from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

from scripts import install_cloakbrowser_runtime as installer


def _fake_sdk(monkeypatch, *, cache: Path, returned: Path, installed_before: bool = False) -> None:
    module = ModuleType("cloakbrowser")

    def binary_info():
        return {"installed": installed_before, "binary_path": str(returned)}

    def ensure_binary():
        assert Path(os.environ["CLOAKBROWSER_CACHE_DIR"]) == cache
        returned.parent.mkdir(parents=True, exist_ok=True)
        returned.write_bytes(b"MZfake")
        return returned

    module.binary_info = binary_info
    module.ensure_binary = ensure_binary
    monkeypatch.setitem(sys.modules, "cloakbrowser", module)


def test_installer_honors_caller_cache_and_verifies_returned_binary(monkeypatch, tmp_path: Path) -> None:
    supplied_cache = tmp_path / "ci-cache"
    default_cache = tmp_path / "project-cache"
    returned = supplied_cache / "chromium-pro.exe"
    monkeypatch.setenv("CLOAKBROWSER_CACHE_DIR", str(supplied_cache))
    monkeypatch.setattr(installer, "CLOAK_CACHE_DIR", default_cache)
    _fake_sdk(monkeypatch, cache=supplied_cache, returned=returned)

    assert installer.main() == 0
    assert returned.is_file()
    assert not default_cache.exists()
    assert Path(os.environ["CLOAKBROWSER_CACHE_DIR"]) == supplied_cache


def test_installer_rejects_missing_or_non_file_returned_binary(monkeypatch, tmp_path: Path) -> None:
    supplied_cache = tmp_path / "ci-cache"
    returned = supplied_cache / "missing.exe"
    monkeypatch.setenv("CLOAKBROWSER_CACHE_DIR", str(supplied_cache))
    module = ModuleType("cloakbrowser")
    module.binary_info = lambda: {"installed": False, "binary_path": str(returned)}
    module.ensure_binary = lambda: returned
    monkeypatch.setitem(sys.modules, "cloakbrowser", module)

    assert installer.main() == 2


@pytest.mark.parametrize("kind", ["camoufox", "cloak"])
def test_consumer_preflight_never_provisions_binary(monkeypatch, kind: str) -> None:
    from utils.browser_runtime import check_browser_runtime

    if kind == "cloak":
        monkeypatch.setattr(installer, "main", lambda: (_ for _ in ()).throw(AssertionError("must not provision")))
    availability = check_browser_runtime(kind)
    assert availability.kind == kind
