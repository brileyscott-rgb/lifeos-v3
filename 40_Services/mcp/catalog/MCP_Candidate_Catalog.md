# MCP Candidate Catalog

> Read-only catalog. No MCP servers installed, started, or activated.
> Each entry documents a candidate MCP server for LifeOS evaluation.

## Evaluation Criteria

Each candidate is assessed on:
- **Risk level:** Minimal / Low / Medium / High / Critical
- **V1 decision:** allow / sandbox / defer / reject
- **Data access level:** none / single-path / bounded-set / broad / system
- **Write capability:** none / append-only / bounded / broad
- **Network exposure:** none / localhost / internal-network / outbound / internet

## Candidate Catalog

---

### 1. modelcontextprotocol/servers (Official MCP Servers)

| Field | Value |
|-------|-------|
| **Name** | MCP Official Servers |
| **Repo/Source** | `https://github.com/modelcontextprotocol/servers` |
| **Purpose** | Reference implementations for MCP servers (filesystem, git, fetch, sqlite, postgres, brave-search, memory, puppeteer) |
| **Install method** | `npx -y @modelcontextprotocol/server-<name>` or `pip install mcp-server-<name>` |
| **Docker support** | Varies by server. Most use `npx` with Node or `uvx` with Python. |
| **Secrets required** | Some (Brave Search API key, GitHub token, Postgres credentials) |
| **Mounts required** | Filesystem: host path. Git: host repo path. |
| **Data access level** | Bounded-set (per server) |
| **Write capability** | Varies: filesystem (rw), git (rw), sqlite (rw), fetch (ro) |
| **Network exposure** | Typically localhost / stdio |
| **Risk level** | Medium (wide scope per server, write-capable by default) |
| **LifeOS use case** | Foundation server implementations. Sandbox-test each before LifeOS adoption. |
| **V1 decision** | **Sandbox** — evaluate individual servers in sandbox. None promoted to production in V1. |
| **Notes** | Most servers lack path restrictions equivalent to LifeOS boundaries. Custom LifeOS MCP server preferred for production. |

---

### 2. Filesystem MCP

| Field | Value |
|-------|-------|
| **Name** | `@modelcontextprotocol/server-filesystem` |
| **Repo/Source** | `https://github.com/modelcontextprotocol/servers` (official) |
| **Purpose** | Read/write files within a bounded directory |
| **Install method** | `npx -y @modelcontextprotocol/server-filesystem <allowed-directory>` |
| **Docker support** | Via Node.js container with path mount |
| **Secrets required** | None |
| **Mounts required** | Host path to allowed directory |
| **Data access level** | Bounded-set (single allowed directory) |
| **Write capability** | Broad — create, edit, delete files within allowed directory |
| **Network exposure** | localhost / stdio |
| **Risk level** | High — write-capable with no allowlist per operation |
| **LifeOS use case** | Sandbox-only for testing MCP protocol integration. Not for vault or production paths. |
| **V1 decision** | **Sandbox** — restrict to `40_Services/mcp/sandbox/test-data/` only. Never promote to production without write-gating. |
| **Notes** | If LifeOS needs a filesystem tool, restrict it to read-only on bounded paths. Write = rejected for V1. |

---

### 3. Git MCP

| Field | Value |
|-------|-------|
| **Name** | `@modelcontextprotocol/server-git` |
| **Repo/Source** | `https://github.com/modelcontextprotocol/servers` (official) |
| **Purpose** | Git repository operations: status, log, diff, branch, commit (optional) |
| **Install method** | `pip install mcp-server-git` |
| **Docker support** | Via Python container with repo mount |
| **Secrets required** | None (read-only). SSH key needed for push (write). |
| **Mounts required** | Host path to git repo |
| **Data access level** | Bounded-set (single git repo) |
| **Write capability** | Bounded — commit, branch if enabled |
| **Network exposure** | localhost / stdio |
| **Risk level** | Medium — read-only log/status/diff is safe; commit/push is high risk |
| **LifeOS use case** | Read-only git status for agent context. Read-only only in V1. |
| **V1 decision** | **Sandbox** — read-only on a test repo. Write rejected for V1. Custom `lifeos.git_status` tool is preferred for production (no git binary exposure). |
| **Notes** | Read-only git status is already available via `lifeos_services.py` and custom MCP tool. Prefer LifeOS custom tool for production. |

