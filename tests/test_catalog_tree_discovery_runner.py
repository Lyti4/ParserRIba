from types import SimpleNamespace

import pytest

from models.catalog_discovery import CatalogDiscoveryResult, CategoryEvidence
from utils.catalog_discovery import summarize_catalog_discovery
from utils.catalog_tree_discovery.entrypoint_collectors import (
    collect_catalog_entrypoints_from_html,
)
from utils.catalog_tree_discovery.graph_builder import build_discovery_graph
from utils.catalog_tree_discovery.listing_validator import classify_catalog_surface
from utils.catalog_tree_discovery.phase_events import make_phase_event
from utils.catalog_tree_discovery.research_queue import ResearchQueue
from utils.catalog_tree_discovery.runner import run_catalog_tree_discovery
from utils.catalog_tree_discovery.surface_collectors import (
    SurfaceSignals,
    collect_catalog_surface_signals,
)
from utils.catalog_tree_discovery.tree_normalizer import normalize_label_for_launcher


def test_graph_builder_merges_duplicate_category_urls() -> None:
    signals = SurfaceSignals(
        dom_categories=[
            CategoryEvidence(name="Рыба", url="https://shop.example/category/fish"),
            CategoryEvidence(name="Рыба и морепродукты", url="https://shop.example/category/fish"),
        ]
    )

    graph = build_discovery_graph(signals)

    assert graph.primary_root_ids == ["category-1"]
    assert len(graph.nodes) == 1
    assert graph.nodes[0].canonical_url == "https://shop.example/category/fish"
    assert graph.nodes[0].label_ru == "Рыба"
    assert graph.nodes[0].raw_evidence_refs == ["Рыба и морепродукты"]


def test_normalize_label_for_launcher_prefers_clean_russian() -> None:
    label = normalize_label_for_launcher("  Рыба___и---морепродукты  ", "https://shop.example/category/fish")

    assert label == "Рыба и морепродукты"


def test_collect_catalog_entrypoints_prefers_menu_and_catalog_surfaces() -> None:
    html = """
    <nav>
      <a href="/catalog/fish">Рыба</a>
      <a href="/catalog/seafood">Морепродукты</a>
    </nav>
    """

    result = collect_catalog_entrypoints_from_html("https://shop.example", html)

    assert [item.name for item in result] == ["Рыба", "Морепродукты"]


def test_listing_validator_classifies_pdf_blocked_challenge_and_listing() -> None:
    pdf_result = classify_catalog_surface(SurfaceSignals(pdf_hint=True))
    blocked_result = classify_catalog_surface(SurfaceSignals(blocked_hint=True))
    challenge_result = classify_catalog_surface(SurfaceSignals(blocked_hint=True, challenge_hint=True))
    listing_result = classify_catalog_surface(
        SurfaceSignals(dom_products=[{"name": "Лосось", "url": "https://shop.example/products/salmon"}])
    )

    assert pdf_result.surface_type == "pdf_flipbook"
    assert blocked_result.surface_type == "blocked"
    assert challenge_result.surface_type == "challenge"
    assert challenge_result.protection_signals == ["challenge"]
    assert listing_result.surface_type == "product_listing"
    assert listing_result.validation_state == "listing_valid"


def test_make_phase_event_builds_streaming_payload() -> None:
    event = make_phase_event(
        "collect_surface",
        "running",
        "Поиск структуры каталога",
        ["Рыба", "Морепродукты"],
    )

    assert event.phase == "collect_surface"
    assert event.status == "running"
    assert event.message_ru == "Поиск структуры каталога"
    assert event.discovered_categories == ["Рыба", "Морепродукты"]


def test_research_queue_deduplicates_urls_and_respects_repeat_limit() -> None:
    queue = ResearchQueue(max_repeat_urls=2)

    assert queue.push("https://shop.example/catalog/fish") is True
    assert queue.push("https://shop.example/catalog/fish") is True
    assert queue.push("https://shop.example/catalog/fish") is False
    assert queue.pop() == "https://shop.example/catalog/fish"
    assert queue.pop() == "https://shop.example/catalog/fish"
    assert queue.pop() is None


