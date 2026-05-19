"""Artifact generation for guided site onboarding."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from models.onboarding import ArtifactPaths
ArtifactGenerator = Callable[[Path, str], ArtifactPaths]


def generate_onboarding_artifacts(root_dir: Path, shop_slug: str) -> ArtifactPaths:
    """Create local runtime paths and repo scaffold paths for one site."""
    runtime_dir = root_dir / "data" / "onboarding" / shop_slug
    scaffold_dir = root_dir / "generated_scaffolds" / shop_slug
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (scaffold_dir / "knowledge_base").mkdir(parents=True, exist_ok=True)
    (scaffold_dir / "backends").mkdir(parents=True, exist_ok=True)
    (scaffold_dir / "captures").mkdir(parents=True, exist_ok=True)

    kb_draft_path = scaffold_dir / "knowledge_base" / f"{shop_slug}.md"
    backend_stub_path = scaffold_dir / "backends" / f"{shop_slug}_backend.py"
    capture_stub_path = scaffold_dir / "captures" / f"{shop_slug}_capture.py"

    if not kb_draft_path.exists():
        kb_draft_path.write_text(
            "# Knowledge Base Draft\n\n- base_url: \n- categories:\n",
            encoding="utf-8",
        )
    if not backend_stub_path.exists():
        backend_stub_path.write_text(
            '"""Store backend scaffold."""\n',
            encoding="utf-8",
        )
    if not capture_stub_path.exists():
        capture_stub_path.write_text(
            '"""Store capture scaffold."""\n',
            encoding="utf-8",
        )

    return ArtifactPaths(
        runtime_db_path=str(root_dir / "data" / "products.db"),
        runtime_report_dir=str(runtime_dir),
        session_state_path=str(runtime_dir / "onboarding_session.json"),
        kb_draft_path=str(kb_draft_path),
        backend_stub_path=str(backend_stub_path),
        capture_stub_path=str(capture_stub_path),
    )


def get_artifact_generator(name: str) -> ArtifactGenerator:
    """Return artifact generator by registry name."""
    normalized = str(name or "").strip().casefold()
    if normalized == "default":
        return generate_onboarding_artifacts
    raise ValueError(f"Unsupported artifact generator: {name}")
