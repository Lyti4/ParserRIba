import json
from pathlib import Path

from utils.site_onboarding import resume_site_onboarding, run_site_onboarding


def test_run_site_onboarding_for_known_site_creates_runtime_ready_session(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    original_probe = site_onboarding._run_catalog_research_sync
    site_onboarding._run_catalog_research_sync = lambda *args, **kwargs: _build_research_result(
        shop_slug="pyaterochka",
        site_url="https://5ka.ru/catalog",
        status_code=200,
        surface_type="category_tree",
        categories=[
            ("Рыба", "https://5ka.ru/catalog/ryba--251C13077/"),
            ("Морепродукты", "https://5ka.ru/catalog/moreprodukty--251C13078/"),
            ("Икра и закуски", "https://5ka.ru/catalog/ikra-zakuski--251C13080/"),
            ("Котлеты и фарш", "https://5ka.ru/catalog/kotlety-farsh--251C13079/"),
        ],
        streamed_categories=["Рыба", "Морепродукты"],
    )
    try:
        result = run_site_onboarding(site_url="https://5ka.ru", root_dir=tmp_path)
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert result.shop_slug == "pyaterochka"
    assert result.status == "runtime_ready"
    assert len(result.category_tree) >= 2
    assert result.active_profile_id.startswith("profile:")
    assert result.active_profile_version_id == "version-1"
    assert result.streamed_categories == ["Рыба", "Морепродукты"]
    assert result.research_mode == "live"
    assert result.current_phase == "build_tree"
    assert Path(result.artifact_paths.session_state_path).exists()
    assert Path(result.artifact_paths.kb_draft_path).exists()
    assert result.diagnostics_summary["catalog_discovery"]["surface_type"] == "category_tree"
    assert result.diagnostics_summary["category_source"] == "browser_discovery"
    assert result.diagnostics_summary["full_catalog_count"] == 4
    assert result.diagnostics_summary["full_catalog_links"][0]["url"] == "https://5ka.ru/catalog/ryba--251C13077/"
    assert result.diagnostics_summary["full_catalog_tree"][0]["name"] == "Каталог"
    assert result.diagnostics_summary["full_catalog_tree"][0]["children"][0]["url"] == "https://5ka.ru/catalog/ryba--251C13077/"
    assert result.diagnostics_summary["profile_snapshot_path"].endswith("version-1.json")


def test_run_site_onboarding_for_known_site_falls_back_to_kb_categories_after_browser_research(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    original_probe = site_onboarding._run_catalog_research_sync
    site_onboarding._run_catalog_research_sync = lambda *args, **kwargs: _build_research_result(
        shop_slug="pyaterochka",
        site_url="https://5ka.ru/",
        status_code=200,
        surface_type="product_listing",
        product_links=[("Товар", "https://5ka.ru/product/fasol--39419/")],
    )
    try:
        result = run_site_onboarding(site_url="https://5ka.ru", root_dir=tmp_path)
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert result.status == "runtime_ready"
    assert len(result.category_tree) >= 2
    assert result.diagnostics_summary["catalog_discovery"]["surface_type"] == "product_listing"
    assert result.diagnostics_summary["category_source"] == "kb_fallback"


def test_run_site_onboarding_for_unknown_site_creates_scaffolds(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    result = run_site_onboarding(site_url="https://unknown-store.example", root_dir=tmp_path)
    assert result.shop_slug == "unknown-store_example"
    assert result.status == "scaffold_ready"
    assert result.category_tree == []
    assert Path(result.artifact_paths.backend_stub_path).exists()
    assert Path(result.artifact_paths.capture_stub_path).exists()


def test_run_site_onboarding_for_known_non_runtime_site_creates_discovery_only_session(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    original_probe = site_onboarding._run_catalog_research_sync
    site_onboarding._run_catalog_research_sync = lambda *args, **kwargs: _build_research_result(
        shop_slug="verny",
        site_url="https://www.verno-info.ru/products",
        status_code=200,
        surface_type="pdf_flipbook",
        documents=[("pdf", "https://www.verno-info.ru/catalog.pdf")],
    )
    try:
        result = run_site_onboarding(site_url="https://www.verno-info.ru/products", root_dir=tmp_path)
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert result.shop_slug == "verny"
    assert result.status == "discovery_only"
    assert result.category_tree == []
    assert result.diagnostics_summary["catalog_discovery"]["surface_type"] == "pdf_flipbook"


def test_run_site_onboarding_for_kb_backed_planned_site_uses_category_tree(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    source = Path("knowledge_base/auchan.md").read_text(encoding="utf-8")
    (tmp_path / "knowledge_base" / "auchan.md").write_text(source, encoding="utf-8")
    import utils.site_onboarding as site_onboarding

    original_probe = site_onboarding._run_catalog_research_sync
    site_onboarding._run_catalog_research_sync = lambda *args, **kwargs: _build_research_result(
        shop_slug="auchan",
        site_url="https://www.auchan.ru/catalog",
        status_code=401,
        surface_type="blocked",
        blocked_hint=True,
        partial=True,
    )
    try:
        result = run_site_onboarding(site_url="https://www.auchan.ru/catalog", root_dir=tmp_path)
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert result.shop_slug == "auchan"
    assert result.status == "discovery_only"
    assert len(result.category_tree) >= 2
    assert result.diagnostics_summary["catalog_discovery"]["surface_type"] == "blocked"


def test_run_site_onboarding_for_planned_site_without_kb_has_empty_tree(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    original_probe = site_onboarding._run_catalog_research_sync
    site_onboarding._run_catalog_research_sync = lambda *args, **kwargs: _build_research_result(
        shop_slug="metro",
        site_url="https://online.metro-cc.ru/",
        status_code=200,
        surface_type="category_tree",
        categories=[("Рыба и морепродукты", "https://online.metro-cc.ru/category/ryba")],
        product_links=[("Лосось", "https://online.metro-cc.ru/products/salmon-123")],
        phase_events=[],
    )
    try:
        result = run_site_onboarding(site_url="https://online.metro-cc.ru/", root_dir=tmp_path)
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert result.shop_slug == "metro"
    assert result.status == "discovery_only"
    assert len(result.category_tree) == 1
    assert result.diagnostics_summary["intent_category_links"] == [
        {"name": "Рыба и морепродукты", "url": "https://online.metro-cc.ru/category/ryba"}
    ]


def test_run_site_onboarding_can_pause_and_resume(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    original_probe = site_onboarding._run_catalog_research_sync
    site_onboarding._run_catalog_research_sync = lambda *args, **kwargs: _build_research_result(
        shop_slug="pyaterochka",
        site_url="https://5ka.ru/catalog",
        status_code=200,
        surface_type="category_tree",
        categories=[("Рыба", "https://5ka.ru/catalog/ryba--251C13077/")],
    )
    try:
        paused = run_site_onboarding(
            site_url="https://5ka.ru",
            root_dir=tmp_path,
            require_operator_confirmation=True,
        )
        resumed = resume_site_onboarding(session_id=paused.session_id, root_dir=tmp_path)
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert paused.status == "needs_operator"
    assert paused.active_profile_id == ""
    assert resumed.session_id == paused.session_id
    assert resumed.status == "runtime_ready"
    assert resumed.active_profile_id.startswith("profile:")
    saved = json.loads(Path(resumed.artifact_paths.session_state_path).read_text(encoding="utf-8"))
    assert saved["status"] == "runtime_ready"


def test_run_site_onboarding_persists_selected_categories(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    original_probe = site_onboarding._run_catalog_research_sync
    site_onboarding._run_catalog_research_sync = lambda *args, **kwargs: _build_research_result(
        shop_slug="pyaterochka",
        site_url="https://5ka.ru/catalog",
        status_code=200,
        surface_type="category_tree",
        categories=[("Рыба", "https://5ka.ru/catalog/ryba--251C13077/")],
    )
    try:
        result = run_site_onboarding(
            site_url="https://5ka.ru",
            root_dir=tmp_path,
            selected_categories=["Рыба", "Морепродукты"],
        )
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    saved = json.loads(Path(result.artifact_paths.session_state_path).read_text(encoding="utf-8"))
    assert result.selected_categories == ["Рыба", "Морепродукты"]
    assert saved["selected_categories"] == ["Рыба", "Морепродукты"]
    assert saved["active_profile_id"].startswith("profile:")
    assert saved["active_profile_version_id"] == "version-1"
    assert saved["streamed_categories"] == ["Рыба"]
    assert saved["research_mode"] == "live"
    assert saved["current_phase"] == "build_tree"


def test_run_site_onboarding_passes_browser_runtime_flags(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    import utils.site_onboarding as site_onboarding

    captured: dict[str, object] = {}
    original_probe = site_onboarding._run_catalog_research_sync

    def fake_probe(*args, **kwargs):
        captured.update(kwargs)
        return _build_research_result(
            shop_slug="pyaterochka",
            site_url="https://5ka.ru/catalog",
            status_code=200,
            surface_type="category_tree",
            categories=[("Рыба", "https://5ka.ru/catalog/ryba--251C13077/")],
        )

    site_onboarding._run_catalog_research_sync = fake_probe
    try:
        run_site_onboarding(
            site_url="https://5ka.ru",
            root_dir=tmp_path,
            headless=True,
            manual_wait=True,
            listen_seconds=9,
        )
    finally:
        site_onboarding._run_catalog_research_sync = original_probe

    assert captured == {
        "headless": True,
        "manual_wait": True,
        "listen_seconds": 9,
        "research_mode": "live",
    }


def _build_research_result(
    *,
    shop_slug: str,
    site_url: str,
    status_code: int,
    surface_type: str,
    categories: list[tuple[str, str]] | None = None,
    product_links: list[tuple[str, str]] | None = None,
    documents: list[tuple[str, str]] | None = None,
    streamed_categories: list[str] | None = None,
    phase_events: list[dict[str, str]] | None = None,
    blocked_hint: bool = False,
    partial: bool = False,
):
    from models.catalog_discovery import (
        CatalogDiscoveryResult,
        CategoryEvidence,
        DiscoveryPhaseEvent,
        DocumentEvidence,
        ProductLinkEvidence,
        SiteProfileVersion,
    )
    from utils.catalog_tree_discovery.runner import CatalogTreeDiscoveryRunResult

    return CatalogTreeDiscoveryRunResult(
        profile=SiteProfileVersion(
            profile_id=f"profile:{shop_slug}",
            version_id="version-1",
            shop_slug=shop_slug,
            site_url=site_url,
            run_id="run-1",
            primary_root_ids=["category-1"] if categories else [],
            nodes=[],
            edges=[],
            notes=["partial_research_due_to_challenge"] if partial else [],
        ),
        phase_events=[
            DiscoveryPhaseEvent(
                phase=item["phase"],
                status=item["status"],
                message_ru=item["message_ru"],
                discovered_categories=list(item.get("discovered_categories") or []),
            )
            for item in (
                phase_events
                or [
                    {
                        "phase": "build_tree",
                        "status": "completed",
                        "message_ru": "Подготовка дерева",
                        "discovered_categories": list(streamed_categories or []),
                    }
                ]
            )
        ],
        streamed_categories=list(streamed_categories if streamed_categories is not None else [name for name, _ in (categories or [])[:1]]),
        current_phase="build_tree",
        mode="live",
        partial=partial,
        catalog_discovery=CatalogDiscoveryResult(
            reachable=200 <= status_code < 400,
            status_code=status_code,
            final_url=site_url,
            surface_type=surface_type,
            blocked_hint=blocked_hint,
            category_links=[CategoryEvidence(name=name, url=url) for name, url in (categories or [])],
            product_links=[ProductLinkEvidence(name=name, url=url) for name, url in (product_links or [])],
            documents=[DocumentEvidence(kind=kind, url=url) for kind, url in (documents or [])],
        ),
        limits={"max_repeat_urls": 3, "max_empty_branches": 5, "max_discovery_depth": 8},
    )


def _prepare_root(root_dir: Path) -> None:
    (root_dir / "data").mkdir(parents=True, exist_ok=True)
    (root_dir / "knowledge_base").mkdir(parents=True, exist_ok=True)
    source = Path("knowledge_base/pyaterochka.md").read_text(encoding="utf-8")
    (root_dir / "knowledge_base" / "pyaterochka.md").write_text(source, encoding="utf-8")