---

### 4. Fetch/Web MCP

| Field | Value |
|-------|-------|
| **Name** | `@modelcontextprotocol/server-fetch` |
| **Repo/Source** | `https://github.com/modelcontextprotocol/servers` (official) |
| **Purpose** | Fetch web page content and convert to markdown |
| **Install method** | `uvx mcp-server-fetch` or `pip install mcp-server-fetch` |
| **Docker support** | Via Python container, needs outbound network |
| **Secrets required** | None (public web only). API keys if authenticated fetch needed. |
| **Mounts required** | None |
| **Data access level** | Outbound network — reads arbitrary URLs |
| **Network exposure** | Outbound internet |
| **Risk level** | Medium — web access can be used for exfiltration, SSRF, or malicious site fetching |
| **LifeOS use case** | Fetch documentation, GitHub READMEs, project references for agent context |
| **V1 decision** | **Sandbox** — restrict to allowlist of domains (github.com, docs.openwebui.com, etc.). Reject open internet fetch. |
| **Notes** | Domain allowlist is critical. Unbounded web fetch = data exfiltration risk. Consider fetch only through n8n HTTP Request nodes with domain restrictions instead. |

---

### 5. SQLite MCP

| Field | Value |
|-------|-------|
| **Name** | `@modelcontextprotocol/server-sqlite` |
| **Repo/Source** | `https://github.com/modelcontextprotocol/servers` (official) |
| **Purpose** | Query SQLite databases |
| **Install method** | `pip install mcp-server-sqlite` |
| **Docker support** | Via Python container with .db file mount |
| **Secrets required** | None (unless DB contains secrets) |
| **Mounts required** | Host path to .db file |
| **Data access level** | Bounded-set (single .db file) |
| **Write capability** | Broad — full SQL including INSERT, UPDATE, DELETE, DROP |
| **Network exposure** | localhost / stdio |
| **Risk level** | High — unrestricted SQL can drop tables, corrupt data, exfiltrate content |
| **LifeOS use case** | Query n8n database, event log (if moved to SQLite), LifeOS application state |
| **V1 decision** | **Defer** — no SQLite databases in LifeOS production yet. Re-evaluate when LifeOS has SQLite state stores. Must be read-only in first deployment. |
| **Notes** | Write-capable SQL = data corruption risk. Read-only mode (`-ro` flag) is minimum requirement. Custom LifeOS MCP tool wrapping specific queries is safer. |

---

### 6. Qdrant MCP

| Field | Value |
|-------|-------|
| **Name** | `qdrant/mcp-server-qdrant` |
| **Repo/Source** | `https://github.com/qdrant/mcp-server-qdrant` |
| **Purpose** | Query and manage Qdrant vector database collections |
| **Install method** | `pip install mcp-server-qdrant` |
| **Docker support** | Via Python container, needs network access to Qdrant |
| **Secrets required** | Qdrant API key (if auth enabled) |
| **Mounts required** | None |
| **Data access level** | Broad — full Qdrant collection access |
| **Write capability** | Broad — create, update, delete collections and points |
| **Network exposure** | Internal network (to Qdrant) |
| **Risk level** | Medium-High — vector DB contains embedded knowledge. Write-capable by default. |
| **LifeOS use case** | Semantic search over indexed vault content. Read-only search first. |
| **V1 decision** | **Defer** — Qdrant not deployed yet. Re-evaluate when Qdrant is active. Must be read-only search only in first deployment. |
| **Notes** | Qdrant access should go through a LifeOS Search API, not direct MCP. Semantic Janitor agent uses the API, not raw MCP. |

---

### 7. open-webui/mcpo

