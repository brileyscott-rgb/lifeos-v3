# LifeOS OpenHands Sandbox Policy

> This policy governs OpenHands deployment and usage in LifeOS V3.
> OpenHands is a sandbox, not a production tool. All output requires review.

## Operating Model

OpenHands runs as a **sandboxed agent lab**. It may:
- Generate code in isolated workspaces
- Test unknown GitHub repositories
- Install and evaluate dependencies
- Prototype MCP servers, APIs, and UIs
- Run learning experiments and tutorials

OpenHands may **not**:
- Edit LifeOS production files
- Access the Obsidian vault
- Read or write real secrets
- Commit to production repos
- Push to remote Git repositories
- Access the Docker socket in write mode
- Execute commands on the host

## Mount Policy

### Allowed: 60_Sandboxes/OpenHands/workspaces/

The only host path mounted into OpenHands is `/home/lifeos/60_Sandboxes/OpenHands/workspaces/`.
This is the sandbox boundary. All code generation, repo cloning, and file
creation must stay within this path.

### Prohibited Mounts

| Path | Risk if Mounted |
|------|----------------|
| `/home/lifeos` | Full LifeOS directory access |
| `/home/lifeos/10_Vaults/` | Personal knowledge, identity data, decisions, policies |
| `/home/lifeos/30_Capture/` | Capture queue data and pending reviews |
| `/home/lifeos/50_Event_Log/` | System event log |
| `/home/lifeos/40_Services/` | Production service configs and source |
| `/home/lifeos/.ssh/` | Private SSH keys |
| `/home/lifeos/.config/` | User config (OpenCode, etc.) |
| Any `.env` file | Real secrets and tokens |

### Docker Socket (Read-Only, Required)

OpenHands requires Docker socket access (`/var/run/docker.sock:ro`) to create
sandbox containers for code execution. This is a **controlled risk**:

- **Read-only socket** — OpenHands can create and manage containers but cannot
  directly access host filesystem through the socket in write mode.
- **Sandbox isolation** — The containers OpenHands creates have no access to
  LifeOS data paths. Their workspace is the OpenHands workspace directory only.
- **No socket passthrough** — OpenHands sandbox containers do not receive
  Docker socket access themselves.
- **Mitigation:** `no-new-privileges:true`, no host network mode, no pid mode.

**This is the only Docker socket mount in LifeOS.** It is confined to OpenHands
and its sandbox containers only. No other LifeOS service receives Docker socket.

## Network Policy

- OpenHands web UI binds `127.0.0.1:3003` only.
- No public exposure, no Cloudflare tunnel, no reverse proxy.
- Outbound internet access is allowed for package installs and git clone.
  The sandbox container provides isolation.

## Output Policy

All OpenHands output must be exported before review:

1. **Patches:** `git diff` or `git format-patch` from the workspace.
2. **Reports:** Markdown documents summarizing findings.
3. **Artifacts:** Generated files, configs, scripts.

Exports go to `60_Sandboxes/OpenHands/exports/<experiment>/`.

## Review Gate

Before any OpenHands output enters LifeOS production:

1. Export the output as a patch/report/artifact.
2. Review with a human or OpenCode (OpenCode may review but is not the OpenHands agent).
3. Apply changes with OpenCode, not OpenHands.
4. Run tests in the production context.
5. Commit and push through normal Git workflow.

No OpenHands agent may commit, push, or apply changes to LifeOS production.

## Secrets Policy

- No real API keys, tokens, or credentials in OpenHands environment variables.
- Use placeholder strings or example values for config files.
- If an API key is needed for a specific experiment (e.g., testing an MCP server
  that calls a cloud API), it must be scoped, time-limited, and manually entered.
- No LifeOS secrets (Telegram token, n8n credentials, GitHub SSH key) may ever
  be passed to OpenHands.

## Decommissioning

When an experiment is complete:

1. Export all valuable output to `exports/`.
2. Stop and remove OpenHands containers.
3. Delete the workspace directory if no longer needed.
4. Remove the Docker volume `openhands_state` if no persistent state is needed.

OpenHands is designed to be disposable. No OpenHands state is critical to LifeOS.
