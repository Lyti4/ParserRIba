"""Human challenge handoff coordination without browser/runtime leakage."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from enum import Enum
import ipaddress
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from pydantic import BaseModel, ConfigDict, Field

from utils.challenge_access import (
    ChallengeCheckpoint,
    ChallengeCheckpointState,
    challenge_access_command,
    remove_challenge_access_authority,
    set_challenge_access,
    validate_challenge_access_checkpoint,
    write_challenge_access_authority,
    write_challenge_checkpoint,
)


class ChallengeWaitStatus(str, Enum):
    RESOLVED = "resolved"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ChallengeWaitResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: ChallengeWaitStatus
    polls: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)


def challenge_view_url(value: str) -> str:
    """Validate a private, noncredentialed noVNC URL for user display."""
    normalized = str(value or "").strip()
    parsed = urlsplit(normalized)
    private_host = False
    if parsed.hostname == "localhost":
        private_host = True
    elif parsed.hostname:
        try:
            address = ipaddress.ip_address(parsed.hostname)
            private_host = address.is_loopback or any(
                address in network
                for network in (
                    ipaddress.ip_network("10.0.0.0/8"),
                    ipaddress.ip_network("172.16.0.0/12"),
                    ipaddress.ip_network("192.168.0.0/16"),
                    ipaddress.ip_network("fc00::/7"),
                )
            )
        except ValueError:
            private_host = False
    allowed_query_keys = {
        "autoconnect",
        "compression",
        "logging",
        "path",
        "quality",
        "reconnect",
        "reconnect_delay",
        "resize",
        "show_dot",
        "view_only",
    }
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    safe_query = all(key in allowed_query_keys for key, _ in query_pairs) and all(
        not any(marker in value.lower() for marker in ("password", "token", "secret", "cookie"))
        for _, value in query_pairs
    )
    invalid = (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or not private_host
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
        or not safe_query
    )
    if invalid:
        raise ValueError("CHALLENGE_VIEW_URL_INVALID: expected a noncredentialed HTTP(S) URL")
    return normalized


def resolve_challenge_browser_headless(
    requested: bool | str | None,
    *,
    challenge_view: str,
    platform: str,
) -> bool | str:
    """Keep the remote handoff browser on the same shared headed display."""
    if challenge_view:
        challenge_view_url(challenge_view)
        if requested is not None and requested is not False:
            raise ValueError(
                "CHALLENGE_VIEW_REQUIRES_HEADED_BROWSER: remote handoff cannot use headless mode"
            )
        return False
    if requested is None:
        return False if platform == "win32" else "virtual"
    return requested


async def wait_for_challenge_resolution(
    check_resolved: Callable[[], Awaitable[bool]],
    *,
    timeout_seconds: float,
    poll_interval_seconds: float = 1.0,
    cancelled: Callable[[], bool] | None = None,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
    monotonic: Callable[[], float] | None = None,
) -> ChallengeWaitResult:
    """Wait cooperatively until the browser adapter reports challenge resolution."""
    if timeout_seconds <= 0:
        raise ValueError("CHALLENGE_TIMEOUT_INVALID: timeout_seconds must be positive")
    if poll_interval_seconds <= 0:
        raise ValueError("CHALLENGE_POLL_INTERVAL_INVALID: poll interval must be positive")

    clock = monotonic or asyncio.get_running_loop().time
    started_at = clock()
    deadline = started_at + timeout_seconds
    polls = 0

    while True:
        if cancelled is not None and cancelled():
            return ChallengeWaitResult(
                status=ChallengeWaitStatus.CANCELLED,
                polls=polls,
                elapsed_seconds=max(0.0, clock() - started_at),
            )

        remaining = deadline - clock()
        if remaining <= 0:
            return ChallengeWaitResult(
                status=ChallengeWaitStatus.TIMED_OUT,
                polls=polls,
                elapsed_seconds=max(0.0, clock() - started_at),
            )

        polls += 1
        try:
            resolved = await asyncio.wait_for(check_resolved(), timeout=remaining)
        except asyncio.TimeoutError:
            return ChallengeWaitResult(
                status=ChallengeWaitStatus.TIMED_OUT,
                polls=polls,
                elapsed_seconds=max(0.0, clock() - started_at),
            )
        if resolved:
            return ChallengeWaitResult(
                status=ChallengeWaitStatus.RESOLVED,
                polls=polls,
                elapsed_seconds=max(0.0, clock() - started_at),
            )

        remaining = deadline - clock()
        if remaining <= 0:
            return ChallengeWaitResult(
                status=ChallengeWaitStatus.TIMED_OUT,
                polls=polls,
                elapsed_seconds=max(0.0, clock() - started_at),
            )
        await sleep(min(poll_interval_seconds, remaining))
