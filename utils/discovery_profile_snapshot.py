"""JSON snapshot writer for persisted discovery profiles."""

from __future__ import annotations

from pathlib import Path

from models.catalog_discovery import SiteProfileVersion


class DiscoveryProfileSnapshotWriter:
    """Write readable JSON snapshots for manual profile inspection."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)

    def write_snapshot(self, profile: SiteProfileVersion) -> Path:
        """Persist one profile snapshot under the shop profile directory."""
        target_dir = self.base_dir / profile.shop_slug / "profiles"
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{profile.version_id}.json"
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return path
