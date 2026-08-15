from launcher.desktop_interaction_state import apply_widget_enabled_state
from models.launcher_state import LauncherAppState


class _DummyWidget:
    def __init__(self) -> None:
        self.enabled = True

    def setEnabled(self, value: bool) -> None:
        self.enabled = value


class _DummyCombo(_DummyWidget):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def currentData(self) -> str:
        return self.value


class _DummyShell:
    def __init__(self) -> None:
        self.state = LauncherAppState()
        self.site_url_input = _DummyWidget()
        self.shop_combo = _DummyWidget()
        self.source_profile_combo = _DummyCombo("local-json-file")
        self.source_locator_input = _DummyWidget()
        self.source_file_picker_button = _DummyWidget()
        self.source_catalog_tree = _DummyWidget()
        self.intent_combo = _DummyWidget()
        self.category_list = _DummyWidget()
        self.headless_checkbox = _DummyWidget()
        self.manual_wait_checkbox = _DummyWidget()
        self.attempts_spin = _DummyWidget()
        self.listen_seconds_spin = _DummyWidget()
        self.filter_widgets = {"suppliers": _DummyWidget(), "brands": _DummyWidget()}
        self.filter_extra_widgets = [_DummyWidget(), _DummyWidget()]
        self.category_action_buttons = [_DummyWidget(), _DummyWidget()]
        self.source_catalog_action_buttons = [_DummyWidget(), _DummyWidget()]
        self.filter_action_buttons = [_DummyWidget()]


def test_apply_widget_enabled_state_disables_widgets_while_running() -> None:
    shell = _DummyShell()
    shell.state.task.status = "running"

    apply_widget_enabled_state(shell)

    assert shell.site_url_input.enabled is False
    assert shell.source_profile_combo.enabled is False
    assert shell.source_locator_input.enabled is False
    assert shell.source_file_picker_button.enabled is False
    assert shell.source_catalog_tree.enabled is False
    assert shell.intent_combo.enabled is False
    assert shell.filter_widgets["suppliers"].enabled is False
    assert shell.filter_extra_widgets[0].enabled is False
    assert shell.category_action_buttons[0].enabled is False
    assert shell.source_catalog_action_buttons[0].enabled is False
    assert shell.filter_action_buttons[0].enabled is False


def test_apply_widget_enabled_state_enables_widgets_when_idle() -> None:
    shell = _DummyShell()
    shell.state.task.status = "idle"

    apply_widget_enabled_state(shell)

    assert shell.site_url_input.enabled is True
    assert shell.source_profile_combo.enabled is True
    assert shell.source_locator_input.enabled is True
    assert shell.source_file_picker_button.enabled is True
    assert shell.source_catalog_tree.enabled is True
    assert shell.intent_combo.enabled is True
    assert shell.filter_widgets["brands"].enabled is True
    assert shell.filter_extra_widgets[1].enabled is True
    assert shell.category_action_buttons[1].enabled is True
    assert shell.source_catalog_action_buttons[1].enabled is True
    assert shell.filter_action_buttons[0].enabled is True


def test_apply_widget_enabled_state_keeps_file_picker_disabled_for_non_file_profile() -> None:
    shell = _DummyShell()
    shell.source_profile_combo.value = "synthetic-example-catalog"
    shell.state.task.status = "idle"

    apply_widget_enabled_state(shell)

    assert shell.source_profile_combo.enabled is True
    assert shell.source_file_picker_button.enabled is False
    assert shell.source_catalog_tree.enabled is True
