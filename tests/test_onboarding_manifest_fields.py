from pathlib import Path

from utils.local_task_registry import run_local_task


async def test_onboarding_manifest_includes_launcher_facing_discovery_fields(tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    manifest = await run_local_task(
        "site_onboarding_discovery",
        {
            "site_url": "https://unknown-store.example",
            "intent": "fish_catalog",
            "selected_categories": ["Рыба"],
        },
        root_dir=tmp_path,
    )

    assert manifest.task_name == "site_onboarding_discovery"
    assert manifest.summary["category_tree"] == []
    assert manifest.summary["selected_categories"] == ["Рыба"]
    assert manifest.summary["catalog_discovery"] == {}
    assert manifest.summary["intent_category_links"] == []
    assert manifest.summary["diagnostics_summary"]["known_backend"] is False


def _prepare_root(root_dir: Path) -> None:
    (root_dir / "data").mkdir(parents=True, exist_ok=True)
    (root_dir / "knowledge_base").mkdir(parents=True, exist_ok=True)
    source = Path("knowledge_base/pyaterochka.md").read_text(encoding="utf-8")
    (root_dir / "knowledge_base" / "pyaterochka.md").write_text(source, encoding="utf-8")
