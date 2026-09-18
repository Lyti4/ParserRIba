# ParserRIba Tools Policy

Date: 2026-05-20

## Purpose

This file defines where external development tools belong in the ParserRIba
workflow and where they do not.

## Current Rule

ParserRIba runtime remains:

`Windows Python -> Camoufox -> local SQLite/JSON/Excel`

The authoritative working copy is the local workspace
`C:\tmp\ParserRIba-clean`. GitHub is a commit/history/review target, not the
place where ParserRIba runs. Generated data, browser profiles, SQLite databases,
reports and diagnostics stay local unless a future architecture decision says
otherwise.

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

## GitHub And Git

Use Git/GitHub for:

- committing intentional local slices;
- preserving history and backup;
- code review and CI feedback;
- release publishing later.

Do not use GitHub as:

- the source of live launcher/runtime state;
- storage for local profiles, reports, SQLite databases, logs or browser data;
- a reason to design features around remote execution before the local program
  is stable.

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

## MarkItDown

MarkItDown is a local artifact-to-Markdown conversion tool for audit, support
and assistant context work.

Use it for:

- converting explicit local `.xlsx`, `.docx`, `.pptx`, `.pdf`, HTML or text
  artifacts into Markdown before review;
- preparing compact context from reports, audits or design/reference documents;
- creating local Markdown copies under `data/converted_markdown/` through
  `scripts/convert_artifact_to_markdown.py`.

Do not use it for:

- launcher/runtime parsing;
- automatic conversion of `.env`, proxy credentials, cookies, tokens, browser
  profiles, SQLite databases, GeoIP databases, build output or secrets;
- broad recursive scans over `data/`, `logs/` or the whole workspace;
- a persistent MCP/server with unrestricted file or URL access.

Preferred workflow:

1. choose one explicit file;
2. run `scripts/convert_artifact_to_markdown.py`;
3. inspect the generated Markdown before using it as assistant context;
4. keep generated Markdown local unless it is intentionally promoted to docs.

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

## Local Agent OS

Local Agent OS is ParserRIba-owned developer tooling for complex agent work.
It writes local Markdown ISA notes under ignored `agent-os/WORK/` and may
optionally mirror safe notes into a local Obsidian vault.

Use it for:

- preserving current state, ideal state and criteria before risky edits;
- recording bounded RLM decomposition steps;
- keeping decisions and verification evidence attached to a task;
- optional local Obsidian knowledge-base continuity.

Do not use it for:

- ParserRIba runtime behavior;
- browser automation or captcha solving;
- cloud memory, hosted LLMs or paid services;
- storing secrets, proxy credentials, cookies or API keys.

## Codex RLM Sidecar

The upstream `alexzhang13/rlm` repository may be used as Codex-only tooling
through `scripts/codex_rlm_sidecar.py` and the isolated
`tools/rlm-runtime/.venv` environment. Optional upstream extras for IPython,
Modal, E2B, Daytona and Prime are installed there for Codex use, but cloud
environments remain disabled by policy until explicitly approved for a run.

Use it for:

- bounded RLM experiments during agent planning or research;
- local endpoint-first model calls through an OpenAI-compatible localhost URL;
- upstream trajectory logs and visualizer inspection;
- preserving agent decisions under ignored `agent-os/`.

Do not use it for:

- ParserRIba product runtime;
- launcher/store/core imports;
- hidden hosted LLM calls;
- cloud sandboxes without explicit approval;
- storing prompts or config that contain secrets.

`scripts/architecture_check.py` blocks direct `rlm` and `rlms` imports from
runtime roots.

`scripts/codex_rlm_mcp.py` is a local stdio MCP wrapper for Codex-facing Agent
OS and sidecar controls. It may expose RLM status/config/dry-run tools, local
visualizer info, Agent OS note creation and structured RLM trajectory commands
to an MCP client, but it must stay developer tooling: no ParserRIba runtime
imports, no hidden hosted model calls, no unrestricted filesystem tools and no
external provider enablement by default.

## Decision Boundary

Before adding any external tool into the project flow, answer these questions:

1. Is it runtime, review, or automation only?
2. Does it reduce real project complexity, or add a new control plane?
3. Can the same task already be handled by local Python, git, tests, and docs?
4. Does it require paid services, cloud coupling, or hidden credentials?

If the answer is unclear, keep the tool out of runtime and treat it as optional
developer tooling only.
