# ParserRIba Agent Workflow

This document defines how an agent should work on ParserRIba and how the same
discipline can be reused in future projects. It is a process guide, not product
runtime code.

## Operating Rule

Work from current evidence:

1. Read `AGENTS.md`.
2. Read current project docs:
   `docs/PROJECT_STATE.md`, `docs/NEXT_STEPS.md`, `docs/DECISIONS.md`,
   `docs/TARGET_ARCHITECTURE.md` and `docs/PROJECT_STRUCTURE.md`.
3. Check `git status --short`.
4. Select the smallest relevant skill set.
5. Make one safe slice.
6. Run the guards that match the edited files.
7. Report what changed, what passed and what risk remains.

Do not rely on old chat memory when a current file can answer the question.

For the default lightweight agent guard set, run:

```powershell
.\.venv\Scripts\python.exe scripts\agent_ops_check.py --scope changed
```

For a stronger check of the guard layer itself, run:

```powershell
.\.venv\Scripts\python.exe scripts\agent_ops_check.py --scope changed --with-tests
```

When a stale-context or long-chat handoff is needed, create a note from
`docs/templates/HANDOFF_NOTE_TEMPLATE.md` and validate it:

```powershell
.\.venv\Scripts\python.exe scripts\agent_ops_check.py --scope changed --handoff-note path\to\handoff.md
```

## Tool Routing

Use spec-kit when the work changes product direction, architecture, UX scope,
storage shape, feature behavior or long-term workflow. A spec should define
requirements, non-goals, success criteria and the validation plan.

Use Superpowers when the work needs a disciplined method: brainstorming,
implementation planning, TDD, systematic debugging, subagent delegation,
review or verification.

Use ParserRIba local skills for project-specific rules: launcher workflow,
store-neutral migration, profile storage, Camoufox diagnostics, reporting,
filters, encoding, cleanup and release readiness.

Use `.agents/skills/parserriba-agent-ops-workflow/SKILL.md` as the project-local
entrypoint for this workflow. It exists so future chats can discover the process
from the repository instead of relying only on global Codex skills.

Use graphify for architecture evidence before large cleanup, dependency
migration, archive deletion or cross-module refactors.

Use subagents for read-only audits, impact analysis, independent verification
or parallel exploration. The orchestrator keeps final responsibility for edits
and validation.

## Local Agent OS

Use Local Agent OS when a task is complex enough that losing context would
create real risk. It creates a local ISA note with current state, ideal state,
acceptance criteria, RLM execution steps, decisions and verification evidence.

Create a note with:

```powershell
.\.venv\Scripts\python.exe scripts\local_agent_os.py new `
  --title "Task title" `
  --objective "Concrete outcome"
```

Optional Obsidian mirroring is local-only and opt-in:

```powershell
$env:PARSERRIBA_OBSIDIAN_VAULT = "C:\path\to\vault"
.\.venv\Scripts\python.exe scripts\local_agent_os.py new `
  --title "Task title" `
  --objective "Concrete outcome" `
  --mirror-obsidian
```

Local Agent OS is dev tooling. It does not replace spec-kit, Superpowers,
graphify, Serena or guard scripts, and it must not become ParserRIba runtime.
On Windows, the CLI can read `PARSERRIBA_OBSIDIAN_VAULT` from the saved user
environment when the current process has not inherited it yet.

For multi-step investigations, use structured RLM trajectories instead of only
editing free-form ISA text:

```powershell
.\.venv\Scripts\python.exe scripts\local_agent_os.py rlm-start `
  --title "Task title" `
  --objective "Concrete outcome" `
  --mirror-obsidian
```

Then record `rlm-step` entries with context, question, result and
stop/continue decision, and finish with `rlm-close` once verification evidence
or the blocking condition is known.

For Codex-only RLM execution through the upstream `rlms` package, use the
sidecar from spec `015-codex-rlm-sidecar`. The sidecar is developer tooling,
not ParserRIba runtime:

```powershell
.\.venv\Scripts\python.exe scripts\codex_rlm_sidecar.py status
.\.venv\Scripts\python.exe scripts\codex_rlm_sidecar.py run `
  --prompt "Summarize current evidence" `
  --model local-model `
  --dry-run
