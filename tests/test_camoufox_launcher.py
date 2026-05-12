from utils.camoufox_launcher import build_camoufox_options


def test_build_camoufox_options_uses_ru_profile_defaults() -> None:
    options = build_camoufox_options(headless=True)

    assert options["locale"] == "ru-RU"
    assert options["humanize"] is True
    assert options["i_know_what_im_doing"] is True


def test_build_camoufox_options_allows_locale_override() -> None:
    options = build_camoufox_options(
        headless=True,
        locale="en-US",
    )

    assert options["locale"] == "en-US"
