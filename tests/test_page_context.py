from utils.page_context import extract_pyaterochka_page_context


def test_extract_pyaterochka_page_context_detects_store_region_and_empty_products() -> None:
    html = """
    <script id="__NEXT_DATA__">
    {"catalogStore":{"selectedStore":{"id":"1"},"address":"Moscow","productsList":[],"products":[],"productsResponse":null}}
    </script>
    """

    context = extract_pyaterochka_page_context(html)

    assert context["next_data_present"] is True
    assert context["catalog_store_present"] is True
    assert context["selected_store_detected"] is True
    assert context["address_detected"] is True
    assert context["region_hint_detected"] is True
    assert context["products_list_empty"] is True
    assert context["products_empty"] is True
    assert context["products_response_null"] is True


def test_extract_pyaterochka_page_context_treats_store_id_as_selected_store() -> None:
    html = '{"catalogStore":{"storeId":"35XY","productsList":[]}}'

    context = extract_pyaterochka_page_context(html)

    assert context["selected_store_detected"] is True
