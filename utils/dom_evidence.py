"""Source-neutral inventory for already-captured rendered HTML evidence."""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from typing import Any


class _DOMInventoryParser(HTMLParser):
    """Count DOM structure without retaining element text or attribute values."""

    _NON_VISIBLE_TEXT_TAGS = frozenset({"script", "style", "template"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.attribute_name_counts: Counter[str] = Counter()
        self.tag_counts: Counter[str] = Counter()
        self.total_elements = 0
        self.json_ld_script_count = 0
        self.meta_refresh_present = False
        self.body_text_characters = 0
        self._body_depth = 0
        self._non_visible_text_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._record_element(tag, attrs)
        normalized_tag = tag.lower()
        if normalized_tag == "body":
            self._body_depth += 1
        if normalized_tag in self._NON_VISIBLE_TEXT_TAGS:
            self._non_visible_text_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._record_element(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "body" and self._body_depth:
            self._body_depth -= 1
        if normalized_tag in self._NON_VISIBLE_TEXT_TAGS and self._non_visible_text_depth:
            self._non_visible_text_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._body_depth and not self._non_visible_text_depth:
            self.body_text_characters += len(data.strip())

    def _record_element(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        self.total_elements += 1
        self.tag_counts[normalized_tag] += 1

        normalized_attrs: dict[str, str | None] = {}
        for name, value in attrs:
            if name:
                normalized_name = name.lower()
                self.attribute_name_counts[normalized_name] += 1
                normalized_attrs[normalized_name] = value

        if normalized_tag == "script" and str(normalized_attrs.get("type", "")).lower() == "application/ld+json":
            self.json_ld_script_count += 1
        if normalized_tag == "meta" and str(normalized_attrs.get("http-equiv", "")).lower() == "refresh":
            self.meta_refresh_present = True


def build_dom_inventory(page_html: str) -> dict[str, Any]:
    """Return JSON-safe structural metadata for a captured HTML document.

    The returned inventory deliberately stores counts and boolean capability flags,
    not page text or attribute values. Full raw evidence remains in the caller's
    separately persisted HTML snapshot.
    """

    parser = _DOMInventoryParser()
    parser.feed(page_html)
    parser.close()
    tags = dict(sorted(parser.tag_counts.items()))

    return {
        "total_elements": parser.total_elements,
        "tag_counts": tags,
        "attribute_name_counts": dict(sorted(parser.attribute_name_counts.items())),
        "script_count": tags.get("script", 0),
        "json_ld_script_count": parser.json_ld_script_count,
        "iframe_count": tags.get("iframe", 0),
        "form_count": tags.get("form", 0),
        "anchor_count": tags.get("a", 0),
        "image_count": tags.get("img", 0),
        "noscript_present": bool(tags.get("noscript", 0)),
        "meta_refresh_present": parser.meta_refresh_present,
        "body_text_characters": parser.body_text_characters,
    }
