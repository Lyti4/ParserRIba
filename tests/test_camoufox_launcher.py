from utils.camoufox_launcher import build_camoufox_options


def test_build_camoufox_options_uses_ru_profile_defaults() -> None:
    options = build_camoufox_options(headless=True)

    assert options["locale"] == "ru-RU"
    assert options["timezone_id"] == "Europe/Moscow"
    assert options["humanize"] is True
    assert options["i_know_what_im_doing"] is True


def test_build_camoufox_options_allows_profile_override() -> None:
    options = build_camoufox_options(
        headless=True,
        locale="en-US",
        timezone_id="UTC",
    )

    assert options["locale"] == "en-US"
    assert options["timezone_id"] == "UTC"
