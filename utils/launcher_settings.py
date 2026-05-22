"""Local settings persistence for the desktop launcher."""

from __future__ import annotations

import json
from pathlib import Path

from models.launcher_state import LauncherAppState, LauncherSettingsState


class LauncherSettingsStore:
    """Persist and restore local launcher settings."""

    def __init__(self, settings_path: Path | str) -> None:
        self.settings_path = Path(settings_path)

    def load(self) -> LauncherSettingsState:
        """Load settings from disk or return defaults."""
        payload = self._load_json()
        settings_payload = payload.get("settings")
        if isinstance(settings_payload, dict):
            return LauncherSettingsState(**settings_payload)
        return LauncherSettingsState()

    def save(self, settings: LauncherSettingsState) -> Path:
        """Persist settings to disk in UTF-8 JSON."""
        payload = self._load_json()
        payload["settings"] = settings.model_dump(mode="json")
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.settings_path

    def load_app_state(self) -> LauncherAppState:
        """Load a fuller launcher state snapshot when available."""
        payload = self._load_json()
        if not payload:
            return LauncherAppState()
        return LauncherAppState(**payload)

    def save_app_state(self, state: LauncherAppState) -> Path:
        """Persist the full launcher state snapshot."""
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return self.settings_path

    def _load_json(self) -> dict:
        if not self.settings_path.exists():
            return {}
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if isinstance(payload, dict):
            return payload
        return {}
