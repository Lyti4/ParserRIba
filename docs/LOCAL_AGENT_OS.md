# ParserRIba Local Agent OS

Local Agent OS is the local working layer for complex agent tasks in
ParserRIba. It creates a persistent ISA note before risky work so the agent can
keep objective, context, decisions and verification evidence in one place.

It is developer tooling only. It is not a ParserRIba runtime component and it
does not change launcher, browser, store adapter, storage or report behavior.

## What It Borrows

From RLM:

- explicit context as the working variable;
- recursive decomposition with bounded depth and iteration;
- stop conditions when evidence is missing, guards fail or user direction is
  needed;
- trajectory notes for later handoff.

From Personal AI Infrastructure:

- ISA framing: current state, ideal state and acceptance criteria;
- local memory as Markdown;
- containment rules for secrets and local-only artifacts;
- optional migration into a user-owned knowledge base such as Obsidian.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\local_agent_os.py new `
  --title "Task title" `
  --objective "Concrete outcome"
```

The default output is:

```text
agent-os/WORK/<timestamp-slug>/ISA.md
```

`agent-os/` is ignored by git.

## Obsidian Mirror

Obsidian mirroring is opt-in:

```powershell
$env:PARSERRIBA_OBSIDIAN_VAULT = "C:\path\to\vault"
.\.venv\Scripts\python.exe scripts\local_agent_os.py new `
  --title "Task title" `
  --objective "Concrete outcome" `
  --mirror-obsidian
```

The mirror path is:

```text
<vault>/ParserRIba/Local Agent OS/<timestamp-slug>.md
```

Mirroring fails closed if the note contains secret-like tokens, passwords,
cookies, proxy credentials or API keys.

On Windows, `scripts/local_agent_os.py` also reads the saved user environment
value from `HKCU\Environment`. This keeps mirroring usable in the current Codex
process after the variable is created, even before a full terminal restart.

## Operating Rule

Use Local Agent OS for complex or long-running work where context loss is a real
risk. For small single-file fixes, use the normal workflow and guards.

## Structured RLM Trajectories

For tasks that need more than one RLM step, use the structured trajectory
commands. They keep machine-readable JSON and rendered Markdown under ignored
`agent-os/WORK/`, and can mirror safe Markdown to Obsidian.

Start:

```powershell
.\.venv\Scripts\python.exe scripts\local_agent_os.py rlm-start `
  --title "Task title" `
  --objective "Concrete outcome" `
  --mirror-obsidian
```

Append a step:

```powershell
.\.venv\Scripts\python.exe scripts\local_agent_os.py rlm-step `
  --trajectory "<trajectory_id>" `
  --context "Current evidence" `
  --question "Next question" `
  --result "Evidence-backed result" `
  --next-decision continue `
  --mirror-obsidian
```

Close:

```powershell
.\.venv\Scripts\python.exe scripts\local_agent_os.py rlm-close `
  --trajectory "<trajectory_id>" `
  --summary "What was learned" `
  --decision "Decision made" `
  --verification "Command or check" `
  --risk "Remaining risk" `
  --next-action "Next safe action" `
  --mirror-obsidian
```

The default implementation is manual and local. It does not install or depend
on the external `rlms` package, hosted LLMs or cloud sandboxes.

## Codex RLM Sidecar

Spec `015-codex-rlm-sidecar` adds an optional Codex-only sidecar for upstream
RLM tooling. It is not ParserRIba runtime.

Installed local pieces:

- upstream checkout: `C:\tmp\rlm-study`;
- isolated sidecar venv: `tools/rlm-runtime/.venv`;
- installed optional RLM extras: `ipython`, `modal`, `e2b`, `daytona`,
  `prime`;
- upstream visualizer dependencies: `C:\tmp\rlm-study\visualizer\node_modules`.

Check the sidecar:

```powershell
.\.venv\Scripts\python.exe scripts\codex_rlm_sidecar.py status
```

Create a secret-free local config under ignored `agent-os/RLM/`:

```powershell
.\.venv\Scripts\python.exe scripts\codex_rlm_sidecar.py init-config
```

Validate a local endpoint request without calling a model:

```powershell
.\.venv\Scripts\python.exe scripts\codex_rlm_sidecar.py run `
  --prompt "Summarize current evidence" `
  --model local-model `
  --dry-run
```

Default policy:

- `vllm`/OpenAI-compatible local endpoint first;
- localhost-compatible base URL required for local backend;
- external providers require `--allow-external-provider`;
- cloud environments are installed but require `--allow-cloud-environment`;
- secret-like prompts are rejected before sidecar execution;
- product runtime must not import `rlm` or `rlms`.

## Local MCP Wrapper

`scripts/codex_rlm_mcp.py` is the local stdio bridge for Agent OS and RLM
sidecar controls. It is dependency-free and exposes only local-safe tools:

- `rlm_status`
- `rlm_init_config`
- `rlm_dry_run`
- `rlm_visualizer_info`
- `agent_os_note`
- `rlm_trajectory_start`
- `rlm_trajectory_step`
- `rlm_trajectory_close`

Inspect tools:

```powershell
.\.venv\Scripts\python.exe scripts\codex_rlm_mcp.py --list-tools
```

Write a local MCP client config snippet under ignored `agent-os/MCP/`:

```powershell
.\.venv\Scripts\python.exe scripts\codex_rlm_mcp.py --write-client-config
```

Run stdio MCP mode:

```powershell
.\.venv\Scripts\python.exe scripts\codex_rlm_mcp.py --stdio
```

The wrapper can create Agent OS notes and RLM trajectories, including optional
Obsidian mirroring through the same `PARSERRIBA_OBSIDIAN_VAULT` setting. It
does not expose the current Codex chat model to Python code and does not enable
external model providers.
