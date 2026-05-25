import json

from models.catalog_discovery import DiscoveryNode, SiteProfileVersion
from utils.discovery_profile_snapshot import DiscoveryProfileSnapshotWriter


def test_discovery_profile_snapshot_writer_persists_json_snapshot(tmp_path) -> None:
    writer = DiscoveryProfileSnapshotWriter(tmp_path)
    profile = SiteProfileVersion(
        profile_id="profile-1",
        version_id="version-7",
        shop_slug="pyaterochka",
        site_url="https://5ka.ru",
        run_id="run-7",
        primary_root_ids=["fish-root"],
        nodes=[DiscoveryNode(node_id="fish-root", label_ru="Рыба")],
        notes=["saved"],
    )

    path = writer.write_snapshot(profile)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path == tmp_path / "pyaterochka" / "profiles" / "version-7.json"
    assert payload["profile_id"] == "profile-1"
    assert payload["version_id"] == "version-7"
    assert payload["nodes"][0]["label_ru"] == "Рыба"
