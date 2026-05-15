"""Page context diagnostics for protected catalog pages."""

from __future__ import annotations

import re
from typing import Any


def extract_pyaterochka_page_context(page_html: str) -> dict[str, Any]:
    """Extract store/region/product state hints from saved Pyaterochka HTML."""
    compact = re.sub(r"\s+", "", page_html)
    return {
        "next_data_present": "__NEXT_DATA__" in page_html,
        "catalog_store_present": "catalogStore" in page_html,
        "selected_store_detected": bool(
            re.search(r'"(?:selectedStore|currentStore|activeStore|store)"\s*:\s*\{', page_html)
            or re.search(r'"storeId"\s*:\s*"[^"]+', page_html)
        ),
        "address_detected": bool(re.search(r'"address"\s*:\s*"[^"]+', page_html)),
        "region_hint_detected": any(marker in page_html.lower() for marker in ("москва", "moscow", "city")),
        "products_list_empty": '"productsList":[]' in compact,
        "products_empty": '"products":[]' in compact,
        "products_response_null": '"productsResponse":null' in compact,
    }
