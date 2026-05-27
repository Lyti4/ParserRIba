from launcher.desktop_product_details import build_product_detail_text


def test_build_product_detail_text_reads_structured_products_without_json() -> None:
    details = build_product_detail_text(
        "",
        ["fish-1"],
        [
            {
                "id": "fish-1",
                "category": "Fish",
                "name": "Cod",
                "brand": "Nord",
                "raw_data": {"supplier": "Nord supplier"},
                "price": {"current": 199.99},
                "in_stock": True,
                "product_link": "https://example.test/product/fish-1",
            }
        ],
    )

    assert "Cod" in details
    assert "Nord supplier" in details
    assert "https://example.test/product/fish-1" in details