| Field | Value |
|-------|-------|
| **Name** | `open-webui/mcpo` |
| **Repo/Source** | `https://github.com/open-webui/mcpo` |
| **Purpose** | MCP-to-OpenAI proxy — connects MCP servers to OpenAI-compatible chat UIs |
| **Install method** | Docker image `ghcr.io/open-webui/mcpo:latest` |
| **Docker support** | Yes — official Docker image |
| **Secrets required** | None (unless upstream OpenAI API needs key) |
| **Mounts required** | None (connects to MCP servers over network) |
| **Data access level** | Proxy — inherits access level of connected MCP servers |
| **Write capability** | Proxy — inherits write capability of connected MCP servers |
| **Network exposure** | localhost (binds 127.0.0.1) |
| **Risk level** | Medium — proxy amplifies reach of connected MCP servers |
| **LifeOS use case** | Bridge between Open WebUI and LifeOS MCP tools for local AI chat |
| **V1 decision** | **Sandbox** — connect only to sandbox MCP servers. Scaffold created at `40_Services/mcpo/`. No production activation. |
| **Notes** | mcpo should only connect to allowlisted MCP servers. mcpo itself has no tool restrictions — the MCP servers it proxies must enforce access control. |

---

### 8. czlonkowski/n8n-mcp

| Field | Value |
|-------|-------|
| **Name** | `czlonkowski/n8n-mcp` |
| **Repo/Source** | `https://github.com/czlonkowski/n8n-mcp` |
| **Purpose** | MCP server exposing n8n workflows, executions, and triggers |
| **Install method** | `npx -y n8n-mcp` (Node.js) |
| **Docker support** | Via Node.js container, needs n8n API access |
| **Secrets required** | n8n API key |
| **Mounts required** | None |
| **Data access level** | Broad — full n8n API access |
| **Write capability** | Bounded — workflow activation, trigger management |
| **Network exposure** | Internal network (to n8n) |
| **Risk level** | High — can activate/deactivate workflows, read execution data and credentials |
| **LifeOS use case** | Agent-driven workflow status and management. Read-only status first, activation with approval. |
| **V1 decision** | **Defer** — requires n8n API key exposure. Prefer LifeOS custom MCP tool that calls n8n API with restricted scope. |
| **Notes** | n8n API key has broad access. Custom MCP tool that calls n8n API with a limited-scope endpoint proxy is safer. |

---

### 9. n8n Official MCP Access Path

| Field | Value |
|-------|-------|
| **Name** | n8n MCP Community Node / HTTP Request + Webhook |
| **Repo/Source** | n8n community nodes (search `n8n-nodes-mcp`) or native HTTP Request node |
| **Purpose** | n8n as MCP client (consuming MCP tools) or MCP server (exposing workflows) |
| **Install method** | Install community node in n8n, or use HTTP Request + Webhook nodes |
| **Docker support** | Native n8n Docker deployment |
| **Secrets required** | Varies by integration |
| **Mounts required** | None |
| **Data access level** | Varies |
| **Write capability** | Varies |
| **Network exposure** | Internal network |
| **Risk level** | Medium-High — community nodes may have supply-chain risk |
| **LifeOS use case** | n8n consumes MCP tools for workflow automation, or exposes workflows as MCP tools |
| **V1 decision** | **Defer** — no n8n community nodes installed in V1. Native HTTP Request + Webhook path preferred over community nodes. |
| **Notes** | LifeOS prefers n8n → API → Service over n8n → MCP → Service. The APIs (Status, Action) are the stable boundary. MCP is for AI agent access, not automation access. |

---

### 10. Playwright MCP

| Field | Value |
|-------|-------|
| **Name** | `@anthropic/mcp-server-puppeteer` or `@anthropic/mcp-server-playwright` |
| **Repo/Source** | Various community implementations referencing Anthropic's browser MCP |
| **Purpose** | Browser automation — navigate, screenshot, click, fill forms |
| **Install method** | `npx -y @anthropic/mcp-server-puppeteer` |
| **Docker support** | Requires browser binary (chromium) — heavy container |
| **Secrets required** | None (unless authenticated sites) |
| **Mounts required** | None |
| **Data access level** | Outbound — can browse any URL |
| **Write capability** | None (read-only browsing) / Broad (if form filling enabled) |
| **Network exposure** | Outbound internet |
| **Risk level** | **Critical** — browser automation can be used for SSRF, credential harvesting via fake login pages, exfiltration via URL parameters, and automated attacks |
| **LifeOS use case** | Web scraping for capture intake, documentation fetching, link previews |
| **V1 decision** | **Reject** — too high risk for V1. Web scraping should go through n8n HTTP Request nodes with domain restrictions, not full browser MCP. |
| **Notes** | If LifeOS needs browser automation, use n8n with controlled Puppeteer nodes, not MCP. MCP browser = agent can navigate anywhere. |

