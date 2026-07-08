# LifeOS mcpo Foundation — Scaffold

> Scaffold-only. mcpo is not running, not installed, not activated.
> This file defines the planning and safety boundaries before any mcpo deployment.

## What is mcpo?

[open-webui/mcpo](https://github.com/open-webui/mcpo) is an MCP-to-OpenAI proxy.
It connects MCP (Model Context Protocol) servers to OpenAI-compatible API
consumers — most notably Open WebUI. mcpo acts as a bridge, translating MCP tool
calls into OpenAI-compatible function-calling interfaces.

In simpler terms: mcpo lets Open WebUI (or any OpenAI-compatible chat UI) use
MCP tools as if they were built-in function-calling capabilities.

## How mcpo Differs from MCP

| Aspect | MCP | mcpo |
|--------|-----|------|
| **Protocol** | Model Context Protocol — client/server protocol for AI tool access | Proxy that translates MCP to OpenAI function-calling |
| **Role** | Defines tools, resources, prompts that AI agents can use | Bridges MCP servers to chat UIs (Open WebUI, etc.) |
| **Scope** | Any MCP-compatible client (Claude Desktop, OpenCode, etc.) | Specifically Open WebUI and OpenAI-compatible consumers |
| **Deployment** | MCP server per domain (git, filesystem, SQL, etc.) | Single mcpo instance connects to multiple MCP servers |

## Why LifeOS May Use mcpo

1. **Open WebUI integration** — When LifeOS deploys Open WebUI for local AI chat,
   mcpo can connect it to LifeOS MCP tools (status, git, captures) without
   building custom Open WebUI tool integrations.

2. **Centralized MCP routing** — A single mcpo gateway can expose multiple MCP
   servers behind one OpenAI-compatible endpoint, simplifying access control
   and audit logging for local AI tools.

3. **Separation of concerns** — MCP servers focus on tool implementation.
   mcpo focuses on protocol translation. LifeOS APIs remain the authoritative
   boundary for mutations.

## First Safe Test: Read-Only MCP Server Against a Tiny Sandbox Folder

The recommended first mcpo test for LifeOS:

1. **Create a sandbox folder:**
   ```bash
   mkdir -p /home/lifeos/40_Services/mcp/sandbox/test-data
   echo '{"test": "hello from mcpo sandbox"}' > /home/lifeos/40_Services/mcp/sandbox/test-data/readme.json
   ```

2. **Run a read-only MCP filesystem server** against only that sandbox folder:
   ```yaml
   # See docker-compose.example.yml
   ```

3. **Run mcpo** pointing at the sandbox MCP server, binding `127.0.0.1` only.

4. **Verify:** The only data accessible is `test-data/`. No vault, no captures,
   no secrets, no Docker socket, no SSH.

This proves the integration without exposing any LifeOS data.

## Why Full Vault Access Is Rejected in V1

- The Obsidian vault (`10_Vaults/LifeOS/`) contains personal notes, project
  context, AI mirror observations, identity patterns, decisions, and policies.
- MCP/mcpo is a new, unproven integration in this environment.
- Full vault read access through any MCP tool would bypass the capture-review-approve
  pipeline and expose sensitive content to any AI consumer connected to mcpo.
- Read-only vault access will be considered in a later phase after strict
  content sensitivity classification and allowlist-based path restrictions.

## Why Shell Execution Is Rejected in V1

- Shell execution MCP servers grant arbitrary command execution to AI.
- No shell MCP can be safely allowlisted — even with path restrictions, prompt
  injection can craft dangerous commands.
- Shell execution is permanently prohibited for MCP/mcpo in LifeOS.
- For administrative tasks, use n8n with explicit reviewed workflows, not MCP.

## How Future Open WebUI Integration May Work

```
Open WebUI (localhost:8080)
    ↕ OpenAI-compatible API
mcpo (localhost:PORT, localhost-only)
    ↕ MCP protocol
LifeOS MCP servers:
    ├── lifeos-status (read-only system status)
    ├── lifeos-git (read-only git status)
    ├── lifeos-captures (read-only capture queue)
    ├── filesystem-sandbox (read-only, sandbox folder only)
    └── ... (allowlisted tools only)
```

Open WebUI users could then ask AI assistants to:
- "Check LifeOS system status"
- "How many pending captures are in the queue?"
- "Is the git repo clean?"

All read-only. All localhost. All deny-by-default.

## How to Keep It localhost-Only

- mcpo container binds `127.0.0.1` only.
- MCP servers bind `127.0.0.1` only or communicate over the `lifeos_internal`
  Docker network without host port mappings.
- No Cloudflare tunnel, no Tailscale funnel, no reverse proxy for mcpo in V1.
- Access only from the local machine — SSH tunnel if remote access is needed.

## How to Remove/Rollback the Scaffold

Since mcpo is scaffold-only with no running containers:

```bash
# Remove mcpo files
rm -rf /home/lifeos/40_Services/mcpo/

# If containers were started:
docker-compose -f /home/lifeos/40_Services/mcpo/docker-compose.example.yml down -v

# Git cleanup (if committed)
git rm -r 40_Services/mcpo/
```

No Docker volumes, no service data, no persistent state to clean up.

## Exact Next Test Plan for mcpo Sandboxing

1. Create the sandbox test-data folder with one harmless JSON file.
2. Start a read-only filesystem MCP server against the sandbox folder.
3. Start mcpo pointing at that MCP server, `127.0.0.1` only.
4. Verify mcpo is reachable at its localhost port.
5. Verify the sandbox MCP server returns only the test file — no vault access.
6. Attempt to read a path outside the sandbox — confirm blocked.
7. Stop all containers.
8. Document results. If successful, this proves the mcpo+MCP integration pattern
   is viable for future LifeOS AI tools.
