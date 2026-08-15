import scripts.run_desktop_launcher as run_desktop_launcher


def test_run_desktop_launcher_smoke_mode(monkeypatch) -> None:
    monkeypatch.setattr(run_desktop_launcher, "parse_args", lambda: type("Args", (), {"smoke": True})())
    monkeypatch.setattr(run_desktop_launcher, "smoke_main", lambda: 7)

    result = run_desktop_launcher.main()

    assert result == 7


def test_run_desktop_launcher_full_mode(monkeypatch) -> None:
    captured = {}

    class _FakeShell:
        def __init__(
            self,
            *,
            root_dir,
            browser_registration,
            browser_collection_enabled,
        ):
            self.root_dir = root_dir
            self.browser_registration = browser_registration
            self.browser_collection_enabled = browser_collection_enabled
            captured["profile_id"] = (
                browser_registration.declared_profile.source_profile_id
            )
            captured["collection_enabled"] = browser_collection_enabled

        def run(self) -> int:
            return 3

    monkeypatch.setattr(run_desktop_launcher, "parse_args", lambda: type("Args", (), {"smoke": False})())
    monkeypatch.setattr(run_desktop_launcher, "DesktopLauncherShell", _FakeShell)

    result = run_desktop_launcher.main()

    assert result == 3
    assert captured == {
        "profile_id": "pyaterochka-live-catalog",
        "collection_enabled": False,
    }
