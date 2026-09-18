# Agent Ops Starter Template

Use this template when starting a new local-first project that should benefit
from the ParserRIba agent workflow.

## Required Files

Create these files first:

- `AGENTS.md`
- `docs/PROJECT_STATE.md`
- `docs/NEXT_STEPS.md`
- `docs/DECISIONS.md`
- `docs/TOOLS_POLICY.md`
- `docs/AGENT_WORKFLOW.md`
- `docs/templates/HANDOFF_NOTE_TEMPLATE.md`
- `.agents/skills/<project>-agent-ops-workflow/SKILL.md`
- `scripts/architecture_check.py`
- one lightweight workflow guard command

## AGENTS.md Minimum Content

Include:

- authoritative workspace path;
- active runtime source;
- project architecture;
- current product path;
- hard constraints;
- forbidden services and artifacts;
- validation commands;
- first-read document list;
- rule to use `docs/AGENT_WORKFLOW.md`.

## Workflow Guard Minimum

The guard should check the project-specific repeated-error classes. Examples:

- encoding and BOM corruption;
- forbidden runtime APIs;
- tracked secrets or runtime artifacts;
- oversized files;
- stale generated files;
- architecture boundary violations.

The guard must be runnable locally and should have unit tests that inject fake
command runners instead of depending on live subprocesses.

## Skill Routing Minimum

The project-local skill should route to:

- project docs;
- feature/spec workflow;
- debugging method;
- guard command;
- handoff process;
- project-specific skills.

Avoid duplicating long docs inside the skill. The skill should point to the
authoritative documents and commands.

## Handoff Minimum

When context gets large:

1. update current project docs;
2. run the lightweight guard;
3. commit a safe slice when appropriate;
4. write a paste-ready prompt with workspace path, first-read docs, current
   branch, active plan, validation state and open risks;
5. validate it with the local workflow guard.
