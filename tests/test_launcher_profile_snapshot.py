import json
from pathlib import Path

from models.launcher_state import LauncherAppState
from utils.launcher_profile_snapshot import build_launcher_profile_snapshot, write_launcher_profile_snapshot


def test_build_launcher_profile_snapshot_keeps_workspace_sections() -> None:
    state = _build_state()

    payload = build_launcher_profile_snapshot(
        state,
        task_name="store_report_export",
        snapshot_id="snapshot-1",
    )

    assert payload is not None
    assert payload["snapshot_id"] == "snapshot-1"
    assert payload["profile"]["site_url"] == "https://5ka.ru"
    assert payload["catalog"]["selected_node_urls"] == ["https://5ka.ru/catalog/fish/"]
    assert payload["products"]["products_count"] == 2
    assert payload["dynamic_filters"]["counts"] == {"brands": {"Nord": 2}}
    assert payload["result"]["artifact_paths"]["excel_path"].endswith("report.xlsx")
    assert "launcher_view" not in payload["result"]


def test_write_launcher_profile_snapshot_writes_history_and_latest(tmp_path: Path) -> None:
    state = _build_state()

    path = write_launcher_profile_snapshot(
        state,
        base_dir=tmp_path,
        task_name="store_report_export",
        snapshot_id="snapshot-1",
    )

    assert path == tmp_path / "pyaterochka" / "profile-1" / "snapshot-1.json"
    assert path is not None
    latest_path = path.parent / "latest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
    assert payload["profile"]["profile_id"] == "profile-1"
    assert latest_payload["snapshot_id"] == "snapshot-1"


def test_build_launcher_profile_snapshot_skips_empty_profile() -> None:
    assert build_launcher_profile_snapshot(LauncherAppState()) is None


def _build_state() -> LauncherAppState:
    return LauncherAppState(
        profile={
            "profile_id": "profile-1",
            "profile_version_id": "version-2",
            "site_url": "https://5ka.ru",
            "domain": "5ka.ru",
            "shop": "pyaterochka",
            "diagnostics": {"known_backend": True},
        },
        catalog={
            "catalog_type": "category_tree",
            "full_tree": [{"name": "Каталог", "children": [{"name": "Рыба"}]}],
            "full_links": [{"name": "Рыба", "url": "https://5ka.ru/catalog/fish/"}],
        },
        selection={
            "categories": ["Рыба"],
            "selected_catalog_nodes": [{"name": "Рыба", "url": "https://5ka.ru/catalog/fish/"}],
            "selected_product_ids": ["fish-1"],
        },
        products={
            "products_count": 2,
            "source_categories": ["Рыба"],
            "selected_product_ids": ["fish-1"],
            "json_path": "C:/reports/products.json",
        },
        dynamic_filters={
            "counts": {"brands": {"Nord": 2}},
            "available_filters": {"brands": {"kind": "facet"}},
        },
        result={
            "summary": {"products_count": 2},
            "artifact_paths": {"excel_path": "C:/reports/report.xlsx"},
            "products_count": 2,
            "source_profile_id": "profile-1",
        },
    )
