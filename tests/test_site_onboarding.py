import json
from pathlib import Path

from utils.site_onboarding import resume_site_onboarding, run_site_onboarding


def test_run_site_onboarding_for_known_site_creates_runtime_ready_session(tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    result = run_site_onboarding(
        site_url="https://5ka.ru",
        root_dir=tmp_path,
    )

    assert result.shop_slug == "pyaterochka"
    assert result.status == "runtime_ready"
    assert len(result.category_tree) >= 2
    assert Path(result.artifact_paths.session_state_path).exists()
    assert Path(result.artifact_paths.kb_draft_path).exists()


def test_run_site_onboarding_for_unknown_site_creates_scaffolds(tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    result = run_site_onboarding(
        site_url="https://verny.example",
        root_dir=tmp_path,
    )

    assert result.shop_slug == "verny_example"
    assert result.status == "scaffold_ready"
    assert result.category_tree == []
    assert Path(result.artifact_paths.backend_stub_path).exists()
    assert Path(result.artifact_paths.capture_stub_path).exists()


def test_run_site_onboarding_can_pause_and_resume(tmp_path: Path) -> None:
    _prepare_root(tmp_path)

    paused = run_site_onboarding(
        site_url="https://5ka.ru",
        root_dir=tmp_path,
        require_operator_confirmation=True,
    )
    resumed = resume_site_onboarding(session_id=paused.session_id, root_dir=tmp_path)

    assert paused.status == "needs_operator"
    assert resumed.session_id == paused.session_id
    assert resumed.status == "runtime_ready"
    saved = json.loads(Path(resumed.artifact_paths.session_state_path).read_text(encoding="utf-8"))
    assert saved["status"] == "runtime_ready"


def _prepare_root(root_dir: Path) -> None:
    (root_dir / "data").mkdir(parents=True, exist_ok=True)
    (root_dir / "knowledge_base").mkdir(parents=True, exist_ok=True)
    source = Path("knowledge_base/pyaterochka.md").read_text(encoding="utf-8")
    (root_dir / "knowledge_base" / "pyaterochka.md").write_text(source, encoding="utf-8")
