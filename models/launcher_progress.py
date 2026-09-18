"""Typed progress events for launcher-safe background work."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LauncherProgressEvent(BaseModel):
    """Immutable progress event emitted by launcher workers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task_kind: str
    phase: str
    message: str
    current: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=0)
