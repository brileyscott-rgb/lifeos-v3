# LifeOS MCP Security Policy

> This policy governs all MCP (Model Context Protocol) tool deployment in LifeOS V3.
> No MCP server may be activated in production without meeting every requirement here.

## Core Principles

### Deny-by-Default

Every MCP tool is **denied by default**. No tool is available unless explicitly
registered in the tool allowlist. Unknown tool requests return a standard error.
No passthrough, no "try it and see," no wildcard tool names.

### Read-Only First

V1 tools are **read-only only**. No tool may modify files, git state, Docker
containers, vault content, event logs, or capture queues. The first write-capable
tools will be in V3 after full sandbox-staging-production gating.

### Localhost-Only

All MCP servers bind `127.0.0.1` only. No `0.0.0.0` binding. No Cloudflare tunnel,
Tailscale funnel, reverse proxy, or any public exposure path. Remote access
requires SSH tunneling with explicit approval.

## Prohibited MCP Capabilities (Permanent)

These MCP capabilities are **permanently prohibited** in LifeOS:

| Capability | Reason |
|-----------|--------|
| **Shell execution** | Arbitrary command execution = full system compromise. No shell MCP under any circumstances. |
| **Full vault filesystem mount** | Vault contains personal notes, identity data, decisions, policies. Always goes through capture pipeline. |
| **Docker socket access** | Docker socket = root-level system access. Container escape, volume access, host compromise. |
| **Direct vault writes** | All vault mutations go through capture → review → approve → controlled processor pipeline. MCP is never a shortcut. |
| **Secrets access** | No MCP tool reads `.env` files, environment variables, tokens, or keys. |
| **Git push/commit** | Git writes require A4 approval through explicit commands, never MCP. |

## Prohibited in V1 (Deferred)

| Capability | V1 Decision | Future Gate |
|-----------|-------------|-------------|
| **Write-capable filesystem** | Deferred | Path-bounded, approved destinations, read-write approval tier |
| **SQLite write** | Deferred | Read-only mode required first. Write after approval tier gating. |
| **Qdrant access** | Deferred | Qdrant not deployed. Read-only search via Search API preferred. |
| **n8n API access** | Deferred | Requires n8n API key scope management. Custom LifeOS tool preferred. |
| **GitHub API write** | Deferred | Fine-grained token required. Read-only in V2, write with A4 in V3. |
| **Web fetch (open internet)** | Deferred | Domain allowlist required. Unbounded fetch = exfiltration risk. |
| **Browser automation** | Rejected | Critical risk. May be reconsidered for read-only screenshots with strict domain binding. |
| **Memory persistence** | Deferred | Event log + structured state preferred. Re-evaluate with AI worker activation. |

## Tool Allowlist

Every MCP tool must be registered in the LifeOS MCP server before it is available.
The allowlist includes:

| Tool Name | V1 Status | Capability | Risk Level |
|-----------|-----------|------------|------------|
| `lifeos.status` | Planned | Read Status API | Low |
| `lifeos.git_status` | Planned | Read git state | Low |
| `lifeos.current_state` | Planned | Parse working state | Low |
| `lifeos.list_projects` | Planned | List project dirs | Low |
| `lifeos.pending_captures` | Planned | List captures metadata | Low |
| `lifeos.generate_handoff_prompt` | Planned | Aggregate context | Low |

Additional tools may be added after sandbox-staging-production gating and
explicit review.

## Resource Allowlist

MCP resources (file-like data accessible by URI) follow the same rules:

- Only registered resources are accessible.
- No wildcard URIs.
- No `file://` scheme for host paths.
- Resources are generated from API responses, not filesystem reads.

## Audit Log Requirement

Every MCP tool call must be logged with:
- `tool_name`
- `timestamp`
- `agent_id` (which AI agent/OpenCode agent called it)
- `parameters` (the arguments, sanitized to remove secrets)
- `result_summary` (success/error, record count, not full data)
- `correlation_id` (links to the parent agent task)
- `duration_ms`

