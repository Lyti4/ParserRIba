"""Persistent Camoufox profile cleanup helpers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

KNOWN_CONTENT_BLOCKER_EXTENSION_IDS = frozenset({"uBlock0@raymondhill.net"})


def disable_known_content_blockers_in_profile(profile_dir: Path) -> None:
    """Disable persisted content-blocker influence without deleting profile state."""
    _remove_extension_preferences(profile_dir / "extension-preferences.json")
    _remove_extension_settings(profile_dir / "extension-settings.json")


def _remove_extension_preferences(path: Path) -> None:
    data = _read_profile_json(path)
    if not isinstance(data, dict):
        return
    changed = False
    for extension_id in KNOWN_CONTENT_BLOCKER_EXTENSION_IDS:
        if extension_id in data:
            data.pop(extension_id, None)
            changed = True
    if changed:
        _write_profile_json_with_backup(path, data)
        logger.info("Disabled persisted content-blocker preferences in {}", path)


def _remove_extension_settings(path: Path) -> None:
    data = _read_profile_json(path)
    if not isinstance(data, dict):
        return
    prefs = data.get("prefs")
    if not isinstance(prefs, dict):
        return
    changed = False
    empty_pref_keys: list[str] = []
    for pref_key, pref_state in prefs.items():
        if not isinstance(pref_state, dict):
            continue
        precedence_list = pref_state.get("precedenceList")
        if not isinstance(precedence_list, list):
            continue
        filtered = [
            item
            for item in precedence_list
            if str(item.get("id", "")) not in KNOWN_CONTENT_BLOCKER_EXTENSION_IDS
        ]
        if len(filtered) == len(precedence_list):
            continue
        pref_state["precedenceList"] = filtered
        changed = True
        if not filtered:
            empty_pref_keys.append(pref_key)
    for pref_key in empty_pref_keys:
        prefs.pop(pref_key, None)
    if changed:
        _write_profile_json_with_backup(path, data)
        logger.info("Disabled persisted content-blocker settings in {}", path)


def _read_profile_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read profile JSON {}: {}", path, exc)
        return None


def _write_profile_json_with_backup(path: Path, data: Any) -> None:
    if path.exists():
        backup_path = path.with_name(f"{path.name}.{_profile_backup_suffix()}.bak")
        if not backup_path.exists():
            shutil.copy2(path, backup_path)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def _profile_backup_suffix() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")
