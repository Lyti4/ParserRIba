"""Extract and normalize site-provided category filters from DOM and API payloads."""

from __future__ import annotations

from typing import Any

from utils.site_filter_descriptors import (
    FacetDescriptor,
    descriptors_to_option_map,
    extract_filter_descriptors_from_payload,
    normalize_filter_descriptors,
)

SITE_FILTER_DOM_SCRIPT = """
() => {
  const clean = (value) => String(value || '').replace(/\\s+/g, ' ').trim();
  const isFilterRoot = (el) => {
    const raw = `${el.className || ''} ${el.getAttribute('data-testid') || ''} ${el.getAttribute('aria-label') || ''}`.toLowerCase();
    return raw.includes('filter') || raw.includes('facet') || raw.includes('фильтр') || el.tagName === 'ASIDE';
  };
  const labelFor = (control) => {
    const id = control.getAttribute('id');
    if (id) {
      const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (label) return clean(label.innerText || label.textContent);
    }
    const ownLabel = control.closest('label');
    if (ownLabel) return clean(ownLabel.innerText || ownLabel.textContent);
    const parent = control.parentElement;
    return parent ? clean(parent.innerText || parent.textContent) : '';
  };
  const titleFor = (control, root) => {
    const fieldset = control.closest('fieldset');
    const legend = fieldset ? fieldset.querySelector('legend') : null;
    if (legend && clean(legend.innerText)) return clean(legend.innerText);
    const section = control.closest('section, article, [role="group"], div');
    const heading = section ? section.querySelector('h1,h2,h3,h4,h5,h6,[class*="title"],[class*="name"]') : null;
    if (heading && clean(heading.innerText)) return clean(heading.innerText);
    return clean(root.getAttribute('aria-label')) || 'Фильтры сайта';
  };
  const groups = {};
  const roots = Array.from(document.querySelectorAll('aside, form, [class], [data-testid], [aria-label]')).filter(isFilterRoot);
  for (const root of roots) {
    const controls = root.querySelectorAll('input[type="checkbox"], input[type="radio"], [role="checkbox"], [aria-checked]');
    for (const control of controls) {
      const option = labelFor(control);
      if (!option || option.length > 80) continue;
      const title = titleFor(control, root);
      if (!groups[title]) groups[title] = new Set();
      groups[title].add(option);
    }
  }
  return Object.fromEntries(Object.entries(groups).map(([key, values]) => [key, Array.from(values)]));
}
"""


async def collect_site_filter_facets(page: Any) -> dict[str, list[str]]:
    """Collect currently visible category filter options from a browser page."""
    try:
        raw = await page.evaluate(SITE_FILTER_DOM_SCRIPT)
    except Exception:
        return {}
    return normalize_site_filter_facets(raw)


def normalize_site_filter_facets(raw: Any) -> dict[str, list[str]]:
    """Normalize site filter groups to a field -> options mapping."""
    return descriptors_to_option_map(normalize_site_filter_descriptors(raw, source="site_dom"))


def normalize_site_filter_descriptors(raw: Any, *, source: str = "site_api") -> list[FacetDescriptor]:
    """Normalize raw DOM/API filter data into structured facet descriptors."""
    return normalize_filter_descriptors(raw, source=source)


def merge_site_filter_facets(*items: Any) -> dict[str, list[str]]:
    """Merge site filter maps without losing option order."""
    merged: dict[str, list[str]] = {}
    for item in items:
        for title, options in normalize_site_filter_facets(item).items():
            target = merged.setdefault(title, [])
            for option in options:
                if option not in target:
                    target.append(option)
    return merged


def extract_site_filter_facets_from_payload(payload: Any) -> dict[str, list[str]]:
    """Extract common API facet payloads into a compatibility field -> options map."""
    return descriptors_to_option_map(extract_site_filter_descriptors_from_payload(payload))


def extract_site_filter_descriptors_from_payload(payload: Any) -> list[FacetDescriptor]:
    """Extract common API facet payloads into structured filter descriptors."""
    return extract_filter_descriptors_from_payload(payload)
