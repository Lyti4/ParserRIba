from utils.network_capture import (
    payload_has_empty_products,
    payload_preview,
    sanitize_diagnostic_url,
)


def test_sanitize_diagnostic_url_masks_sensitive_query_values() -> None:
    url = "https://5ka.ru/api/catalog?token=abc&city=moscow&session=secret"

    sanitized = sanitize_diagnostic_url(url)

    assert "token=%2A%2A%2A" in sanitized
    assert "session=%2A%2A%2A" in sanitized
    assert "city=moscow" in sanitized
    assert "abc" not in sanitized
    assert "secret" not in sanitized


def test_sanitize_diagnostic_url_masks_challenge_query_values() -> None:
    url = "https://5ka.ru/xpvnsulc/?hcheck=abc&request_id=rid&oirutpspsc=challenge&city=moscow"

    sanitized = sanitize_diagnostic_url(url)

    assert "abc" not in sanitized
    assert "rid" not in sanitized
    assert "challenge" not in sanitized
    assert "city=moscow" in sanitized


def test_payload_has_empty_products_detects_common_shapes() -> None:
    assert payload_has_empty_products('{"products": []}')
    assert payload_has_empty_products('{"productsList": [], "productsResponse": null}')
    assert not payload_has_empty_products('{"products": [{"name": "Fish"}]}')


def test_payload_preview_compacts_whitespace() -> None:
    assert payload_preview("{\n  \"products\": []\n}", max_length=20) == '{ "products": [] }'


def test_payload_preview_redacts_sensitive_json_fields() -> None:
    preview = payload_preview('{"token":"secret","products":[{"name":"Fish"}]}')

    assert "secret" not in preview
    assert '"token": "***"' in preview
