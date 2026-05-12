from utils.human_behavior import (
    HumanBehaviorProfile,
    browse_category_page,
    build_category_behavior_profile,
    hover_product_cards,
)


class FakeMouse:
    def __init__(self) -> None:
        self.moves: list[tuple[float, float, int]] = []
        self.wheels: list[int] = []

    async def move(self, x: float, y: float, steps: int = 1) -> None:
        self.moves.append((x, y, steps))

    async def wheel(self, x: int, y: int) -> None:
        self.wheels.append(y)


class FakePage:
    def __init__(self) -> None:
        self.mouse = FakeMouse()
        self.pauses: list[int] = []

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        self.pauses.append(timeout_ms)


class FakeCard:
    async def bounding_box(self) -> dict[str, float]:
        return {"x": 10, "y": 20, "width": 100, "height": 80}


def test_build_category_behavior_profile_for_fish() -> None:
    profile = build_category_behavior_profile("Рыба")

    assert profile.name == "fish-category"
    assert profile.scroll_steps_min <= profile.scroll_steps_max
    assert profile.hover_cards >= 1


async def test_browse_category_page_uses_profile_scrolls() -> None:
    page = FakePage()
    profile = HumanBehaviorProfile(
        min_pause_ms=1,
        max_pause_ms=1,
        scroll_steps_min=2,
        scroll_steps_max=2,
        scroll_delta_min=10,
        scroll_delta_max=10,
    )

    await browse_category_page(page, profile)

    assert len(page.mouse.wheels) == 2
    assert page.pauses


async def test_hover_product_cards_moves_over_limited_cards() -> None:
    page = FakePage()
    profile = HumanBehaviorProfile(
        min_pause_ms=1,
        max_pause_ms=1,
        hover_cards=2,
        mouse_move_steps_min=1,
        mouse_move_steps_max=1,
    )

    await hover_product_cards(page, [FakeCard(), FakeCard(), FakeCard()], profile)

    assert len(page.mouse.moves) == 2
