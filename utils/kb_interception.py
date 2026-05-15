"""Knowledge-base parsing helpers for API interception markers."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field


class InterceptionConfig(BaseModel):
    """Safe API interception markers for diagnostics."""

    allowed_hosts: list[str] = Field(default_factory=list)
    product_api_path_markers: list[str] = Field(default_factory=list)
    api_path_markers: list[str] = Field(default_factory=list)
    challenge_markers: list[str] = Field(default_factory=list)
    image_markers: list[str] = Field(default_factory=list)
    script_markers: list[str] = Field(default_factory=list)


def parse_interception_section(content: str) -> InterceptionConfig:
    """Parse the optional API Interception section."""
    section = extract_named_section(content, "API Interception")
    if not section:
        return InterceptionConfig()
    fields = {
        "allowed_hosts",
        "product_api_path_markers",
        "api_path_markers",
        "challenge_markers",
        "image_markers",
        "script_markers",
    }
    values: dict[str, list[str]] = {field: [] for field in fields}
    current_field: str | None = None
    for line in section.splitlines():
        stripped = line.strip()
        header = re.match(r"^-\s+\**([A-Za-z_]+)\**:\s*(.*)$", stripped)
        if header and header.group(1) in fields:
            current_field = header.group(1)
            values[current_field].extend(extract_inline_values(header.group(2)))
            continue
        if current_field and stripped.startswith("-"):
            values[current_field].extend(extract_inline_values(stripped[1:].strip()))
    return InterceptionConfig(**{key: unique_non_empty(items) for key, items in values.items()})


def extract_named_section(content: str, title: str) -> str:
    """Extract a Markdown section by title text."""
    title_lower = title.lower()
    in_section = False
    section_lines: list[str] = []
    for line in content.split("\n"):
        if line.startswith("## ") and title_lower in line.lower():
            in_section = True
            continue
        if line.startswith("## ") and in_section:
            break
        if in_section:
            section_lines.append(line)
    return "\n".join(section_lines)


def extract_inline_values(text: str) -> list[str]:
    """Extract backtick or comma-separated values from one KB line."""
    backtick_values = re.findall(r"`([^`]+)`", text)
    if backtick_values:
        return [value.strip() for value in backtick_values]
    return [item.strip() for item in text.split(",") if item.strip()]


def unique_non_empty(values: list[str]) -> list[str]:
    """Return unique non-empty values while preserving order."""
    result: list[str] = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
