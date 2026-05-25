import base64
import json

from utils.catalog_tree_discovery.payload_classifiers import classify_payload


def test_classifier_extracts_nextjs_hydration_tree() -> None:
    payload = {
        "props": {
            "pageProps": {
                "menu": [
                    {
                        "name": "Рыба",
                        "url": "/catalog/ryba/",
                        "children": [{"name": "Красная рыба", "url": "/catalog/ryba/krasnaya/"}],
                    }
                ]
            }
        }
    }

    result = classify_payload(
        base_url="https://shop.example/",
        content_type="application/json",
        body_text=json.dumps(payload, ensure_ascii=False),
    )

    assert result.payload_type == "catalog_tree_payload"
    assert [item.url for item in result.categories] == [
        "https://shop.example/catalog/ryba/",
        "https://shop.example/catalog/ryba/krasnaya/",
    ]
    assert result.confidence > 0.6


def test_classifier_extracts_apollo_redux_like_nested_categories() -> None:
    payload = {
        "__APOLLO_STATE__": {
            "Category:1": {"title": "Морепродукты", "path": "/category/seafood/"},
            "Category:2": {"label": "Креветки", "href": "/category/seafood/shrimp/"},
        }
    }

    result = classify_payload(
        base_url="https://shop.example/",
        content_type="application/json",
        body_text=json.dumps(payload, ensure_ascii=False),
    )

    assert result.payload_type == "catalog_tree_payload"
    assert {item.name for item in result.categories} == {"Морепродукты", "Креветки"}


def test_classifier_decodes_escaped_json_catalog_urls() -> None:
    escaped = json.dumps(
        json.dumps({"items": [{"name": "Вино", "url": "/catalog/vino/"}]}, ensure_ascii=False),
        ensure_ascii=False,
    )

    result = classify_payload(base_url="https://shop.example/", content_type="application/json", body_text=escaped)

    assert result.payload_type == "catalog_tree_payload"
    assert result.categories[0].url == "https://shop.example/catalog/vino/"


def test_classifier_decodes_base64url_jwt_like_payload_structure() -> None:
    body = json.dumps({"category": {"name": "Икра", "url": "/catalog/ikra/"}}).encode("utf-8")
    segment = base64.urlsafe_b64encode(body).decode("ascii").rstrip("=")
    token = f"header.{segment}.signature"

    result = classify_payload(base_url="https://shop.example/", content_type="text/plain", body_text=token)

    assert result.payload_type == "catalog_tree_payload"
    assert result.categories[0].name == "Икра"


def test_classifier_extracts_graphql_edges_nodes_children() -> None:
    payload = {
        "data": {
            "catalog": {
                "edges": [
                    {
                        "node": {
                            "name": "Заморозка",
                            "url": "/catalog/frozen/",
                            "children": [{"name": "Рыба", "url": "/catalog/frozen/fish/"}],
                        }
                    }
                ]
            }
        }
    }

    result = classify_payload(
        base_url="https://shop.example/graphql",
        content_type="application/json",
        body_text=json.dumps(payload, ensure_ascii=False),
    )

    assert result.payload_type == "catalog_tree_payload"
    assert any(hint.kind == "graphql_tree" for hint in result.route_hints)
    assert len(result.categories) == 2


def test_classifier_detects_protection_payload() -> None:
    result = classify_payload(
        base_url="https://shop.example/session",
        content_type="text/html",
        body_text="<html>datadome captcha perimeterx servicepipe</html>",
    )

    assert result.payload_type == "protection_payload"
    assert "protection:captcha" in result.protection_signals
    assert "protection:datadome" in result.protection_signals
