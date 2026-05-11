from utils.antibot import detect_pyaterochka_antibot
from utils.geoip import geoip_extra_installed
from utils.proxy import mask_proxy_url, parse_proxy_url


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


def test_geoip_extra_available_in_test_environment() -> None:
    assert geoip_extra_installed() is True
