from utils.antibot import PageDiagnostics
from utils.pyaterochka_catalog_capture import (
    PYATEROCHKA_MANUAL_GATE_PROFILE,
    _RawProductCollector,
    _capture_browse_rounds,
    _manual_challenge_wait_seconds,
    _product_settle_seconds,
    _wait_for_manual_challenge,
)


class _FakeJsonResponse:
    def __init__(self, *, url: str, payload: dict, content_type: str = "application/json") -> None:
        self.url = url
        self._payload = payload
        self._content_type = content_type

    async def all_headers(self) -> dict[str, str]:
        return {"Content-Type": self._content_type}

    async def json(self) -> dict:
        return self._payload


class _FakeManualPage:
    def __init__(self) -> None:
        self.calls = 0

    async def title(self) -> str:
        return "captcha" if self.calls < 2 else "catalog"

    async def content(self) -> str:
        return "<html>captcha</html>" if self.calls < 2 else "<html>catalog</html>"

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        del timeout_ms
        self.calls += 1

    @property
    def url(self) -> str:
        if self.calls < 2:
            return "https://5ka.ru/xpvnsulc/?back_location=/catalog/syr--251C51985/"
        return "https://5ka.ru/catalog/syr--251C51985/"


async def test_wait_for_manual_challenge_polls_without_tty(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    page = _FakeManualPage()

    diagnostics = await _wait_for_manual_challenge(
        page,
        initial_diagnostics=PageDiagnostics(
            blocked=True,
            reason="pyaterochka_captcha",
            final_url=page.url,
            title="captcha",
            html_size=20,
        ),
        max_seconds=5,
    )

    assert diagnostics.blocked is False
    assert page.calls == 2


async def test_raw_product_collector_accepts_structured_json_without_products_url() -> None:
    collector = _RawProductCollector()
    response = _FakeJsonResponse(
        url="https://5ka.ru/api/catalog/listing",
        payload={
            "data": {
                "items": [
                    {
                        "plu": 4023639,
                        "name": "Cod",
                        "prices": {"regular": "999.99"},
                        "url": "/product/cod--4023639/",
                    }
                ]
            }
        },
    )

    await collector.record_response(response)

    assert collector.items_by_id["4023639"]["name"] == "Cod"
    assert collector.product_urls == {"https://5ka.ru/api/catalog/listing"}


class _FakeCatalogWithStaleCaptchaPage:
    async def title(self) -> str:
        return "Пятёрочка"

    async def content(self) -> str:
        return "<html><script>rotate image captcha text kept in bundle</script></html>"

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        del timeout_ms

    @property
    def url(self) -> str:
        return "https://5ka.ru/catalog/tushyonka-konservy--251C52435/"


async def test_wait_for_manual_challenge_accepts_catalog_url_with_stale_captcha_text(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    page = _FakeCatalogWithStaleCaptchaPage()

    diagnostics = await _wait_for_manual_challenge(
        page,
        initial_diagnostics=PageDiagnostics(
            blocked=True,
            reason="pyaterochka_rotate_image_captcha",
            final_url=page.url,
            title="Пятёрочка",
            html_size=70,
        ),
        max_seconds=5,
    )

    assert diagnostics.blocked is False
    assert diagnostics.reason == "manual_catalog_ready_after_challenge"


class _FakeHomeAfterCaptchaPage:
    async def title(self) -> str:
        return "Пятерочка"

    async def content(self) -> str:
        return "<html><body>home</body></html>"

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        del timeout_ms

    @property
    def url(self) -> str:
        return "https://5ka.ru/"


async def test_wait_for_manual_challenge_accepts_home_after_captcha(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    page = _FakeHomeAfterCaptchaPage()

    diagnostics = await _wait_for_manual_challenge(
        page,
        initial_diagnostics=PageDiagnostics(
            blocked=True,
            reason="pyaterochka_rotate_image_captcha",
            final_url="https://5ka.ru/xpvnsulc/?back_location=/catalog/syr--251C51985/",
            title="captcha",
            html_size=40,
        ),
        max_seconds=5,
    )

    assert diagnostics.blocked is False
    assert diagnostics.reason == "ok"


async def test_wait_for_manual_challenge_delegates_to_shared_gate(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    page = _FakeHomeAfterCaptchaPage()
    captured: dict[str, object] = {}

    async def fake_wait_for_manual_store_page(
        passed_page,
        *,
        listen_seconds: int,
        profile,
        collect_diagnostics,
        max_wait_seconds: int | None,
    ) -> None:
        captured["page"] = passed_page
        captured["listen_seconds"] = listen_seconds
        captured["profile"] = profile
        captured["collect_diagnostics"] = collect_diagnostics
        captured["max_wait_seconds"] = max_wait_seconds

    monkeypatch.setattr(
        "utils.pyaterochka_catalog_capture.wait_for_manual_store_page",
        fake_wait_for_manual_store_page,
    )

    diagnostics = await _wait_for_manual_challenge(
        page,
        initial_diagnostics=PageDiagnostics(
            blocked=True,
            reason="pyaterochka_rotate_image_captcha",
            final_url="https://5ka.ru/xpvnsulc/?back_location=/catalog/syr--251C51985/",
            title="captcha",
            html_size=40,
        ),
        max_seconds=430,
    )

    assert diagnostics.blocked is False
    assert captured == {
        "page": page,
        "listen_seconds": 43,
        "profile": PYATEROCHKA_MANUAL_GATE_PROFILE,
        "collect_diagnostics": captured["collect_diagnostics"],
        "max_wait_seconds": 430,
    }


def test_product_settle_seconds_caps_stale_launcher_wait() -> None:
    assert _product_settle_seconds(43) == 8


def test_manual_challenge_wait_keeps_browser_open_for_multiple_captcha_rounds() -> None:
    assert _manual_challenge_wait_seconds(43) == 430
    assert _manual_challenge_wait_seconds(10) == 300
    assert _manual_challenge_wait_seconds(120) == 900


def test_manual_capture_uses_single_browse_round_after_operator_wait() -> None:
    assert _capture_browse_rounds(manual_wait=True, browse_rounds=4) == 1
    assert _capture_browse_rounds(manual_wait=False, browse_rounds=4) == 4
