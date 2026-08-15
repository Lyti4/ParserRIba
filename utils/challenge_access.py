"""Private checkpoint and remote-access authorization for challenge handoff."""

from __future__ import annotations

import asyncio
from enum import Enum
import json
import os
from pathlib import Path
import tempfile
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChallengeCheckpointState(str, Enum):
    BLOCKED_CHALLENGE = "blocked_challenge"
    RESOLVED = "resolved"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ChallengeCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_version: Literal[1] = 1
    run_id: str = Field(min_length=1)
    store: str = Field(min_length=1)
    attempt: int = Field(ge=1)
    state: ChallengeCheckpointState
    created_at: str = Field(min_length=1)
    updated_at: str = Field(min_length=1)


def challenge_access_command(action: str, unit: str) -> tuple[str, ...]:
    """Build the exact shell-free systemd access-control command."""
    if action not in {"start", "stop"} or unit != "parserriba-challenge-access.target":
        raise ValueError(
            "CHALLENGE_ACCESS_CONTROL_INVALID: expected start/stop of the allowlisted unit"
        )
    if action == "stop":
        return (
            "systemctl",
            "--user",
            "stop",
            "parserriba-challenge-web.service",
            "parserriba-challenge-vnc.service",
            unit,
        )
    return ("systemctl", "--user", "restart", unit)


def _challenge_access_authority_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if not runtime_dir:
        raise RuntimeError("CHALLENGE_ACCESS_RUNTIME_DIR_MISSING")
    directory = Path(runtime_dir) / "parserriba-challenge"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    return directory / "access-authority.json"


def _fsync_directory(path: Path) -> None:
    directory_fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def write_challenge_access_authority(
    checkpoint_path: Path,
    expected_run_id: str,
) -> Path:
    """Create private systemd authorization after same-run checkpoint validation."""
    checkpoint = validate_challenge_access_checkpoint(checkpoint_path, expected_run_id)
    target = _challenge_access_authority_path()
    payload = {
        "schema_version": 1,
        "run_id": checkpoint.run_id,
        "checkpoint_path": str(Path(checkpoint_path).resolve(strict=True)),
    }
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            os.chmod(temporary_path, 0o600)
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
        _fsync_directory(target.parent)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return target


def remove_challenge_access_authority() -> None:
    """Revoke systemd authorization even when access services are stopped."""
    target = _challenge_access_authority_path()
    target.unlink(missing_ok=True)
    _fsync_directory(target.parent)


async def set_challenge_access(
    unit: str,
    action: str,
    *,
    checkpoint_path: Path | None = None,
    expected_run_id: str = "",
    timeout_seconds: float = 15,
) -> bool:
    """Activate or revoke remote control without invoking a shell."""
    if not unit:
        return False
    if action == "start":
        if checkpoint_path is None:
            raise RuntimeError("CHALLENGE_ACCESS_CHECKPOINT_INVALID")
        write_challenge_access_authority(checkpoint_path, expected_run_id)
    command = challenge_access_command(action, unit)
    completed = False
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise RuntimeError("CHALLENGE_ACCESS_CONTROL_TIMEOUT") from None
        if process.returncode != 0:
            detail = (stderr or stdout).decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"CHALLENGE_ACCESS_CONTROL_FAILED: {detail[:240]}")
        completed = True
    finally:
        if action == "stop" or (action == "start" and not completed):
            remove_challenge_access_authority()
    return True


def write_challenge_checkpoint(path: Path, checkpoint: ChallengeCheckpoint) -> Path:
    """Atomically persist only the allowlisted challenge-control state."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    encoded = json.dumps(
        checkpoint.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    return target


def validate_challenge_access_checkpoint(
    path: Path,
    expected_run_id: str,
) -> ChallengeCheckpoint:
    """Require a blocked checkpoint owned by the run requesting remote access."""
    if not expected_run_id:
        raise RuntimeError("CHALLENGE_ACCESS_CHECKPOINT_RUN_MISMATCH")
    try:
        checkpoint = ChallengeCheckpoint.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except Exception:
        raise RuntimeError("CHALLENGE_ACCESS_CHECKPOINT_INVALID") from None
    if checkpoint.run_id != expected_run_id:
        raise RuntimeError("CHALLENGE_ACCESS_CHECKPOINT_RUN_MISMATCH")
    if checkpoint.state is not ChallengeCheckpointState.BLOCKED_CHALLENGE:
        raise RuntimeError("CHALLENGE_ACCESS_CHECKPOINT_NOT_BLOCKED")
    return checkpoint
