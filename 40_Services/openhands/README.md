# LifeOS OpenHands Sandbox Plan

> Scaffold-only. OpenHands is not installed, not running, not activated.
> This document defines the sandbox policy and safe-use boundaries.

## Purpose

OpenHands (formerly OpenDevin) is an AI-powered software engineering agent
platform. In LifeOS, OpenHands serves as a **sandboxed agent lab** — not as
the main LifeOS executor.

## Why OpenHands Is Useful

1. **Code generation in isolation** — Test AI-generated code without risking
   production repos or system configs.
2. **Dependency experiments** — Install and test Python/Node packages, libraries,
   and tools without polluting the host environment.
3. **Unknown repo testing** — Clone and evaluate GitHub repos in a containerized
   sandbox before deciding to integrate them into LifeOS.
4. **MCP server prototyping** — Build and test new MCP servers before promoting
   them to the LifeOS MCP catalog.
5. **Dashboard/frontend prototyping** — Test UI mockups and dashboard layouts
   without affecting running services.
6. **Learning and evaluation** — Use OpenHands to understand how autonomous
   coding agents work without giving them production access.

## Why OpenHands Is Not the Main LifeOS Orchestrator

1. **LifeOS has OpenCode** — OpenCode is the primary development agent for
   LifeOS, with explicit approval tiers and path restrictions. OpenHands
   lacks LifeOS-specific policy integration.
2. **Vault isolation** — OpenHands must never touch the Obsidian vault or
   production config files. LifeOS knowledge is curated through the capture
   pipeline, not AI code agents.
3. **No production commit access** — OpenHands output must be exported as
   patches, reports, or artifacts, then reviewed by a human or OpenCode
   before entering production LifeOS.
4. **Audit boundary** — OpenHands runs in a container with no access to
   LifeOS data paths. Its actions are not logged in the LifeOS event log.
   Without audit, it cannot be a trusted orchestrator.

## Safe Use Cases (Allowed)

| Use Case | Risk | Notes |
|----------|------|-------|
| Test unknown GitHub repos | Low | Clone into workspace, evaluate, export report |
| Prototype MCP servers | Low | Build in sandbox, export patch for review |
| Prototype Search API | Low | Build in sandbox, export patch for review |
| Prototype dashboard UI | Low | Build in sandbox, export patch for review |
| Test Python/Node dependencies | Low | Install in container, no host pollution |
| Generate code in isolation | Low | Write code in workspace, export for review |
| Evaluate package conflicts | Low | Test conflicting versions safely |
| Learning/tutorial projects | Low | Disposable workspaces for learning |

## Rejected V1 Use Cases

| Use Case | Reason |
|----------|--------|
| Direct LifeOS repo editing | No production path access |
| Direct vault writes | Vault is always through capture pipeline |
| Full vault mount | Vault contains sensitive personal data |
| Docker socket access | Socket = host compromise |
| Host shell access | Arbitrary command execution risk |
| Autonomous production commits | No git push or commit to LifeOS repos |
| Production secrets access | No .env files, tokens, or credentials |
| Public webhook exposure | No Cloudflare tunnel, no reverse proxy |
| n8n workflow editing | n8n is a separate controlled automation layer |
| Telegram bot modification | ChatOps bot is a separate controlled service |

## Folder Layout

```
40_Services/openhands/
├── README.md                    # This file
├── docker-compose.example.yml   # Example compose for sandbox-only deployment
├── config.example.toml          # Example OpenHands config (localhost-only)
└── Sandbox_Policy.md            # Detailed sandbox security policy

60_Sandboxes/OpenHands/
├── README.md                    # Sandbox workspace documentation
├── workspaces/                  # Isolated workspaces per experiment
│   ├── .gitkeep
│   └── <experiment-name>/
└── exports/                     # Patches, reports, artifacts for review
    └── .gitkeep
```

## Mount Policy

### Allowed Mounts

