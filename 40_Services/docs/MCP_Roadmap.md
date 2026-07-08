# LifeOS MCP Roadmap V1

> MCP = Model Context Protocol. LifeOS exposes a controlled MCP server for AI
> agents (OpenCode, Claude, etc.) to query system state without direct filesystem
> access, Docker socket, or shell execution.

## MCP Purpose in LifeOS

The MCP server is the **single controlled interface** between AI agents and
LifeOS system state. It replaces ad-hoc shell commands, direct filesystem reads,
and Docker socket access with a vetted, read-only-first tool allowlist.

Without MCP:
- Agents need Docker socket, git CLI, filesystem access
- No access control or audit trail
- Every agent gets the same (full) access as the user

With MCP:
- Agents query via typed tools with explicit capabilities
- Read-only by default, write behind approval gates
- Audit trail through MCP server logs
- No shell execution, no Docker socket, no direct vault writes

## Design Principles

### Read-Only First

All V1 tools are read-only. No tool modifies files, git state, Docker containers,
or vault content. This is non-negotiable for V1.

### Deny-by-Default

Every tool is explicitly allowed. Unknown tool requests are denied with a
standard error. No passthrough, no "try it and see," no wildcard tool names.

### Tool Allowlist

Only tools registered in the MCP server manifest are available. Adding a tool
requires explicit code change and review.

### No Shell Execution

No tool accepts or executes shell commands. No `subprocess.run`, no `os.system`,
no `eval`, no code execution of any kind.

### No Direct Vault Writes

No tool writes to `10_Vaults/` or any Obsidian path. Vault mutations require
human approval through the capture → review → approve → controlled processor
pipeline. MCP tools are not a shortcut around this pipeline.

### No Docker Socket

No tool accesses the Docker socket or Docker API. Container status is reported
through health endpoints, not Docker commands.

### No Secrets

No tool reads `.env` files, environment variables, or any secret-bearing paths.

## V1 Tools (Read-Only)

These tools are safe for any authorized AI agent to call. All are read-only.

### lifeos.status

**Purpose:** Return current system health and capture queue counts.

**Returns:** Same as `GET /status` on Status API: pending/approved/rejected/processed captures, event log summary, path status.

**Risk:** Low — read-only, no parameters.

### lifeos.git_status

**Purpose:** Check git dirty state and current commit.

**Returns:** Current branch, commit hash, dirty count, dirty file list (paths only, no diffs).

**Risk:** Low — read-only git porcelain, no diffs exposed.

### lifeos.current_state

**Purpose:** Return the Current_Working_State.md summary as structured data.

**Returns:** Active milestone, completed items count, known backlog count, last update timestamp.

**Risk:** Low — parses a known markdown file, no mutation.

### lifeos.list_projects

**Purpose:** List known LifeOS projects from vault directory.

**Returns:** Project names, paths, last modified timestamps.

**Risk:** Low — directory listing only, no file content.

### lifeos.pending_captures

**Purpose:** List pending review captures.

**Returns:** Capture IDs, titles, types, created timestamps (no full content).

**Risk:** Low — metadata only, no capture body.

### lifeos.generate_handoff_prompt

**Purpose:** Generate an OpenCode handoff prompt from current system state.

**Returns:** A structured prompt string containing repo root, git state, running services, and capture queue summary. No secrets, no vault content.

**Risk:** Low — aggregates read-only data already available to other tools.

## V2 Tools (Future, Read-Only)

### lifeos.search_vault

**Purpose:** Search Obsidian vault for notes matching a query.

**Returns:** File paths and titles, not full content. Content preview requires separate tool.

**Risk:** Medium — exposes vault structure and note titles. Content is sensitive.

**Gate:** Requires vault search policy and content sensitivity classification.

## V3 Tools (Future, Write-Gated)

### lifeos.create_capture

**Purpose:** Create a new capture via Action API.

**Returns:** Capture ID and status.

**Risk:** Medium — writes to capture queue and event log, but not vault.

**Gate:** Requires approval tier A3 or higher. No direct vault write.

### lifeos.submit_job

**Purpose:** Submit a job to the AI worker queue.

**Returns:** Job ID and status.

**Risk:** High — triggers AI agent execution.

**Gate:** Requires approval tier A4 or higher. Job must pass dry-run validation.

## Explicitly Out of Scope (V1 and V2)

| Request | Reason |
|---------|--------|
| Shell command execution | No shell, no code execution |
| Docker container management | No Docker socket |
| File read/write outside known paths | No general filesystem access |
| Environment variable access | No secrets |
| Git commit/push | No git writes |
| n8n workflow activation | No automation triggers |
| Cloudflare tunnel management | No network infrastructure |
| AI model invocation | No model calls from MCP |
| Direct vault writes | Always through capture pipeline |

## Architecture

```
AI Agent (OpenCode, Claude, etc.)
  ↓
MCP Server (Python stdlib, localhost only)
  ↓ (read-only)
  ├── Status API (localhost:8787) — capture counts, event log
  ├── Git (subprocess, read-only porcelain)
  ├── Filesystem (known paths only, read-only)
  └── Current_Working_State.md parser
```

The MCP server:
- Runs as a Docker container on `lifeos_internal` network
- Binds `127.0.0.1` only
- Has read-only mounts to `30_Capture/`, `50_Event_Log/`
- Does NOT mount `10_Vaults/` (vault search is V2, content is V3)
- Does NOT have Docker socket
- Does NOT have `.env` or secrets access
- Does NOT have write permission to any path

## Activation Checklist (Future)

- [ ] MCP server scaffold created (Python stdlib, localhost)
- [ ] Read-only tools implemented and tested
- [ ] Deny-by-default enforced in server
- [ ] Tool allowlist manifest created
- [ ] No shell execution path exists
- [ ] No secret access path exists
- [ ] No Docker socket mounted
- [ ] No vault write path exists
- [ ] MCP server added to unified compose with `experiments` profile
- [ ] Health check endpoint active
- [ ] OpenCode MCP client configured for localhost
- [ ] Manual dry-run test: agent queries status, verifies read-only
- [ ] Approval recorded in Current_Working_State.md

## Deferrals

- Vault search — requires content sensitivity policy
- Write tools — requires approval tier design
- AI worker job submission — requires worker activation
- n8n integration — requires n8n adoption into unified compose
- Cloudflare tunnel exposure — requires security review
