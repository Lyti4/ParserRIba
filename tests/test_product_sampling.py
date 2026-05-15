from utils.product_sampling import extract_sample_products, find_cards, query_first_attribute, query_first_text


class FakeElement:
    def __init__(self, text: str = "", attrs: dict[str, str] | None = None) -> None:
        self.text = text
        self.attrs = attrs or {}

    async def inner_text(self) -> str:
        return self.text

    async def get_attribute(self, attr: str) -> str:
        return self.attrs.get(attr, "")


class FakeCard:
    def __init__(self, elements: dict[str, FakeElement]) -> None:
        self.elements = elements

    async def query_selector(self, selector: str) -> FakeElement | None:
        return self.elements.get(selector)


class FakePage:
    def __init__(self, cards: list[FakeCard]) -> None:
        self.cards = cards

    async def query_selector_all(self, selector: str) -> list[FakeCard]:
        return self.cards if selector == ".card" else []


async def test_query_first_text_returns_first_non_empty_match() -> None:
    root = FakeCard({".name": FakeElement(" Fish ")})

    assert await query_first_text(root, [".missing", ".name"]) == "Fish"


async def test_query_first_attribute_returns_first_match() -> None:
    root = FakeCard({"a": FakeElement(attrs={"href": "/product"})})

    assert await query_first_attribute(root, ["a"], "href") == "/product"


async def test_find_cards_returns_first_non_empty_selector() -> None:
    cards = [FakeCard({})]

    assert await find_cards(FakePage(cards), [".missing", ".card"]) == cards


async def test_extract_sample_products_normalizes_relative_links() -> None:
    card = FakeCard(
        {
            ".name": FakeElement("Fish"),
            ".price": FakeElement("100"),
            "a": FakeElement(attrs={"href": "/product"}),
        }
    )

    products = await extract_sample_products([card], [".name"], [".price"], ["a"])

    assert products == [
        {
            "index": "1",
            "name": "Fish",
            "price": "100",
            "link": "https://5ka.ru/product",
        }
    ]
