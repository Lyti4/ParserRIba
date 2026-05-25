"""Local task/actor contracts for launcher and automation flows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TASK_SCHEMA_VERSION = 1
TaskStatus = Literal["ok", "empty", "failed", "needs_operator", "discovery_only", "scaffold_ready", "runtime_ready"]


class RunManifest(BaseModel):
    """Machine-readable result for one local task run."""

    task_name: str
    shop: str
    intent: str = "fish_catalog"
    input: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime = Field(default_factory=datetime.utcnow)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    schema_version: int = TASK_SCHEMA_VERSION