Audit logs should be written to `50_Event_Log/mcp/` with the same JSONL format
as the main event log.

## Secrets: Never Committed

- MCP server config files must not contain real API keys, tokens, or credentials.
- Use environment variables with docker-compose `environment:` blocks.
- Config files committed to Git are `.example` templates only.
- Real config files are gitignored.

## Prompt Injection Risk

MCP tools receive parameters from AI agents, and AI agents receive prompts from
humans or other agents. Every MCP tool must assume parameters may be malicious:

- **Path traversal:** Reject `../` and absolute paths in any parameter.
- **Command injection:** Never pass tool parameters to `subprocess.run` or `os.system`.
- **SQL injection:** Use parameterized queries if SQL is ever added to MCP.
- **URL injection:** Validate URLs against domain allowlist.
- **Size limits:** Reject requests with excessive parameter sizes (> 16KB per param).
- **Rate limiting:** Per-agent rate limits to prevent abuse.

## Supply-Chain Risk

Third-party MCP servers from npm or PyPI are untrusted code:

- **Prefer custom LifeOS MCP tools** over community MCP servers.
- **Community MCP servers are sandbox-only** until reviewed.
- **Pin versions** — no `latest` tags for MCP images or packages.
- **Review dependencies** before installing any MCP server package.
- **No auto-updates** — MCP servers require explicit version bumps.

## Permissions/Mount Review Checklist

Before activating any MCP server, verify every item on this checklist:

- [ ] Ports bind `127.0.0.1` only (no `0.0.0.0`)
- [ ] No Docker socket mount (`/var/run/docker.sock`)
- [ ] No host home directory mount (`/home/lifeos` or `~`)
- [ ] No vault mount (`10_Vaults/`)
- [ ] No `~/.ssh` mount
- [ ] No `~/.config` mount
- [ ] No real `.env` files mounted
- [ ] No secrets in environment variables (check for tokens, keys)
- [ ] `read_only: true` if no write is required
- [ ] `cap_drop: ALL` if Docker deployment
- [ ] `no-new-privileges:true` if Docker deployment
- [ ] Named volumes only (no host path bind mounts for write paths)
- [ ] Health check configured
- [ ] Logging with size/rotation limits
- [ ] All allowed paths explicitly listed (no broad mounts)

## Rollback/Removal Requirements

Every MCP server must have a documented removal path:

```bash
# Stop containers
docker-compose -f <compose-file> down

# Remove volumes (if data is disposable)
docker-compose -f <compose-file> down -v

# Remove config files
rm -rf <mcp-server-path>

# Verify no orphaned containers
docker ps -a --filter "name=mcp"

# Verify no orphaned volumes
docker volume ls --filter "name=mcp"
```

## Review Requirements Before Adding Any New MCP Server

1. **Candidate evaluation:** Complete the candidate catalog entry (name, repo, purpose, risk, V1 decision).
2. **Sandbox test:** Test with isolated test data. Verify scope boundaries.
3. **Security review:** Complete the permissions/mount checklist above.
4. **Code review:** At least one reviewer inspects the MCP server configuration.
5. **Approval recorded:** Entry in Current_Working_State.md documenting the decision.
6. **Rollback documented:** Explicit removal instructions written.

No MCP server is added to production without completing every step above.

## Sandbox → Staging → Production Rule

Every new MCP tool follows this progression:

```
Sandbox (isolated test data, read-only, disposable)
  → Staging (read-only mounts to copies of real data)
    → Production (read-only mounts to real data paths, logging active)
```

No tool skips a stage. Each stage requires explicit approval before promotion.

## Deferrals

- Write-capable MCP tools — V3 minimum
- Vault search MCP — V2 minimum, after content sensitivity classification
- n8n MCP integration — after n8n adoption into unified compose
- External AI access to LifeOS MCP — after auth and rate-limiting are in place
- Remote MCP access — after Tailscale or SSH tunneling with auth
