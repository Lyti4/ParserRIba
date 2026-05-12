from utils.antibot import classify_navigation_error, detect_pyaterochka_antibot
from utils.geoip import geoip_extra_installed
from utils.proxy import (
    choose_proxy_for_attempt,
    load_proxy_urls,
    mask_proxy_url,
    parse_proxy_url,
    split_proxy_urls,
)


def test_parse_proxy_url_splits_credentials() -> None:
    parsed = parse_proxy_url("http://user:secret@example.com:1000")

    assert parsed.server == "http://example.com:1000"
    assert parsed.username == "user"
    assert parsed.password == "secret"
    assert parsed.as_playwright() == {
        "server": "http://example.com:1000",
        "username": "user",
        "password": "secret",
    }


def test_mask_proxy_url_hides_credentials() -> None:
    masked = mask_proxy_url("http://user:secret@example.com:1000")

    assert masked == "http://***:***@example.com:1000"
    assert "secret" not in masked


def test_split_proxy_urls_accepts_common_separators() -> None:
    value = "http://a:1\nhttp://b:2; http://c:3, http://d:4"

    assert split_proxy_urls(value) == [
        "http://a:1",
        "http://b:2",
        "http://c:3",
        "http://d:4",
    ]


def test_load_proxy_urls_keeps_primary_first_and_deduplicates() -> None:
    proxies = load_proxy_urls(
        primary="http://primary:1000",
        pool="http://second:1000\nhttp://primary:1000",
    )

    assert proxies == ["http://primary:1000", "http://second:1000"]


def test_choose_proxy_for_attempt_rotates() -> None:
    proxies = ["http://one:1000", "http://two:1000"]

    assert choose_proxy_for_attempt(proxies, 1) == "http://one:1000"
    assert choose_proxy_for_attempt(proxies, 2) == "http://two:1000"
    assert choose_proxy_for_attempt(proxies, 3) == "http://one:1000"


def test_detect_pyaterochka_antibot_redirect() -> None:
    blocked, reason = detect_pyaterochka_antibot(
        "https://5ka.ru/xpvnsulc/?back_location=https%3A%2F%2F5ka.ru%2Fcatalog%2F",
        "Loading https://5ka.ru/xpvnsulc/",
        "<html></html>",
    )

    assert blocked is True
    assert reason == "pyaterochka_antibot_redirect"


def test_detect_pyaterochka_ok_catalog() -> None:
    blocked, reason = detect_pyaterochka_antibot(
        "https://5ka.ru/catalog/ryba--251C13077/",
        "Рыба",
        "<html><body>catalog</body></html>",
    )

    assert blocked is False
    assert reason == "ok"


def test_detect_pyaterochka_rotate_image_captcha() -> None:
    blocked, reason = detect_pyaterochka_antibot(
        "https://5ka.ru/catalog/ryba--251C13077/",
        "Проверка",
        "<html><body>Поверните изображение горизонтально</body></html>",
    )

    assert blocked is True
    assert reason == "pyaterochka_rotate_image_captcha"


def test_classify_navigation_dns_error() -> None:
    reason = classify_navigation_error("Page.goto: NS_ERROR_UNKNOWN_HOST")

    assert reason == "network_dns_error"


def test_geoip_extra_available_in_test_environment() -> None:
    assert geoip_extra_installed() is True
