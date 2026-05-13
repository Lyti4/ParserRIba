from utils.camoufox_launcher import (
    allow_images_in_profile,
    build_camoufox_options,
    disable_session_restore_in_profile,
)


def test_build_camoufox_options_uses_ru_profile_defaults() -> None:
    options = build_camoufox_options(headless=True)

    assert options["locale"] == "ru-RU"
    assert options["humanize"] == 1.5
    assert options["i_know_what_im_doing"] is True
    assert options["os"] == "windows"
    assert options["block_webrtc"] is True


def test_build_camoufox_options_allows_locale_override() -> None:
    options = build_camoufox_options(
        headless=True,
        locale="en-US",
    )

    assert options["locale"] == "en-US"


def test_build_camoufox_options_allows_fingerprint_os_override() -> None:
    options = build_camoufox_options(
        headless=True,
        fingerprint_os=["windows", "linux"],
    )

    assert options["os"] == ["windows", "linux"]


def test_build_camoufox_options_allows_persistent_profile(tmp_path) -> None:
    profile_dir = tmp_path / "profile"
    options = build_camoufox_options(
        headless=True,
        user_data_dir=profile_dir,
    )

    assert options["persistent_context"] is True
    assert options["user_data_dir"] == str(profile_dir)
    assert profile_dir.exists()


def test_allow_images_in_profile_updates_persisted_pref(tmp_path) -> None:
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    prefs_path = profile_dir / "prefs.js"
    prefs_path.write_text('user_pref("permissions.default.image", 2);\n', encoding="utf-8")

    allow_images_in_profile(profile_dir)

    assert 'user_pref("permissions.default.image", 1);' in prefs_path.read_text(encoding="utf-8")


def test_disable_session_restore_in_profile_writes_startup_prefs(tmp_path) -> None:
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    prefs_path = profile_dir / "prefs.js"
    prefs_path.write_text('user_pref("browser.startup.page", 3);\n', encoding="utf-8")

    disable_session_restore_in_profile(profile_dir)
    prefs = prefs_path.read_text(encoding="utf-8")

    assert 'user_pref("browser.startup.page", 0);' in prefs
    assert 'user_pref("browser.sessionstore.resume_from_crash", false);' in prefs
    assert 'user_pref("browser.sessionstore.max_resumed_crashes", 0);' in prefs
