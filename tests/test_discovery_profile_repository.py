from models.catalog_discovery import DiscoveryEdge, DiscoveryNode, RouteHint, SiteProfileVersion
from utils.discovery_profile_repository import SQLiteDiscoveryProfileRepository


def test_discovery_profile_repository_saves_latest_profile_and_history(tmp_path) -> None:
    repository = SQLiteDiscoveryProfileRepository(tmp_path / "profiles.db")
    first = _build_profile(version_id="version-1", run_id="run-1", note="first")
    second = _build_profile(version_id="version-2", run_id="run-2", note="second")

    repository.save_profile_version(first)
    repository.save_profile_version(second)

    latest = repository.get_latest_profile("pyaterochka", "https://5ka.ru")
    versions = repository.list_profile_versions("pyaterochka", "https://5ka.ru")

    assert latest is not None
    assert latest.profile_id == "profile-1"
    assert latest.version_id == "version-2"
    assert latest.notes == ["second"]
    assert [item.version_id for item in versions] == ["version-2", "version-1"]


def test_discovery_profile_repository_returns_empty_results_for_unknown_site(tmp_path) -> None:
    repository = SQLiteDiscoveryProfileRepository(tmp_path / "profiles.db")

    assert repository.get_latest_profile("metro", "https://online.metro-cc.ru") is None
    assert repository.list_profile_versions("metro", "https://online.metro-cc.ru") == []


def _build_profile(*, version_id: str, run_id: str, note: str) -> SiteProfileVersion:
    return SiteProfileVersion(
        profile_id="profile-1",
        version_id=version_id,
        shop_slug="pyaterochka",
        site_url="https://5ka.ru",
        run_id=run_id,
        primary_root_ids=["fish-root"],
        nodes=[
            DiscoveryNode(
                node_id="fish-root",
                label_ru="Рыба",
                canonical_url="https://5ka.ru/catalog/fish",
                route_hints=[RouteHint(kind="api", value="/api/products")],
            ),
            DiscoveryNode(
                node_id="seafood-root",
                label_ru="Морепродукты",
                parent_ids=["fish-root"],
            ),
        ],
        edges=[
            DiscoveryEdge(
                from_node_id="fish-root",
                to_node_id="seafood-root",
            )
        ],
        notes=[note],
    )
