"""Create local Local Agent OS ISA notes for ParserRIba agent work."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_AGENT_ROOT = ROOT / "agent-os"
OBSIDIAN_ENV_VAR = "PARSERRIBA_OBSIDIAN_VAULT"
DEFAULT_CRITERIA = (
    "Current evidence is written before code changes.",
    "RLM steps are bounded and stop on missing evidence.",
    "Verification commands are recorded before completion.",
)
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(
        r"(?i)\b(api[_-]?key|token|cookie|password|passwd|secret|proxy)\b"
        r"\s*[:=]\s*\S+"
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._-]{16,}"),
)


@dataclass(frozen=True)
class LocalAgentOSResult:
    """Paths created for one Local Agent OS work item."""

    item_id: str
    local_path: Path
    obsidian_path: Path | None


def slugify(value: str) -> str:
    ascii_value = value.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug[:64] or "work-item"


def resolve_obsidian_vault(cli_value: str | None) -> Path | None:
    if cli_value:
        return Path(cli_value)
    if OBSIDIAN_ENV_VAR in os.environ:
        return Path(os.environ[OBSIDIAN_ENV_VAR])
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, _kind = winreg.QueryValueEx(key, OBSIDIAN_ENV_VAR)
            if value:
                return Path(value)
        except OSError:
            return None
    return None


def render_isa_note(
    *,
    title: str,
    objective: str,
    current_state: str,
    ideal_state: str,
    criteria: Sequence[str],
    created_at: datetime,
) -> str:
    criteria_lines = "\n".join(f"- {criterion}" for criterion in criteria)
    created = created_at.isoformat(timespec="seconds")
    return f"""# Local Agent OS: {title}

- Created: {created}
- Objective: {objective}
- Scope: ParserRIba dev/agent workflow only; not product runtime.

## Current State

{current_state}

## Ideal State

{ideal_state}

## Acceptance Criteria

{criteria_lines}

## RLM Execution

- Method: recursive language-model work loop expressed as local notes.
- Max depth: 3.
- Max iterations per depth: 3.
- Budget stop: stop on missing evidence, failing guard or user decision.

### RLM Step Template

1. Context variable:
2. Question:
3. Result:
4. Next call or stop:

## PAI-Inspired Local Memory

- Source context:
- Decisions:
- Migration notes:
- Containment notes:
- Optional Obsidian mirror:

## Decisions

- Pending.

## Verification

- Pending.

## Next Action

