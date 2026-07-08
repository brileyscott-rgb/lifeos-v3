# LifeOS MCP Foundation

> Scaffold-only. No MCP servers running, no mcpo active, no production MCP tools.
> This document defines MCP policy, catalog, and planning for LifeOS V3.

## MCP Purpose in LifeOS

The Model Context Protocol (MCP) provides a controlled, typed interface for AI
agents to access LifeOS system state and perform approved actions. MCP replaces
ad-hoc shell commands, direct filesystem reads, and broad Docker socket access
with a vetted, read-only-first tool allowlist.

Without MCP:
- Agents need Docker socket, git CLI, or filesystem access
- No access control or audit trail
- Every agent gets the same (full) access

With MCP:
- Agents query via typed tools with explicit capabilities
- Read-only by default, writes behind approval gates
- Audit trail through MCP server logs
- No shell execution, no Docker socket, no direct vault writes

## Read-Only-First Policy

V1 is strictly read-only. No MCP tool may modify:
- Files on the host filesystem
- Git repository state (no commit, push, merge)
- Docker containers (no start, stop, restart, prune)
- The Obsidian vault (no note creation, no file edits)
- Event logs (read-only parsing only)
- Capture queue (read-only listing only)

The first write-capable MCP tools will be in V3, and only after:
- Allowlist-based tool registration
- Approval tier gating (A3 minimum, A4 for destructive)
- Audit logging with correlation IDs
- Sandbox testing before production

## Custom LifeOS MCP Server vs. Generic MCP Servers

### Generic MCP Servers

Public, community-maintained MCP servers from the MCP ecosystem:
- `@modelcontextprotocol/server-filesystem` — reads files from a directory
- `@modelcontextprotocol/server-git` — git status, diff, log
- `@modelcontextprotocol/server-fetch` — HTTP requests
- `@modelcontextprotocol/server-sqlite` — SQLite queries
- And many others (see catalog)

These are **candidates** to be sandbox-tested and allowlisted. They are not
production-ready for LifeOS without path restrictions, write restrictions,
and audit logging.

### Custom LifeOS MCP Server

A purpose-built MCP server exposing LifeOS-specific tools:
- `lifeos.status` — query Status API
- `lifeos.git_status` — read-only git porcelain
- `lifeos.current_state` — parse Current_Working_State.md
- `lifeos.list_projects` — list project directories
- `lifeos.pending_captures` — capture queue metadata

A custom server is the preferred production path because:
1. **No filesystem access granted** — tools call APIs, not filesystem ops
2. **Paath restrictions are inherent** — each tool has a bounded data scope
3. **Audit logging is built-in** — every tool call logs correlation ID, agent, result
4. **Allowlist is explicit** — no tool exists that wasn't purpose-built
5. **Secrets boundary is clear** — no tool touches `.env`, tokens, or keys

## How MCP Relates to LifeOS Components

| Component | MCP Relationship |
|-----------|-----------------|
| **OpenCode** | Primary MCP client. OpenCode agents use MCP tools to gather context and verify state without raw shell commands. |
| **ChatGPT/Claude Desktop** | External AI tools may connect to LifeOS MCP if explicitly approved. Not planned for V1. |
| **Open WebUI** | May connect via mcpo proxy to use LifeOS MCP tools. Sandbox-only in V1. |
| **n8n** | May trigger MCP tool calls through HTTP Request nodes (future). Or n8n may expose its own MCP server. Not in V1. |
| **Local models (Ollama)** | May use MCP tools through Open WebUI + mcpo. Read-only only. Not in V1. |

## Sandbox vs. Staging vs. Production MCP

| Stage | Folder | Mounts | Write | Who Can Use | Risk |
|-------|--------|--------|-------|-------------|------|
| **Sandbox** | `40_Services/mcp/sandbox/` | Isolated test-data folder only | No | Developer testing only | Minimal |
| **Staging** | `40_Services/mcp/` + isolated Docker network | Read-only mounts to copies of test data | No | Review before production | Low |
| **Production** | `40_Services/mcp/` + `lifeos_internal` network | Read-only mounts to real data paths | No (V1) / Gated (V3) | Approved agents only | Medium-High |

The rule: sandbox → staging → production for every new MCP tool. No tool skips
stages. Tools that pass staging still require production approval before activation.

## Activation Plan

1. Create MCP candidate catalog (done — see `catalog/MCP_Candidate_Catalog.md`).
2. Write MCP security policy (done — see `../docs/MCP_Security_Policy.md`).
3. Define tool allowlist for V1 custom LifeOS MCP server (future).
4. Implement V1 custom MCP server with read-only tools (future).
5. Sandbox-test each tool against isolated test data (future).
6. Promote to staging with read-only mounts to real data paths (future).
7. Security review and approval (future).
8. Activate in production with logging and monitoring (future).

No step is skipped. No tool is activated without sandbox-staging-production.
