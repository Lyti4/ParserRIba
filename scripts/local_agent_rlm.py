"""Structured RLM trajectories for ParserRIba Local Agent OS."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Sequence

from scripts.local_agent_os import (
    DEFAULT_AGENT_ROOT,
    assert_safe_for_obsidian,
    slugify,
)


DECISIONS = {"continue", "stop", "blocked", "needs_user"}
MODES = {"manual", "local_assisted", "external_adapter"}


@dataclass
class RLMEvidenceRef:
    """Safe reference to evidence used by one RLM step."""

    kind: str
    label: str
    target: str
    safe_to_mirror: bool = True


@dataclass
class RLMStep:
    """One context-question-result-decision unit."""

    step_id: int
    depth: int
    iteration: int
    context: str
    question: str
    result: str
    next_decision: str
    evidence_refs: list[RLMEvidenceRef] = field(default_factory=list)
    created_at: str = ""


@dataclass
class RLMCloseout:
    """Final trajectory summary."""

    summary: str
    decisions: list[str]
    verification: list[str]
    risks: list[str]
    next_action: str
    closed_at: str


@dataclass
class RLMTrajectory:
    """Local structured RLM work record."""

    trajectory_id: str
    title: str
    objective: str
    mode: str = "manual"
    max_depth: int = 3
    max_iterations: int = 3
    created_at: str = ""
    updated_at: str = ""
    status: str = "active"
    steps: list[RLMStep] = field(default_factory=list)
    closeout: RLMCloseout | None = None


@dataclass(frozen=True)
class RLMPaths:
    """Filesystem paths for one trajectory."""

    trajectory_id: str
    root: Path
    json_path: Path
    markdown_path: Path
    obsidian_path: Path | None = None


def start_trajectory(
    *,
    title: str,
    objective: str,
    mode: str = "manual",
    max_depth: int = 3,
    max_iterations: int = 3,
    agent_root: Path = DEFAULT_AGENT_ROOT,
    obsidian_vault: Path | None = None,
    mirror_obsidian: bool = False,
    created_at: datetime | None = None,
) -> RLMPaths:
    if mode not in MODES:
        raise ValueError(f"Unknown RLM mode: {mode}")
    created = created_at or datetime.now()
    now = created.isoformat(timespec="seconds")
    trajectory = RLMTrajectory(
        trajectory_id=f"{created.strftime('%Y%m%d-%H%M%S')}-{slugify(title)}",
        title=title,
        objective=objective,
        mode=mode,
        max_depth=max_depth,
        max_iterations=max_iterations,
        created_at=now,
        updated_at=now,
    )
    paths = _paths_for(trajectory.trajectory_id, agent_root, obsidian_vault)
    _write_trajectory(trajectory, paths, mirror_obsidian=mirror_obsidian)
    return paths


def append_step(
    *,
    trajectory_id: str,
    context: str,
    question: str,
    result: str,
    next_decision: str,
    depth: int = 1,
    iteration: int = 1,
    evidence_refs: Sequence[RLMEvidenceRef] = (),
    agent_root: Path = DEFAULT_AGENT_ROOT,
    obsidian_vault: Path | None = None,
    mirror_obsidian: bool = False,
) -> RLMPaths:
    if next_decision not in DECISIONS:
        raise ValueError(f"Unknown next decision: {next_decision}")
    trajectory, paths = load_trajectory(trajectory_id, agent_root, obsidian_vault)
    if trajectory.status != "active":
        raise ValueError("Cannot append a step to a non-active trajectory.")
    step = RLMStep(
        step_id=len(trajectory.steps) + 1,
        depth=depth,
        iteration=iteration,
        context=context,
        question=question,
        result=result,
        next_decision=next_decision,
        evidence_refs=list(evidence_refs),
        created_at=_now(),
    )
    trajectory.steps.append(step)
    trajectory.updated_at = _now()
    _write_trajectory(trajectory, paths, mirror_obsidian=mirror_obsidian)
    return paths


def close_trajectory(
    *,
    trajectory_id: str,
    summary: str,
    decisions: Sequence[str],
    verification: Sequence[str],
    risks: Sequence[str],
    next_action: str,
    agent_root: Path = DEFAULT_AGENT_ROOT,
    obsidian_vault: Path | None = None,
    mirror_obsidian: bool = False,
) -> RLMPaths:
    trajectory, paths = load_trajectory(trajectory_id, agent_root, obsidian_vault)
    trajectory.status = "closed"
    trajectory.updated_at = _now()
    trajectory.closeout = RLMCloseout(
        summary=summary,
        decisions=list(decisions),
        verification=list(verification),
        risks=list(risks),
        next_action=next_action,
        closed_at=_now(),
    )
    _write_trajectory(trajectory, paths, mirror_obsidian=mirror_obsidian)
    return paths


def render_trajectory(
    *,
    trajectory_id: str,
    agent_root: Path = DEFAULT_AGENT_ROOT,
    obsidian_vault: Path | None = None,
    mirror_obsidian: bool = False,
) -> RLMPaths:
    trajectory, paths = load_trajectory(trajectory_id, agent_root, obsidian_vault)
    _write_trajectory(trajectory, paths, mirror_obsidian=mirror_obsidian)
    return paths


def load_trajectory(
    trajectory_id: str,
    agent_root: Path = DEFAULT_AGENT_ROOT,
    obsidian_vault: Path | None = None,
) -> tuple[RLMTrajectory, RLMPaths]:
    paths = _paths_for(trajectory_id, agent_root, obsidian_vault)
    data = json.loads(paths.json_path.read_text(encoding="utf-8"))
    steps = [
        RLMStep(
            evidence_refs=[
                RLMEvidenceRef(**ref) for ref in step.get("evidence_refs", [])
            ],
            **{key: value for key, value in step.items() if key != "evidence_refs"},
        )
        for step in data.get("steps", [])
    ]
    closeout_data = data.get("closeout")
    closeout = RLMCloseout(**closeout_data) if closeout_data else None
    trajectory = RLMTrajectory(
        steps=steps,
        closeout=closeout,
        **{key: value for key, value in data.items() if key not in {"steps", "closeout"}},
    )
    return trajectory, paths


def parse_evidence(values: Sequence[str] | None) -> list[RLMEvidenceRef]:
    refs: list[RLMEvidenceRef] = []
    for value in values or ():
        parts = value.split("|", 3)
        if len(parts) != 3:
            raise ValueError("Evidence must use kind|label|target format.")
        refs.append(RLMEvidenceRef(kind=parts[0], label=parts[1], target=parts[2]))
    return refs


def _paths_for(
    trajectory_id: str,
    agent_root: Path,
    obsidian_vault: Path | None,
) -> RLMPaths:
    root = agent_root / "WORK" / trajectory_id
    obsidian_path = None
    if obsidian_vault is not None:
        obsidian_path = (
            obsidian_vault / "ParserRIba" / "Local Agent OS" / f"{trajectory_id}.md"
        )
    return RLMPaths(
        trajectory_id=trajectory_id,
        root=root,
        json_path=root / "trajectory.json",
        markdown_path=root / "trajectory.md",
        obsidian_path=obsidian_path,
    )


def _write_trajectory(
    trajectory: RLMTrajectory,
    paths: RLMPaths,
    *,
    mirror_obsidian: bool,
) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.json_path.write_text(
        json.dumps(asdict(trajectory), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown = _render_markdown(trajectory)
    paths.markdown_path.write_text(markdown, encoding="utf-8")
    if mirror_obsidian:
        if paths.obsidian_path is None:
            raise ValueError("Obsidian mirror requested, but no vault path was provided.")
        assert_safe_for_obsidian(markdown)
        paths.obsidian_path.parent.mkdir(parents=True, exist_ok=True)
        paths.obsidian_path.write_text(markdown, encoding="utf-8")


def _render_markdown(trajectory: RLMTrajectory) -> str:
    lines = [
        f"# RLM Trajectory: {trajectory.title}",
        "",
        f"- Created: {trajectory.created_at}",
        f"- Updated: {trajectory.updated_at}",
        f"- Status: {trajectory.status}",
        f"- Mode: {trajectory.mode}",
        f"- Objective: {trajectory.objective}",
        f"- Limits: depth {trajectory.max_depth}, iterations {trajectory.max_iterations}",
        "",
        "## Steps",
    ]
    if not trajectory.steps:
        lines.extend(["", "- No steps recorded yet."])
    for step in trajectory.steps:
        lines.extend(
            [
                "",
                f"### Step {step.step_id}",
                "",
                f"- Depth: {step.depth}",
                f"- Iteration: {step.iteration}",
                f"- Created: {step.created_at}",
                f"- Next decision: {step.next_decision}",
                "",
                "Context:",
                "",
                step.context,
                "",
                "Question:",
                "",
                step.question,
                "",
                "Result:",
                "",
                step.result,
            ]
        )
        if step.evidence_refs:
            lines.extend(["", "Evidence:"])
            for ref in step.evidence_refs:
                lines.append(f"- {ref.kind}: {ref.label} -> {ref.target}")
    if trajectory.closeout is not None:
        closeout = trajectory.closeout
        lines.extend(
            [
                "",
                "## Closeout",
                "",
                closeout.summary,
                "",
                "Decisions:",
                *_bullets(closeout.decisions),
                "",
                "Verification:",
                *_bullets(closeout.verification),
                "",
                "Risks:",
                *_bullets(closeout.risks),
                "",
                f"Next action: {closeout.next_action}",
            ]
        )
    return "\n".join(lines) + "\n"


def _bullets(values: Sequence[str]) -> list[str]:
    return [f"- {value}" for value in values] or ["- None recorded."]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