---

### 11. GitHub MCP

| Field | Value |
|-------|-------|
| **Name** | `@anthropic/mcp-server-github` or community variants |
| **Repo/Source** | Various implementations |
| **Purpose** | GitHub API access: repos, issues, PRs, commits, search |
| **Install method** | `npx -y @anthropic/mcp-server-github` |
| **Docker support** | Via Node.js container, needs GitHub token |
| **Secrets required** | GitHub personal access token |
| **Mounts required** | None |
| **Data access level** | Broad — all repos accessible to the token |
| **Write capability** | Bounded — create issues, PRs, comments (depending on token scope) |
| **Network exposure** | Outbound to GitHub API |
| **Risk level** | High — token scope may allow repo creation, PR merging, secret access |
| **LifeOS use case** | Agent-driven GitHub operations: create issues, review PRs, check repo status |
| **V1 decision** | **Defer** — requires GitHub token with scope management. Read-only GitHub status via lifeos_services.py is sufficient for V1. |
| **Notes** | If LifeOS needs GitHub MCP, use a fine-grained token with read-only access to specific repos. Write access requires A4 approval. |

---

### 12. Docker MCP Candidates

| Field | Value |
|-------|-------|
| **Name** | Various community Docker MCP implementations |
| **Repo/Source** | Community packages (`docker-mcp-server`, `mcp-server-docker`) |
| **Purpose** | Docker container management: list, start, stop, logs, exec |
| **Install method** | Varies (Python, Node.js). Requires Docker socket. |
| **Docker support** | Requires Docker socket mount |
| **Secrets required** | None (socket access = credential) |
| **Mounts required** | `/var/run/docker.sock` |
| **Data access level** | **System** — full Docker daemon access |
| **Write capability** | **System** — start/stop containers, exec commands |
| **Network exposure** | localhost / internal |
| **Risk level** | **Critical** — Docker socket access via MCP = root-level system access. Can escape container, read all volumes, execute arbitrary commands. |
| **LifeOS use case** | Container health checks, log access, service management |
| **V1 decision** | **Reject** — Docker socket MCP is permanently prohibited. Container status comes through Status API and health endpoints. Log access through Dozzle (read-only, localhost). Service management through explicit compose commands or n8n workflows. |
| **Notes** | Docker socket MCP is the single most dangerous MCP candidate. Full host compromise through container escape. Never add to LifeOS. |

---

### 13. Obsidian/Markdown MCP Candidates

| Field | Value |
|-------|-------|
| **Name** | Various community Markdown/note MCP servers |
| **Repo/Source** | Community packages (search `mcp-server-obsidian`, `mcp-server-markdown`) |
| **Purpose** | Read and write Obsidian vault notes, search vault, create/update notes |
| **Install method** | Varies. Typically `npx` or `pip` with vault path. |
| **Docker support** | Requires vault path mount |
| **Secrets required** | None |
| **Mounts required** | Full vault path (`10_Vaults/LifeOS/`) |
| **Data access level** | **Broad** — entire vault |
| **Write capability** | **Broad** — create, edit, delete vault notes |
| **Network exposure** | localhost |
| **Risk level** | **Critical** — vault contains personal notes, identity observations, decisions, policies, project context. Full vault access = total compromise of LifeOS knowledge layer. |
| **LifeOS use case** | Vault search for agent context, note creation through capture pipeline |
| **V1 decision** | **Reject** — full vault MCP is permanently prohibited. Vault access goes through the capture → review → approve pipeline, not direct MCP. |
| **Notes** | A limited vault-search MCP tool (read-only, path-bounded, title-only) may be considered in V2 after content sensitivity classification. This would be a custom LifeOS tool, not a generic Obsidian MCP. |

---

### 14. Browser/Search MCP Candidates

