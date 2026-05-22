# ParserRIba Tools Policy

Date: 2026-05-20

## Purpose

This file defines where external development tools belong in the ParserRIba
workflow and where they do not.

## Current Rule

ParserRIba runtime remains:

`Windows Python -> Camoufox -> local SQLite/JSON/Excel`

External developer tools may support coding, review, or automation work, but
they are not part of the parser runtime unless a separate decision explicitly
promotes them into the shipped product.

For the desktop launcher path specifically:

- do not search for a special "launcher plugin" as a runtime dependency;
- the launcher should be implemented directly in `PySide6`;
- existing plugins are auxiliary only:
  - `GitHub` later for release automation;
  - `Figma` only for optional screen mockups;
  - `Browser` is mainly for local web surfaces and is not central to the
    desktop launcher.

## CodeRabbit

CodeRabbit is a code review tool.

Use it for:

- review of committed changes;
- review of a narrow, intentional uncommitted diff;
- feedback after a refactor or feature slice is already implemented.

Do not use it for:

- live scraping;
- parser runtime decisions;
- review of broad dirty worktrees with local artifacts in `data/`,
  `generated_scaffolds/`, `logs/`, `build/`, or `dist/`.

Windows note:

- CodeRabbit CLI is run through WSL/Ubuntu on this machine.
- The safe local entrypoint is `scripts/run_coderabbit_review.py`.

Preferred workflow:

1. stage or commit only the intended scope;
2. keep generated artifacts out of the review scope;
3. run committed review first;
4. use uncommitted review only for small, clean diffs.

## YepCode

YepCode is a workspace/process automation tool.

Use it for:

- local or remote process work inside a real YepCode workspace;
- MCP/process exposure when the project explicitly chooses that model later.

Do not use it for:

- parser runtime on v1;
- code review;
- adding an extra platform layer without a concrete process/workspace use case.

Current status:

- YepCode CLI may remain installed locally.
- It is not part of ParserRIba runtime or launcher flow.
- Do not integrate it deeper until there is an explicit workspace/process plan.

## Decision Boundary

Before adding any external tool into the project flow, answer these questions:

1. Is it runtime, review, or automation only?
2. Does it reduce real project complexity, or add a new control plane?
3. Can the same task already be handled by local Python, git, tests, and docs?
4. Does it require paid services, cloud coupling, or hidden credentials?

If the answer is unclear, keep the tool out of runtime and treat it as optional
developer tooling only.
