# LifeOS n8n Automation Roadmap

> n8n is the LifeOS automation layer. It orchestrates workflows, not the
> source of truth. LifeOS APIs remain the authoritative boundary.

## Current State

- **n8n version:** Running via legacy Docker Compose (`40_Services/n8n/docker-compose.yml`)
- **Port:** `127.0.0.1:5678` (localhost-only, Basic Auth enabled)
- **Network:** `lifeos_internal` Docker network
- **Webhooks:** No public webhooks. Cloudflare Quick Tunnel POC completed and torn down.
- **Telegram:** Bot is systemd user service, not n8n. No Telegram webhook.
- **Workflows:** Status Digest workflow exists (Manual Trigger → HTTP Request → Status API). Inactive.
- **Unified compose:** n8n defined in `lifeos.yaml` with `manual-start-disabled` profile. Not active.
- **Adoption:** n8n migration from legacy compose to unified compose is deferred.

## Guiding Principles

1. **n8n remains local-only** — No public webhooks until explicit approval with security review.
2. **No direct vault mount** — n8n reads LifeOS data through APIs, not filesystem mounts.
3. **No Docker socket** — n8n does not control containers. Container health via Status API.
4. **Read-only Status Digest first** — The first active n8n workflow should be a read-only
   system status digest that polls the Status API and sends a summary to Telegram.
5. **n8n is automation layer, not source of truth** — LifeOS APIs (Status, Action, future
   Search API) define the system boundary. n8n orchestrates across them.
6. **LifeOS APIs remain the boundary** — No n8n node writes directly to vault, capture
   queue, event log, or git repo. All mutations go through Action API.

## Roadmap

### Phase 1: Foundation (Current — V1)

| Item | Status | Notes |
|------|--------|-------|
| n8n running local-only | Done | Legacy compose, localhost:5678 |
| Basic Auth enabled | Done | N8N_BASIC_AUTH_ACTIVE=true |
| No public webhooks | Done | Cloudflare POC torn down |
| Unified compose definition | Done | manual-start-disabled profile |
| Inert scaffold workflows | Done | Placeholder docs only |
| Status API reachable from n8n | Done | Via lifeos_internal network |
| Action API reachable from n8n | Done | Via lifeos_internal network |

### Phase 2: Read-Only Automations (V1-V2)

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **Status Digest workflow** | Scaffold exists | High | Manual Trigger → Status API → Telegram. First real workflow to activate. |
| **Service Health Digest** | Not started | High | Poll Status API + Docker health checks. Send Telegram if service down. |
| **Pending Capture Reminder** | Not started | Medium | Poll Status API pending_captures. Notify if >= 5 pending. |
| **Git Dirty-State Alert** | Not started | Low | Poll Git via API. Notify if dirty > 5 files for > 24hrs. |
| **Disk Usage Alert** | Not started | Medium | Poll disk via script or API. Notify if >= 90%. |

### Phase 3: Gated Mutations (V2-V3)

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| Capture creation via n8n | Not started | Medium | n8n → Action API. Requires Telegram webhook for inbound captures. |
| Approved capture processing | Not started | Low | n8n → Controlled File Processor. A3-gated. Requires explicit confirmation per batch. |
| Project scaffolding workflow | Not started | Low | n8n → Action API → create project structure. Requires approval tier. |
| Maintenance scheduling | Not started | Low | n8n → Semantic Janitor trigger. Read-only suggestions first. |

### Phase 4: MCP Integration (V3+)

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| MCP-enabled n8n access | Not started | Low | n8n → MCP server. Only via allowlisted MCP tools. No shell, no Docker socket. |
| n8n as MCP provider | Not started | Low | Expose workflow status/triggers as MCP tools. Read-only first. |
| Agent-triggered workflows | Not started | Low | AI agent → MCP → n8n workflow trigger. Approval-gated. |

## Explicitly Deferred/Rejected

| Item | Status | Reason |
|------|--------|--------|
| Public webhooks | Deferred | Requires Cloudflare domain setup + security review + Telegram webhook change |
| Direct vault writes from n8n | Rejected | Always through capture pipeline and controlled processor |
| n8n Execute Command nodes | Rejected (V1) | Shell execution risk. May be allowed for sandboxed nodes in V3 with A5 approval. |
| Docker container management from n8n | Rejected | n8n does not control other services. Use compose commands or Status API. |
| Git commit/push from n8n | Rejected | Git writes are always manual or agent-driven with approval. |
| n8n community nodes | Deferred | Supply-chain risk. Evaluate per-node with sandbox testing before installation. |
| n8n as Telegram webhook receiver | Deferred | Requires Cloudflare tunnel. Systemd polling bot is current path. |

## Activation Checklist

Before activating any n8n workflow in production:

- [ ] Workflow defined and reviewed (code or n8n export)
- [ ] All API calls are to `lifeos_internal` network or `localhost` only
- [ ] No Execute Command nodes
- [ ] No direct filesystem writes
- [ ] No Docker socket or shell access
- [ ] No secret or token logged in workflow output
- [ ] Retry and error handling configured
- [ ] Alert/notification for workflow failure
- [ ] Rollback documented (deactivate workflow, no data mutation to undo)
- [ ] Approval recorded in Current_Working_State.md

## Future Considerations

### n8n Adoption into Unified Compose

When n8n migrates from legacy compose to unified compose:
- Stop legacy n8n container gracefully
- Verify n8n data volume preservation
- Start unified n8n with same volume
- Verify workflows and credentials intact
- Remove `manual-start-disabled` profile
- Document migration event

### Cloudflare Tunnel for n8n Webhooks

When public webhooks are needed (Telegram webhook, external service callbacks):
- Requires Cloudflare domain setup
- Tunnel must be domain-based (not Quick Tunnel)
- Only `/webhook/` path exposed (not n8n UI root)
- Cloudflare Access or n8n Basic Auth on webhook endpoints
- Telegram polling bot stopped or reconfigured before webhook activation

### n8n as AI Pipeline Orchestrator

If n8n orchestrates AI processing pipelines:
- AI model calls go through LiteLLM (future) for provider abstraction
- AI output is always a proposal, never a direct write
- Approval gate before any mutation
- Event log entry for every AI pipeline execution
- No model API keys in n8n credentials — use environment variables
