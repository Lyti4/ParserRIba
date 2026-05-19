from pathlib import Path

from utils.onboarding_artifacts import get_artifact_generator
from utils.protection_strategies import get_protection_strategy


def test_get_artifact_generator_returns_default(tmp_path: Path) -> None:
    generator = get_artifact_generator("default")
    paths = generator(tmp_path, "demo_store")

    assert paths.runtime_report_dir.endswith("demo_store")
    assert Path(paths.kb_draft_path).exists()


def test_get_protection_strategy_returns_pause_for_operator() -> None:
    strategy = get_protection_strategy("pause_for_operator")

    assert strategy.name == "pause_for_operator"
    assert strategy.pause_for_operator is True
