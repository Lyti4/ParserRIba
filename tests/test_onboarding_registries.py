from pathlib import Path

from utils.onboarding_artifacts import get_artifact_generator
from utils.protection_strategies import get_protection_strategy
from utils.store_catalog_registry import match_known_store_site, resolve_catalog_research_site


def test_get_artifact_generator_returns_default(tmp_path: Path) -> None:
    generator = get_artifact_generator("default")
    paths = generator(tmp_path, "demo_store")

    assert paths.runtime_report_dir.endswith("demo_store")
    assert Path(paths.kb_draft_path).exists()


def test_get_protection_strategy_returns_pause_for_operator() -> None:
    strategy = get_protection_strategy("pause_for_operator")

    assert strategy.name == "pause_for_operator"
    assert strategy.pause_for_operator is True


def test_match_known_store_site_returns_discovery_only_profile_for_verny() -> None:
    profile = match_known_store_site("https://www.verno-info.ru/products")

    assert profile is not None
    assert profile.shop == "verny"
    assert profile.onboarding_status == "discovery_only"
    assert profile.export_backend_shop is None


def test_match_known_store_site_returns_kb_backed_profile_for_auchan() -> None:
    profile = match_known_store_site("https://www.auchan.ru/catalog")

    assert profile is not None
    assert profile.shop == "auchan"
    assert profile.onboarding_status == "discovery_only"
    assert profile.export_backend_shop is None
    assert profile.kb_shop == "auchan"


def test_match_known_store_site_returns_planned_profile_for_metro() -> None:
    profile = match_known_store_site("https://online.metro-cc.ru/")

    assert profile is not None
    assert profile.shop == "metro"
    assert profile.onboarding_status == "discovery_only"
    assert profile.export_backend_shop is None
    assert profile.kb_shop is None


def test_resolve_catalog_research_site_prefers_explicit_shop_hint() -> None:
    profile = resolve_catalog_research_site("https://unknown-store.example", "pyaterochka")

    assert profile is not None
    assert profile.shop == "pyaterochka"
    assert profile.export_backend_shop == "pyaterochka"
