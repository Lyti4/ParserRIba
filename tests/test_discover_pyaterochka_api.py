from scripts.discover_pyaterochka_api import (
    MANUAL_DISCOVERY_PROMPT,
    _collect_dom_product_links,
    _parse_args,
    _wait_for_manual_ready,
)


async def test_wait_for_manual_ready_skips_prompt_when_disabled() -> None:
    calls: list[str] = []

    def prompt(value: str) -> None:
        calls.append(value)

    await _wait_for_manual_ready(manual_wait=False, prompt_func=prompt)

    assert calls == []


async def test_wait_for_manual_ready_uses_prompt_when_enabled() -> None:
    calls: list[str] = []

    def prompt(value: str) -> None:
        calls.append(value)

    await _wait_for_manual_ready(manual_wait=True, prompt_func=prompt)

    assert calls == [MANUAL_DISCOVERY_PROMPT]


def test_parse_args_keeps_manual_wait_enabled_by_default() -> None:
    args = _parse_args([])

    assert args.manual_wait is True


def test_parse_args_accepts_no_manual_wait() -> None:
    args = _parse_args(["--no-manual-wait", "--listen-seconds", "30"])

    assert args.manual_wait is False
    assert args.listen_seconds == 30


async def test_collect_dom_product_links_extracts_unique_product_hrefs() -> None:
    class FakePage:
        async def evaluate(self, script: str, limit: int) -> list[dict[str, str]]:
            assert "document.querySelectorAll" in script
            assert limit == 3
            return [
                {"href": "https://5ka.ru/product/forel-file--4023639/", "title": "Forel"},
                {"href": "https://5ka.ru/product/forel-file--4023639/", "title": "Forel dup"},
                {"href": "https://5ka.ru/product/losos--4015936/", "title": "Losos"},
                {"href": "https://5ka.ru/catalog/ryba--251C13077/", "title": "Catalog"},
            ]

    evidence = await _collect_dom_product_links(FakePage(), limit=3)

    assert evidence == {
        "count": 2,
        "sample_links": [
            {"href": "https://5ka.ru/product/forel-file--4023639/", "title": "Forel"},
            {"href": "https://5ka.ru/product/losos--4015936/", "title": "Losos"},
        ],
        "product_ids": ["4023639", "4015936"],
        "links_by_id": {
            "4023639": "https://5ka.ru/product/forel-file--4023639/",
            "4015936": "https://5ka.ru/product/losos--4015936/",
        },
    }
