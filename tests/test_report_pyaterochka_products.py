from scripts.report_pyaterochka_products import build_products_report


def test_build_products_report_shows_snapshot_changes() -> None:
    report = build_products_report(
        {
            "products_count": 10,
            "latest_snapshot_at": "2026-05-19T01:00:00.000001+00:00",
            "previous_snapshot_at": "2026-05-19T00:30:00.000001+00:00",
            "changed_prices": [
                {
                    "product_id": "4023639",
                    "name": "Треска",
                    "previous_price": 999.99,
                    "current_price": 899.99,
                }
            ],
            "changed_availability": [
                {
                    "product_id": "4023639",
                    "name": "Треска",
                    "previous_in_stock": True,
                    "current_in_stock": False,
                }
            ],
        }
    )

    assert "Pyaterochka Products Report" in report
    assert "Products stored: 10" in report
    assert "Changed prices: 1" in report
    assert "4023639 | Треска | 999.99 -> 899.99" in report
    assert "Changed availability: 1" in report
    assert "4023639 | Треска | True -> False" in report