- `60_Sandboxes/OpenHands/workspaces/` — read-write, isolated per experiment
- Docker image layers and cache (inside container, not host)
- Named volumes for OpenHands internal state

### Prohibited Mounts

| Path | Reason |
|------|--------|
| `/home/lifeos` | Complete LifeOS directory — too broad |
| `/home/lifeos/10_Vaults/` | Personal knowledge and identity data |
| `/home/lifeos/.ssh/` | Private SSH keys |
| `/home/lifeos/.config/` | User configs, OpenCode config |
| `/home/lifeos/*/.env` | Real secrets and tokens |
| `/var/run/docker.sock` | Docker socket = host compromise |
| Any production repo | LifeOS source code |

### Network Policy

- OpenHands container binds `127.0.0.1` only.
- No public port exposure, no Cloudflare tunnel.
- Outbound internet access may be needed for package installs and git clone.
  This is acceptable because OpenHands runs disposable code in an isolated
  container — the risk is contained.

## Import/Export Process

Every OpenHands experiment follows this flow:

### Import (Setup)

1. Define the experiment purpose and expected output.
2. Create a workspace directory: `60_Sandboxes/OpenHands/workspaces/<experiment>/`
3. Copy any reference files or templates into the workspace (not vault data).
4. Start OpenHands with the workspace mounted.
5. Clone any target repos into the workspace.

### Export (Review)

1. Generate output in one of these formats:
   - **Patch file:** `git format-patch` or `diff` for code changes
   - **Report:** Markdown document describing findings
   - **Artifact:** Generated file, config template, or script
2. Save output to `60_Sandboxes/OpenHands/exports/<experiment>/`
3. Review the exported output with a human or OpenCode.
4. After review and approval, apply the changes to LifeOS production.
5. Archive or delete the workspace.

## Example Workflow: Prototype a New MCP Server

1. **Prototype in OpenHands:**
   ```bash
   # Start OpenHands with workspace mount
   WORKSPACE=/home/lifeos/60_Sandboxes/OpenHands/workspaces/mcp-prototype
   docker-compose -f 40_Services/openhands/docker-compose.example.yml up -d
   ```
   OpenHands builds the MCP server in the sandbox workspace.

2. **Export patch/report:**
   ```bash
   # Save diff as patch
   git diff > 60_Sandboxes/OpenHands/exports/mcp-prototype/mcp-server.patch
   # Write report
   echo "MCP server tested: ..." > 60_Sandboxes/OpenHands/exports/mcp-prototype/report.md
   ```

3. **Review in staging:**
   - Human or OpenCode reviews the patch and report.
   - Apply patch to a staging copy of the MCP catalog.
   - Run tests against staging.

4. **Apply with OpenCode only after tests:**
   - OpenCode applies the reviewed patch to production `40_Services/mcp/`.
   - Tests pass in production context.
   - Commit and push.

## Rollback/Removal Instructions

```bash
# Stop and remove OpenHands container
docker-compose -f /home/lifeos/40_Services/openhands/docker-compose.example.yml down -v

# Remove workspace data (if no valuable exports)
rm -rf /home/lifeos/60_Sandboxes/OpenHands/workspaces/<experiment>/

# Remove exported files (if no longer needed)
rm -rf /home/lifeos/60_Sandboxes/OpenHands/exports/<experiment>/
```

## Activation Gate

OpenHands requires explicit approval before first activation:
- [ ] Sandbox Policy reviewed and approved (see `Sandbox_Policy.md`)
- [ ] Docker compose validated with `docker-compose config`
- [ ] Mount policy verified: no vault, no home, no SSH, no Docker socket
- [ ] Port bound to `127.0.0.1` only
- [ ] Workspace directory created under `60_Sandboxes/OpenHands/`
- [ ] Rollback instructions tested (dry-run)
- [ ] First experiment defined with clear input/output boundaries

Do not activate OpenHands without completing this checklist.
