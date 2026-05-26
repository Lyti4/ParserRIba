"""Artifact generation for guided site onboarding."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from models.onboarding import ArtifactPaths
ArtifactGenerator = Callable[[Path, str], ArtifactPaths]


def generate_onboarding_artifacts(root_dir: Path, shop_slug: str) -> ArtifactPaths:
    """Create local runtime and operator-note paths for one site."""
    runtime_dir = root_dir / "data" / "onboarding" / shop_slug
    (runtime_dir / "profiles").mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    notes_dir = runtime_dir / "operator_notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    kb_draft_path = notes_dir / f"{shop_slug}_knowledge_base_draft.md"

    if not kb_draft_path.exists():
        kb_draft_path.write_text(
            "# Knowledge Base Draft\n\n- base_url: \n- categories:\n",
            encoding="utf-8",
        )

    return ArtifactPaths(
        runtime_db_path=str(root_dir / "data" / "products.db"),
        runtime_report_dir=str(runtime_dir),
        session_state_path=str(runtime_dir / "onboarding_session.json"),
        kb_draft_path=str(kb_draft_path),
    )


def get_artifact_generator(name: str) -> ArtifactGenerator:
    """Return artifact generator by registry name."""
    normalized = str(name or "").strip().casefold()
    if normalized == "default":
        return generate_onboarding_artifacts
    raise ValueError(f"Unsupported artifact generator: {name}")