| Field | Value |
|-------|-------|
| **Name** | `@anthropic/mcp-server-brave-search`, community search MCP servers |
| **Repo/Source** | Various |
| **Purpose** | Web search via Brave Search API or other search engines |
| **Install method** | `npx -y @anthropic/mcp-server-brave-search` |
| **Docker support** | Via Node.js container, needs API key |
| **Secrets required** | Brave Search API key or equivalent |
| **Mounts required** | None |
| **Data access level** | Outbound — web search results |
| **Write capability** | None |
| **Network exposure** | Outbound internet |
| **Risk level** | Low-Medium — read-only search, but API key exposure risk |
| **LifeOS use case** | Agent-driven web search for research, context gathering |
| **V1 decision** | **Defer** — requires API key management. Search for agent context can be done via n8n workflows with controlled HTTP Request nodes. |
| **Notes** | If LifeOS adds web search MCP, use environment variables for API key (never in config files) and log all search queries for audit. |

---

### 15. Memory MCP Candidates

| Field | Value |
|-------|-------|
| **Name** | Various memory/context MCP servers |
| **Repo/Source** | Community packages (`@anthropic/mcp-server-memory`, `mcp-server-mem0`, etc.) |
| **Purpose** | Persistent memory/context storage for AI agents across sessions |
| **Install method** | Varies. `npx -y @anthropic/mcp-server-memory` |
| **Docker support** | Varies. May require SQLite/JSON file mount. |
| **Secrets required** | None (local). API key if cloud memory service. |
| **Mounts required** | Memory storage file path |
| **Data access level** | Bounded-set (single memory file) |
| **Write capability** | Broad — add, update, delete memory entries |
| **Network exposure** | localhost (local memory). Internet (cloud memory). |
| **Risk level** | Medium — memory persistence can accumulate stale/corrupted context. Write-capable by default. |
| **LifeOS use case** | Cross-session agent memory for context continuity |
| **V1 decision** | **Defer** — no AI agents running in V1 that need cross-session memory. LifeOS event log and Current_Working_State.md serve as structured memory for now. Re-evaluate when AI workers are active. |
| **Notes** | LifeOS memory strategy should use event log + vector search + structured state (SQLite), not ad-hoc MCP memory. Semantic memory should go through Qdrant Search API, not direct MCP. |

---

## V1 Decision Summary

| Candidate | V1 Decision | Reason |
|-----------|-------------|--------|
| Official MCP Servers (suite) | **Sandbox** | Evaluate individually, none promoted to production |
| Filesystem MCP | **Sandbox** | Restrict to sandbox folder only, read-only |
| Git MCP | **Sandbox** | Read-only on test repo. Prefer custom `lifeos.git_status` |
| Fetch/Web MCP | **Sandbox** | Domain allowlist required |
| SQLite MCP | **Defer** | No SQLite state yet. Read-only mode required later. |
| Qdrant MCP | **Defer** | Qdrant not deployed. Search API preferred over direct MCP. |
| open-webui/mcpo | **Sandbox** | Scaffold created. Connect to sandbox MCP only. |
| czlonkowski/n8n-mcp | **Defer** | Requires n8n API key. Custom LifeOS tool preferred. |
| n8n Official MCP Path | **Defer** | Prefer API boundary over MCP for automation. |
| Playwright MCP | **Reject** | Critical risk. Browser automation = system compromise. |
| GitHub MCP | **Defer** | Requires GitHub token. Read-only status script sufficient. |
| Docker MCP | **Reject** | Critical risk. Docker socket = host compromise. Permanently prohibited. |
| Obsidian/Markdown MCP | **Reject** | Critical risk. Full vault access. Permanently prohibited. |
| Browser/Search MCP | **Defer** | Requires API key management. |
| Memory MCP | **Defer** | Event log + structured state preferred over ad-hoc MCP memory. |

## Next Steps

1. Complete MCP Security Policy (`40_Services/docs/MCP_Security_Policy.md`).
2. Create MCP sandbox test-data folder with harmless content.
3. Sandbox-test filesystem MCP (read-only) against sandbox folder.
4. Implement custom LifeOS MCP server with V1 read-only tools.
5. No production MCP activation until sandbox → staging → production for each tool.
