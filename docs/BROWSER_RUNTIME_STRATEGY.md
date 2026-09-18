# Browser Runtime Strategy

Date: 2026-06-05

## Decision

ParserRIba should support a second browser runtime through a controlled
browser-runtime contract, but Camoufox remains the stable default. Further
second-browser work is deferred until the store-neutral project unification is
complete enough that root/shared layers no longer leak Pyaterochka defaults.

CloakBrowser is a candidate experimental Chromium backend. It should not be
bundled into a commercial installer or treated as a required dependency until
licensing, support and A/B smoke evidence are resolved.

## Current Status

Paused after Slice 1.

Completed:

- browser runtime request/availability models;
- runtime registry with Camoufox as default;
- Camoufox backend adapter delegating to the existing launch builder;
- browser discovery routed through the registry with default `camoufox`.

Deferred:

- launcher UI for choosing browser runtime;
- StoreProfile browser-runtime preferences;
- optional CloakBrowser package/backend;
- A/B browser smoke comparison.

Reason: ParserRIba first needs full store-neutral unification of shared roots,
task routing, reports, filters, profile naming and launcher defaults. Expanding
browser count before that would add support surface while the product contract
is still being cleaned up.

## Why

ParserRIba currently depends on Camoufox for protected-store work:

- persistent profile;
- proxy and GeoIP;
- human-like behavior;
- safe network/API interception;
- manual captcha/challenge diagnostics;
- async Playwright-compatible browser flow.

A Chromium-like runtime may help on stores where Chrome behavior performs
better than Firefox-like behavior, but adding it as an uncontrolled parallel
path would increase support risk.

## Product Rules

- The launcher chooses browser runtime before research starts.
- Camoufox is the recommended default.
- CloakBrowser is shown as experimental only when installed and allowed by
  policy.
- Runtime selection is saved per StoreProfile.
- Runtime diagnostics are saved with sessions and support artifacts.
- Unknown/new sites remain `discovery_only` until a real product adapter exists.
- Browser binaries, profiles, cookies and credentials stay out of Git.
- Do not hide runtime downloads or auto-updates from the user.
- Do not redistribute CloakBrowser binaries without explicit licensing approval.

## Planned Feature

The spec-kit feature lives in:

```text
specs/001-browser-runtime-selection/
```

Implementation order when this work resumes:

1. Define the runtime contract and registry.
2. Route the existing Camoufox path through the contract.
3. Add profile and launcher runtime selection.
4. Add optional CloakBrowser backend and availability checks.
5. Add A/B smoke diagnostics.
6. Update support and release documentation.

## Plugin Support

No plugin replaces this implementation. Plugins are support tools:

- Superpowers for planning, TDD and review discipline.
- spec-kit for feature specification and task breakdown.
- graphify for impact analysis.
- Figma for launcher UI design.
- CodeRabbit/GitHub for review and backup.
- Mem for safe high-level decision memory.