def test_surface_collectors_detect_russian_region_gate_markers() -> None:
    signals = collect_catalog_surface_signals(
        site_url="https://shop.example/",
        final_url="https://shop.example/",
        status_code=200,
        html="<html><body><div>Выберите ваш регион и город</div></body></html>",
    )

    assert signals.region_hint is True


def test_summarize_catalog_discovery_preserves_public_result_contract() -> None:
    html = """
    <html>
      <body>
        <a href="/category/fish">Рыба</a>
        <a href="/products/salmon-123">Лосось</a>
        <script>fetch('/api/catalog')</script>
      </body>
    </html>
    """

    summary = summarize_catalog_discovery(
        site_url="https://shop.example/",
        final_url="https://shop.example/",
        status_code=200,
        html=html,
    )

    assert summary.surface_type == "category_tree"
    assert summary.validation_state == "menu_only"
    assert summary.primary_root_ids == ["category-1"]
    assert len(summary.nodes) == 1
    assert len(summary.category_links) == 1
    assert len(summary.product_links) == 1


@pytest.mark.asyncio
async def test_run_catalog_tree_discovery_returns_profile_and_phase_events(monkeypatch) -> None:
    async def fake_discover(*args, **kwargs):
        del args, kwargs
        return (
            CatalogDiscoveryResult(
                reachable=True,
                status_code=200,
                final_url="https://5ka.ru/catalog",
                surface_type="category_tree",
                category_links=[
                    CategoryEvidence(name="Рыба", url="https://5ka.ru/catalog/fish"),
                    CategoryEvidence(name="Морепродукты", url="https://5ka.ru/catalog/seafood"),
                ],
                primary_root_ids=["category-1"],
                notes=["baseline"],
            ),
            SimpleNamespace(
                shop="pyaterochka",
                final_url="https://5ka.ru/catalog",
                status_code=200,
                manual_wait_used=False,
                phase_events=[
                    make_phase_event("open_site", "completed", "Открытие сайта"),
                    make_phase_event("expand_menu", "running", "Раскрытие меню"),
                ],
            ),
        )

    monkeypatch.setattr(
        "utils.catalog_tree_discovery.runner.discover_catalog_research_context_via_browser",
        fake_discover,
    )

    result = await run_catalog_tree_discovery("https://5ka.ru/", shop="pyaterochka", mode="live")

    assert result.profile.shop_slug == "pyaterochka"
    assert result.profile.site_url == "https://5ka.ru/catalog"
    assert result.streamed_categories == ["Рыба", "Морепродукты"]
    assert result.current_phase == "build_tree"
    assert result.phase_events[0].phase == "open_site"
    assert result.phase_events[1].phase == "expand_menu"
    assert result.phase_events[-1].discovered_categories == ["Рыба", "Морепродукты"]
    assert result.partial is False


@pytest.mark.asyncio
async def test_run_catalog_tree_discovery_marks_partial_challenge_result(monkeypatch) -> None:
    async def fake_discover(*args, **kwargs):
        del args, kwargs
        return (
            CatalogDiscoveryResult(
                reachable=False,
                status_code=403,
                final_url="https://shop.example/catalog",
                surface_type="challenge",
                challenge_hint=True,
            ),
            SimpleNamespace(
                shop="shop",
                final_url="https://shop.example/catalog",
                status_code=403,
                manual_wait_used=True,
            ),
        )

    monkeypatch.setattr(
        "utils.catalog_tree_discovery.runner.discover_catalog_research_context_via_browser",
        fake_discover,
    )

    result = await run_catalog_tree_discovery("https://shop.example/catalog", mode="quiet", manual_wait=True)

    assert result.partial is True
    assert "partial_research_due_to_challenge" in result.profile.notes
    assert "manual_wait_used" in result.profile.notes
    assert len(result.phase_events) == 1
    assert result.phase_events[0].phase == "build_tree"
    assert result.streamed_categories == []