- Fill the first RLM step before making risky changes.
"""


def assert_safe_for_obsidian(text: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError("Refusing to mirror possible secret content to Obsidian.")


def create_work_item(
    *,
    title: str,
    objective: str,
    current_state: str = "Not captured yet.",
    ideal_state: str = "Not captured yet.",
    criteria: Sequence[str] = DEFAULT_CRITERIA,
    agent_root: Path = DEFAULT_AGENT_ROOT,
    obsidian_vault: Path | None = None,
    mirror_obsidian: bool = False,
    created_at: datetime | None = None,
) -> LocalAgentOSResult:
    created = created_at if created_at is not None else datetime.now()
    item_id = f"{created.strftime('%Y%m%d-%H%M%S')}-{slugify(title)}"
    content = render_isa_note(
        title=title,
        objective=objective,
        current_state=current_state,
        ideal_state=ideal_state,
        criteria=criteria,
        created_at=created,
    )

    obsidian_path: Path | None = None
    if mirror_obsidian:
        if obsidian_vault is None:
            raise ValueError(
                "Obsidian mirror requested, but no vault path was provided."
            )
        assert_safe_for_obsidian(content)
        obsidian_path = (
            obsidian_vault / "ParserRIba" / "Local Agent OS" / f"{item_id}.md"
        )

    local_path = agent_root / "WORK" / item_id / "ISA.md"
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding="utf-8")

    if obsidian_path is not None:
        obsidian_path.parent.mkdir(parents=True, exist_ok=True)
        obsidian_path.write_text(content, encoding="utf-8")

    return LocalAgentOSResult(
        item_id=item_id,
        local_path=local_path,
        obsidian_path=obsidian_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="create a Local Agent OS note")
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument("--objective", required=True)
    new_parser.add_argument("--current-state", default="Not captured yet.")
    new_parser.add_argument("--ideal-state", default="Not captured yet.")
    new_parser.add_argument("--criteria", action="append")
    new_parser.add_argument("--agent-root", default=str(DEFAULT_AGENT_ROOT))
    new_parser.add_argument("--obsidian-vault")
    new_parser.add_argument("--mirror-obsidian", action="store_true")

    rlm_start = subparsers.add_parser("rlm-start", help="start an RLM trajectory")
    rlm_start.add_argument("--title", required=True)
    rlm_start.add_argument("--objective", required=True)
    rlm_start.add_argument("--mode", default="manual")
    rlm_start.add_argument("--max-depth", type=int, default=3)
    rlm_start.add_argument("--max-iterations", type=int, default=3)
    rlm_start.add_argument("--agent-root", default=str(DEFAULT_AGENT_ROOT))
    rlm_start.add_argument("--obsidian-vault")
    rlm_start.add_argument("--mirror-obsidian", action="store_true")

    rlm_step = subparsers.add_parser("rlm-step", help="append an RLM step")
    rlm_step.add_argument("--trajectory", required=True)
    rlm_step.add_argument("--context", required=True)
    rlm_step.add_argument("--question", required=True)
    rlm_step.add_argument("--result", required=True)
    rlm_step.add_argument("--next-decision", required=True)
    rlm_step.add_argument("--depth", type=int, default=1)
    rlm_step.add_argument("--iteration", type=int, default=1)
    rlm_step.add_argument("--evidence", action="append")
    rlm_step.add_argument("--agent-root", default=str(DEFAULT_AGENT_ROOT))
    rlm_step.add_argument("--obsidian-vault")
    rlm_step.add_argument("--mirror-obsidian", action="store_true")

    rlm_close = subparsers.add_parser("rlm-close", help="close an RLM trajectory")
    rlm_close.add_argument("--trajectory", required=True)
    rlm_close.add_argument("--summary", required=True)
    rlm_close.add_argument("--decision", action="append", default=[])
    rlm_close.add_argument("--verification", action="append", default=[])
    rlm_close.add_argument("--risk", action="append", default=[])
    rlm_close.add_argument("--next-action", required=True)
    rlm_close.add_argument("--agent-root", default=str(DEFAULT_AGENT_ROOT))
    rlm_close.add_argument("--obsidian-vault")
    rlm_close.add_argument("--mirror-obsidian", action="store_true")

    rlm_render = subparsers.add_parser("rlm-render", help="render an RLM trajectory")
    rlm_render.add_argument("--trajectory", required=True)
    rlm_render.add_argument("--agent-root", default=str(DEFAULT_AGENT_ROOT))
    rlm_render.add_argument("--obsidian-vault")
    rlm_render.add_argument("--mirror-obsidian", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "new":
        return _run_rlm_command(args)

    criteria = args.criteria if args.criteria is not None else DEFAULT_CRITERIA
    obsidian_vault = resolve_obsidian_vault(args.obsidian_vault)
    try:
        result = create_work_item(
            title=args.title,
            objective=args.objective,
            current_state=args.current_state,
            ideal_state=args.ideal_state,
            criteria=criteria,
            agent_root=Path(args.agent_root),
            obsidian_vault=obsidian_vault,
            mirror_obsidian=args.mirror_obsidian,
        )
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    sys.stdout.write("Created Local Agent OS ISA:\n")
    sys.stdout.write(f"- local: {result.local_path}\n")
    if result.obsidian_path is not None:
        sys.stdout.write(f"- obsidian: {result.obsidian_path}\n")
    return 0


def _run_rlm_command(args: argparse.Namespace) -> int:
    from scripts.local_agent_rlm import (
        append_step,
        close_trajectory,
        parse_evidence,
        render_trajectory,
        start_trajectory,
    )

    obsidian_vault = resolve_obsidian_vault(args.obsidian_vault)
    try:
        if args.command == "rlm-start":
            paths = start_trajectory(
                title=args.title,
                objective=args.objective,
                mode=args.mode,
                max_depth=args.max_depth,
                max_iterations=args.max_iterations,
                agent_root=Path(args.agent_root),
                obsidian_vault=obsidian_vault,
                mirror_obsidian=args.mirror_obsidian,
            )
        elif args.command == "rlm-step":
            paths = append_step(
                trajectory_id=args.trajectory,
                context=args.context,
                question=args.question,
                result=args.result,
                next_decision=args.next_decision,
                depth=args.depth,
                iteration=args.iteration,
                evidence_refs=parse_evidence(args.evidence),
                agent_root=Path(args.agent_root),
                obsidian_vault=obsidian_vault,
                mirror_obsidian=args.mirror_obsidian,
            )
        elif args.command == "rlm-close":
            paths = close_trajectory(
                trajectory_id=args.trajectory,
                summary=args.summary,
                decisions=args.decision,
                verification=args.verification,
                risks=args.risk,
                next_action=args.next_action,
                agent_root=Path(args.agent_root),
                obsidian_vault=obsidian_vault,
                mirror_obsidian=args.mirror_obsidian,
            )
        elif args.command == "rlm-render":
            paths = render_trajectory(
                trajectory_id=args.trajectory,
                agent_root=Path(args.agent_root),
                obsidian_vault=obsidian_vault,
                mirror_obsidian=args.mirror_obsidian,
            )
        else:
            raise ValueError(f"Unknown command: {args.command}")
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    sys.stdout.write("RLM trajectory updated:\n")
    sys.stdout.write(f"- id: {paths.trajectory_id}\n")
    sys.stdout.write(f"- json: {paths.json_path}\n")
    sys.stdout.write(f"- markdown: {paths.markdown_path}\n")
    if args.mirror_obsidian and paths.obsidian_path is not None:
        sys.stdout.write(f"- obsidian: {paths.obsidian_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
