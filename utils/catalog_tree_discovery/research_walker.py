"""Active single-page browser walker for catalog research."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from models.catalog_discovery import ApiEvidence, CatalogDiscoveryResult, CategoryEvidence
from utils.catalog_discovery import build_catalog_discovery_result
from utils.catalog_tree_discovery.entrypoint_collectors import collect_catalog_entrypoints_from_html
from utils.catalog_tree_discovery.event_capture import DiscoveryEventCapture
from utils.catalog_tree_discovery.menu_expander import expand_menu_surfaces
from utils.catalog_tree_discovery.phase_events import make_phase_event
from utils.catalog_tree_discovery.research_queue import ResearchQueue
from utils.catalog_tree_discovery.surface_collectors import SurfaceSignals, collect_catalog_surface_signals

MAX_VISITED_PAGES = 4


@dataclass
class ResearchWalkerResult:
    """Serializable output of an active browser research walk."""

    discovery: CatalogDiscoveryResult
    phase_events: list[Any]
    streamed_categories: list[str]
    final_url: str
    status_code: int


class CamoufoxResearchWalker:
    """Drive one browser page through a small serial catalog exploration loop."""

    def __init__(self, *, listen_seconds: int, max_repeat_urls: int, max_depth: int) -> None:
        self.listen_seconds = max(1, int(listen_seconds))
        self.max_depth = max(1, int(max_depth))
        self.queue = ResearchQueue(max_repeat_urls=max_repeat_urls)

    async def run(
        self,
        *,
        site_url: str,
        page: Any,
        initial_response: Any | None,
    ) -> ResearchWalkerResult:
        """Expand menu surfaces and walk a few discovered catalog branches."""
        phase_events = [make_phase_event("open_site", "completed", "Открытие сайта")]
        capture = DiscoveryEventCapture()
        tasks = self._attach_network_capture(page, capture)
        aggregate = SurfaceSignals()
        visited_urls: list[str] = []
        final_url = page.url or site_url
        status_code = int(getattr(initial_response, "status", 0) or 0)

        phase_events.append(make_phase_event("expand_menu", "running", "Раскрытие меню"))
        await expand_menu_surfaces(page)
        await page.wait_for_timeout(self.listen_seconds * 1000)
        current_signals, final_url, status_code = await self._collect_page_signals(
            page=page,
            site_url=site_url,
            fallback_status=status_code,
        )
        self._merge_signals(aggregate, current_signals, capture)
        visited_urls.append(final_url)
        discovered_names = [item.name or item.url for item in aggregate.dom_categories]
        phase_events.append(make_phase_event("collect_surface", "running", "Сбор структуры", discovered_names[:8]))

        for item in collect_catalog_entrypoints_from_html(final_url or site_url, await page.content()):
            self._maybe_enqueue(site_url, item)

        steps = 0
        while steps < min(self.max_depth, MAX_VISITED_PAGES - 1):
            next_url = self.queue.pop()
            if not next_url or next_url in visited_urls:
                break
            response = await page.goto(next_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(self.listen_seconds * 1000)
            current_signals, final_url, status_code = await self._collect_page_signals(
                page=page,
                site_url=next_url,
                fallback_status=int(getattr(response, "status", 0) or 0),
            )
            self._merge_signals(aggregate, current_signals, capture)
            visited_urls.append(final_url)
            for item in current_signals.dom_categories:
                self._maybe_enqueue(site_url, item)
            steps += 1

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        discovery = build_catalog_discovery_result(
            site_url=site_url,
            final_url=final_url or site_url,
            status_code=status_code,
            signals=aggregate,
            discovery_source="mixed" if capture.route_hints else "dom",
        )
        if capture.route_hints:
            discovery.api_hints.extend(
                ApiEvidence(kind=hint.kind, value=hint.value, source="network")
                for hint in capture.route_hints
            )
        return ResearchWalkerResult(
            discovery=discovery,
            phase_events=phase_events,
            streamed_categories=[item.name or item.url for item in discovery.category_links][:8],
            final_url=final_url or site_url,
            status_code=status_code,
        )

    def _attach_network_capture(self, page: Any, capture: DiscoveryEventCapture) -> list[asyncio.Task[None]]:
        tasks: list[asyncio.Task[None]] = []

        def track_request(request: Any) -> None:
            tasks.append(asyncio.create_task(capture.record_request(str(request.url))))

        def track_response(response: Any) -> None:
            async def _record() -> None:
                try:
                    body_text = await response.text()
                except Exception:
                    body_text = ""
                await capture.record_response(
                    url=str(response.url),
                    status=int(getattr(response, "status", 0) or 0),
                    content_type=str(getattr(response, "headers", {}).get("content-type", "")),
                    body_text=body_text,
                )

            tasks.append(asyncio.create_task(_record()))

        page.on("request", track_request)
        page.on("response", track_response)
        return tasks

    async def _collect_page_signals(
        self,
        *,
        page: Any,
        site_url: str,
        fallback_status: int,
    ) -> tuple[SurfaceSignals, str, int]:
        html = await page.content()
        final_url = page.url or site_url
        status_code = int(fallback_status or 0)
        return (
            collect_catalog_surface_signals(
                site_url=site_url,
                final_url=final_url,
                status_code=status_code,
                html=html,
            ),
            final_url,
            status_code,
        )

    def _maybe_enqueue(self, root_url: str, item: CategoryEvidence) -> None:
        if not self._same_host(root_url, item.url):
            return
        self.queue.push(item.url)

    def _merge_signals(
        self,
        target: SurfaceSignals,
        source: SurfaceSignals,
        capture: DiscoveryEventCapture,
    ) -> None:
        target.dom_categories = self._dedup_links(target.dom_categories + source.dom_categories)
        target.dom_products = self._dedup_links(target.dom_products + source.dom_products)
        target.documents = self._dedup_links(target.documents + source.documents)
        target.api_hints = self._dedup_links(target.api_hints + source.api_hints)
        target.raw_hrefs = list(dict.fromkeys(target.raw_hrefs + source.raw_hrefs))
        target.blocked_hint = target.blocked_hint or source.blocked_hint
        target.challenge_hint = target.challenge_hint or source.challenge_hint
        target.region_hint = target.region_hint or source.region_hint
        target.pdf_hint = target.pdf_hint or source.pdf_hint
        target.csrf_meta_detected = target.csrf_meta_detected or source.csrf_meta_detected
        target.products_path_seen = target.products_path_seen or source.products_path_seen
        target.pagination_hint = target.pagination_hint or source.pagination_hint
        for hint in capture.route_hints:
            api_hint = ApiEvidence(kind=hint.kind, value=hint.value, source="network")
            if not any(existing.kind == api_hint.kind and existing.value == api_hint.value for existing in target.api_hints):
                target.api_hints.append(api_hint)

    def _dedup_links(self, items: list[Any]) -> list[Any]:
        seen: set[tuple[str, str]] = set()
        result: list[Any] = []
        for item in items:
            key = (
                str(getattr(item, "kind", "")),
                str(getattr(item, "url", "") or getattr(item, "value", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    def _same_host(self, left: str, right: str) -> bool:
        return urlparse(left).netloc.casefold() == urlparse(right).netloc.casefold()