```

Real sidecar runs must start with a localhost-compatible OpenAI/vLLM endpoint.
External providers and cloud sandboxes require explicit approval flags and
should be recorded in an RLM trajectory before use.

For Codex tool integration without external keys, use the local MCP stdio
wrapper. It exposes sidecar status, config initialization, dry-run payload
validation, visualizer info, Agent OS note creation and structured RLM
trajectory commands. It does not expose the current ChatGPT/Codex session as a
model endpoint and it does not enable external providers:

```powershell
.\.venv\Scripts\python.exe scripts\codex_rlm_mcp.py --list-tools
.\.venv\Scripts\python.exe scripts\codex_rlm_mcp.py --write-client-config
.\.venv\Scripts\python.exe scripts\codex_rlm_mcp.py --stdio
```

## Guard-Backed Workflow

Skills are guidance. Guard scripts are enforcement.

| Risk | Required response |
| --- | --- |
| Cyrillic corruption, mojibake, BOM | Run `scripts/encoding_guard.py --changed` |
| Staged Cyrillic or encoding-sensitive commit | Run `scripts/encoding_guard.py --staged` |
| Architecture drift, forbidden APIs | Run `scripts/architecture_check.py` |
| Large file split or move | Use `parserriba-safe-file-split`, then focused tests |
| Launcher UI/UX change | Use `parserriba-launcher-visual-review`, then targeted launcher tests and launcher smoke |
| Browser/runtime change | Run targeted async tests and diagnostics before full gate |
| Spec-kit feature closeout | Use `parserriba-spec-closeout` and run `scripts/spec_closeout_check.py` |
| Stale context or long chat | Create and validate a handoff note |
| Multi-step RLM investigation | Use `scripts/local_agent_os.py rlm-start`, `rlm-step`, then `rlm-close` |

For important code slices, run the full ParserRIba validation gate from
`C:\tmp\ParserRIba-clean`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q models utils scripts tests stores launcher
.\.venv\Scripts\python.exe scripts\architecture_check.py
.\.venv\Scripts\python.exe scripts\run_desktop_launcher.py --smoke
```

Documentation-only slices may use focused guards when the scope is clearly not
runtime-affecting.

`scripts/agent_ops_check.py` is the default wrapper for documentation,
specification, skill-routing and guardrail slices. It does not replace the full
validation gate for runtime changes.

`scripts/spec_closeout_check.py` is the default closeout guard for spec-kit
features. It checks open tasks, required project docs, optional graphify output
and optional clean git state.

`scripts/launcher_visual_review.py` is the default visual guard for launcher UI
changes. It verifies stable launcher regions and writes light/dark screenshots
under ignored `logs/launcher_visual_review/`.

## Common Mistake Classes

Encoding mistakes:
Avoid shell rewrites for non-ASCII tracked files. Prefer `apply_patch` for
manual edits and run the encoding guard after docs, tests, specs or UI text
changes.

Before committing encoding-sensitive work, run:

```powershell
.\.venv\Scripts\python.exe scripts\encoding_guard.py --staged
.\.venv\Scripts\python.exe scripts\encoding_normalization_dry_run.py --changed
```

When PowerShell output may contain Russian text, do not trust terminal
rendering. Capture exact output with:

```powershell
.\.venv\Scripts\python.exe scripts\utf8_command.py -- <command>
```

For the full incident playbook, use `docs/ENCODING_INCIDENTS.md`.

Stale project context:
Read current docs first. If docs disagree, update the authoritative project
docs before continuing.

Over-broad refactors:
Use replacement discipline: define the new contract, switch active callers,
then remove or archive the old path only after evidence proves it is inactive.

Runtime shortcuts:
Do not add paid scraping, cloud browsers, captcha solving, hosted LLMs or
external paid APIs without explicit approval.

Codex RLM sidecar drift:
`rlms` may be installed in `tools/rlm-runtime/.venv`, but product runtime must
not import `rlm` or `rlms`. `scripts/architecture_check.py` enforces this for
`launcher/`, `utils/`, `stores/` and `models/`.

False completion:
Do not call work complete until current command output, tests, rendered UI or
file inspection proves the stated requirements.

## Future Project Template

For a new project, create these first:

- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- `docs/NEXT_STEPS.md`
- `docs/DECISIONS.md`
- `docs/TOOLS_POLICY.md`
- `docs/AGENT_WORKFLOW.md`
- `docs/templates/AGENT_OPS_STARTER.md`
- `docs/templates/HANDOFF_NOTE_TEMPLATE.md`
- project-specific skills under `.agents/skills/` or local Codex skills
- an agent workflow skill like `.agents/skills/parserriba-agent-ops-workflow/`
- `scripts/architecture_check.py` or equivalent
- one validation command that can prove the current slice

The template should stay local-first unless the user explicitly chooses a cloud
runtime or hosted service.

Use `docs/templates/AGENT_OPS_STARTER.md` as the copyable starter checklist for
future projects.
