"""Tests for typed launcher progress events."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.launcher_progress import LauncherProgressEvent


def test_launcher_progress_event_is_immutable() -> None:
    event = LauncherProgressEvent(
        task_kind="product_export",
        phase="collect_products",
        message="Сбор товаров",
        current=1,
        total=3,
    )

    assert event.task_kind == "product_export"
    assert event.current == 1
    with pytest.raises(ValidationError, match="frozen"):
        event.current = 2


def test_launcher_progress_event_round_trips_as_json_data() -> None:
    event = LauncherProgressEvent(
        task_kind="research",
        phase="build_tree",
        message="Подготовка дерева каталога",
        current=None,
        total=None,
    )

    payload = event.model_dump(mode="json")
    loaded = LauncherProgressEvent(**payload)

    assert loaded == event
    assert payload == {
        "task_kind": "research",
        "phase": "build_tree",
        "message": "Подготовка дерева каталога",
        "current": None,
        "total": None,
    }


def test_launcher_progress_event_rejects_negative_counts() -> None:
    with pytest.raises(ValidationError):
        LauncherProgressEvent(
            task_kind="product_export",
            phase="collect_products",
            message="Сбор товаров",
            current=-1,
            total=3,
        )
