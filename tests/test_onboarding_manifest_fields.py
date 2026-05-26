from pathlib import Path

from utils.local_task_registry import run_local_task


async def test_onboarding_manifest_includes_launcher_facing_discovery_fields(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    from models.catalog_discovery import CatalogDiscoveryResult, CategoryEvidence, SiteProfileVersion
    from utils.catalog_tree_discovery.runner import CatalogTreeDiscoveryRunResult

    original_probe = site_onboarding._run_catalog_research_sync

    def fake_probe(*args, **kwargs):
        del kwargs
        assert args[1] is None
        return CatalogTreeDiscoveryRunResult(
            profile=SiteProfileVersion(
                profile_id="profile:unknown-store_example",
                version_id="version-1",
                shop_slug="unknown-store_example",
                site_url="https://unknown-store.example/catalog",
                run_id="run-1",
                primary_root_ids=["category-1"],
                nodes=[],
                edges=[],
                notes=[],
            ),
            phase_events=[],
            streamed_categories=["Рыба"],
            current_phase="build_tree",
            mode="live",
            partial=False,
            catalog_discovery=CatalogDiscoveryResult(
                reachable=True,
                status_code=200,
                final_url="https://unknown-store.example/catalog",
                surface_type="category_tree",
                category_links=[
                    CategoryEvidence(name="Рыба", url="https://unknown-store.example/catalog/fish"),
                ],
            ),
            limits={"max_repeat_urls": 3, "max_empty_branches": 5, "max_discovery_depth": 8},
        )

    site_onboarding._run_catalog_research_sync = fake_probe
    try:
        manifest = await run_local_task(
            "site_onboarding_discovery",
            {
                "site_url": "https://unknown-store.example",
                "intent": "fish_catalog",
                "selected_categories": ["Рыба"],
            },
            root_dir=tmp_path,
        )
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert manifest.task_name == "site_onboarding_discovery"
    assert manifest.status == "discovery_only"
    assert manifest.summary["category_tree"][0]["url"] == "https://unknown-store.example/catalog/fish"
    assert manifest.summary["selected_categories"] == ["Рыба"]
    assert manifest.summary["catalog_discovery"]["surface_type"] == "category_tree"
    assert manifest.summary["intent_category_links"] == [{"name": "Рыба", "url": "https://unknown-store.example/catalog/fish"}]
    assert manifest.summary["diagnostics_summary"]["known_backend"] is False
    assert manifest.summary["active_profile_id"] == "profile:unknown-store_example"
    assert manifest.summary["active_profile_version_id"] == "version-1"
    assert manifest.summary["streamed_categories"] == ["Рыба"]
    assert manifest.summary["research_mode"] == "live"
    assert manifest.summary["current_phase"] == "build_tree"
    assert manifest.summary["partial_research"] is False


def _prepare_root(root_dir: Path) -> None:
    (root_dir / "data").mkdir(parents=True, exist_ok=True)
    (root_dir / "knowledge_base").mkdir(parents=True, exist_ok=True)
    source = Path("knowledge_base/pyaterochka.md").read_text(encoding="utf-8")
    (root_dir / "knowledge_base" / "pyaterochka.md").write_text(source, encoding="utf-8")
