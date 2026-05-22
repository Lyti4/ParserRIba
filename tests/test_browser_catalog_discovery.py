from types import SimpleNamespace

import pytest

from models.catalog_discovery import CatalogDiscoveryResult
from scripts.discover_pyaterochka_api import PROFILE_DIR
from utils.browser_catalog_discovery import (
    discover_catalog_research_context_via_browser,
    discover_catalog_site_via_browser,
)


@pytest.mark.asyncio
async def test_pyaterochka_browser_discovery_reuses_protected_camoufox_context(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class _DummyPage:
        def __init__(self) -> None:
            self.url = "https://5ka.ru/catalog"
            self.headers = {}
            self.waits: list[int] = []

        async def set_extra_http_headers(self, headers):
            self.headers = dict(headers)

        async def goto(self, site_url: str, **kwargs):
            calls["goto"] = {"site_url": site_url, **kwargs}
            return SimpleNamespace(status=200)

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.waits.append(timeout_ms)

        async def content(self) -> str:
            return """
            <html>
              <body>
                <a href="/catalog/ryba--251C13077/">Рыба</a>
                <a href="/catalog/moreprodukty--251C13078/">Морепродукты</a>
              </body>
            </html>
            """

        @property
        def mouse(self):
            return SimpleNamespace()

    class _DummyBrowser:
        async def new_page(self):
            page = _DummyPage()
            calls["page"] = page
            return page

    class _DummyCamoufox:
        def __init__(self, **kwargs):
            calls["launch_options"] = kwargs

        async def __aenter__(self):
            return _DummyBrowser()

        async def __aexit__(self, exc_type, exc, tb):
            return None

    def fake_build_camoufox_options(**kwargs):
        calls["build_options"] = kwargs
        return {"headless": kwargs["headless"], "persistent_context": True}

    async def fake_wait_for_pyaterochka_state(page, response, seconds=30):
        calls["wait_state"] = {
            "page_url": page.url,
            "status": response.status,
            "seconds": seconds,
        }
        return SimpleNamespace(blocked=False, status=200, reason="ok")

    async def fake_browse_category_page(page, profile):
        calls["browse_profile"] = profile.name
        return None

    monkeypatch.setattr("utils.browser_catalog_discovery.configure_windows_console", lambda: None)
    monkeypatch.setattr("utils.browser_catalog_discovery.load_dotenv_file", lambda path: calls.setdefault("dotenv", str(path)))
    monkeypatch.setattr("utils.browser_catalog_discovery.load_proxy_urls", lambda primary, pool: ["http://u:p@example:1000"])
    monkeypatch.setattr("utils.browser_catalog_discovery.choose_proxy_for_attempt", lambda proxy_urls, attempt: proxy_urls[0])
    monkeypatch.setattr("utils.browser_catalog_discovery.build_camoufox_options", fake_build_camoufox_options)
    monkeypatch.setattr("utils.browser_catalog_discovery.AsyncCamoufox", _DummyCamoufox)
    monkeypatch.setattr("utils.browser_catalog_discovery.wait_for_pyaterochka_state", fake_wait_for_pyaterochka_state)
    monkeypatch.setattr("utils.browser_catalog_discovery.browse_category_page", fake_browse_category_page)
    monkeypatch.setattr("utils.browser_catalog_discovery.KBLoader", lambda path: SimpleNamespace(load_shop=lambda shop: SimpleNamespace(headers=SimpleNamespace(custom={"x-test": "1"}))))

    result = await discover_catalog_site_via_browser(
        "https://5ka.ru/",
        shop="pyaterochka",
        headless=True,
        manual_wait=False,
        listen_seconds=3,
    )

    assert isinstance(result, CatalogDiscoveryResult)
    assert result.surface_type == "category_tree"
    assert [item.name for item in result.category_links] == ["Рыба", "Морепродукты"]
    assert calls["build_options"] == {
        "headless": True,
        "proxy_url": "http://u:p@example:1000",
        "geoip": False,
        "block_images": False,
        "block_webgl": False,
        "humanize": True,
        "fingerprint_os": "windows",
        "user_data_dir": PROFILE_DIR,
    }
    assert calls["wait_state"] == {
        "page_url": "https://5ka.ru/catalog",
        "status": 200,
        "seconds": 10,
    }
    assert calls["browse_profile"] == "fish-category"
    assert calls["goto"] == {
        "site_url": "https://5ka.ru/",
        "wait_until": "domcontentloaded",
        "timeout": 60000,
    }
    assert calls["page"].headers == {"x-test": "1"}
    assert calls["page"].waits == [5000, 3000]


@pytest.mark.asyncio
async def test_browser_research_context_wraps_existing_discovery_result(monkeypatch) -> None:
    async def fake_discover(*args, **kwargs):
        del args, kwargs
        return CatalogDiscoveryResult(
            reachable=True,
            status_code=200,
            final_url="https://shop.example/catalog",
            surface_type="category_tree",
        )

    monkeypatch.setattr("utils.browser_catalog_discovery.discover_catalog_site_via_browser", fake_discover)

    result, context = await discover_catalog_research_context_via_browser(
        "https://shop.example/catalog",
        shop="metro",
        manual_wait=True,
        listen_seconds=4,
    )

    assert result.final_url == "https://shop.example/catalog"
    assert context.shop == "metro"
    assert context.final_url == "https://shop.example/catalog"
    assert context.status_code == 200
    assert context.manual_wait_used is True
