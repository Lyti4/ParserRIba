from launcher.desktop_view_helpers import build_summary_text
from models.launcher_state import LauncherAppState


def test_build_summary_text_shows_partial_research_warning_and_expand_menu_phase() -> None:
    state = LauncherAppState()
    state.research.current_phase = "expand_menu"
    state.profile.diagnostics = {"partial_research": True}

    summary = build_summary_text(state)

    assert "Текущий этап: Раскрытие меню" in summary
    assert "Предупреждение: частично исследовано." in summary
