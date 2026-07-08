# LifeOS MCP Catalog

> Grouped candidate evaluation catalog for LifeOS V3 MCP and external tool
> ecosystem. Combines the existing MCP Candidate Catalog (15 entries) with the
> new Repo Radar candidates (10 entries). All candidates are read-only evaluation
> until sandbox-staging-production gating is complete.
> Created: 2026-07-08

## Catalog Groups

Every candidate is assigned to one of five groups:

| Group | Criteria | Action |
|-------|----------|--------|
| **Approved for Sandbox Test** | Read-only or bounded write, localhost-only, no secrets, infrastructure exists | May run isolated sandbox test with explicit path restrictions |
| **Deferred** | Requires infrastructure not yet deployed, secrets not yet managed, or policy not yet written | Wait for prerequisites. Re-evaluate when infrastructure is ready. |
| **High-Risk Quarantine** | Write-capable, network exposure, secrets required, broad filesystem access | Requires explicit A4 approval + full security review before any test |
| **Discovery Indexes** | Reference lists, not tools themselves | Use for awareness. Never install based on list presence alone. |
| **Rejected for Now** | Critical risk, permanently prohibited, or infrastructure mismatch | Do not re-evaluate without major architectural change |

---

## Group 1: Approved for Sandbox Test

Sandbox = isolated test-data folder only. Read-only. No vault, no secrets, no Docker socket.

### 1. @modelcontextprotocol/server-time (Sandbox Tested 2026-07-08)

| Field | Value |
|-------|-------|
| **Source** | Official MCP Servers (`modelcontextprotocol/servers`) |
| **Category** | mcp-server |
| **Risk Tier** | **A0** — fully read-only, no filesystem, no network, no deps |
| **Sandbox Status** | **Tested (Mode A stdio smoke test)** — see `40_Services/mcp/sandbox/time-test/results.md` |
| **Why Sandbox** | The single safest MCP server. Zero risk. Proves MCP client/server integration without any data exposure. |
| **Sandbox Test** | `npx -y @guanxiong/mcp-server-time` (community npm package) via stdio JSON-RPC. Official `@modelcontextprotocol/server-time` npm package does not exist. Official Python `mcp-server-time` requires uvx (not installed). Tool list and tool call verified via piped JSON-RPC. |
| **Production Path** | Never — use only to validate MCP protocol integration. Not needed in production. |
| **Notes** | MCP protocol confirmed working on this system. Next: custom LifeOS MCP server with API-backed tools. |

### 2. @modelcontextprotocol/server-fetch (Domain-Allowlisted)

| Field | Value |
|-------|-------|
| **Source** | Official MCP Servers (`modelcontextprotocol/servers`) |
| **Category** | mcp-server |
| **Risk Tier** | **A1** — read-only web fetch with domain allowlist |
| **Why Sandbox** | Useful for fetching documentation, READMEs, project references. Domain allowlist mitigates exfiltration risk. |
| **Sandbox Test** | Restrict to `github.com`, `docs.openwebui.com`, `modelcontextprotocol.io`. Test fetch of known-safe pages. Verify blocked domains return error. |
| **Production Path** | V2+ — custom LifeOS fetch tool with more restrictive domain allowlist and URL validation. |
| **Notes** | Unbounded web fetch = data exfiltration risk. Domain allowlist is critical. Consider n8n HTTP Request nodes instead — n8n has built-in domain restrictions. |

### 3. open-webui/mcpo (Connected to Sandbox MCP Only)

| Field | Value |
|-------|-------|
| **Source** | `open-webui/mcpo` |
| **Category** | proxy |
| **Risk Tier** | **A2** — privilege amplifier, inherits risk of proxied MCP servers |
| **Why Sandbox** | Scaffold exists at `40_Services/mcpo/`. Safe first-test plan documented. Validates MCP proxy pattern. |
| **Sandbox Test** | Start mcpo with sandbox MCP servers (time + filesystem-sandbox). `--api-key` required. `deny_by_default: true`. Verify only allowlisted tools available. |
| **Production Path** | V2+ — after Open WebUI deployed. Requires: MCP servers deployed, API key mandatory, hot-reload off, config reviewed. |
| **Notes** | mcpo has no tool-level access control — proxied MCP servers must enforce their own boundaries. Config hot-reload could load new MCP servers at runtime. |

### 4. @modelcontextprotocol/server-filesystem (Sandbox Folder Only, Read-Only)

| Field | Value |
|-------|-------|
| **Source** | Official MCP Servers (`modelcontextprotocol/servers`) |
| **Category** | mcp-server |
| **Risk Tier** | **A3** — write-capable by default. Restricted to read-only on sandbox folder. |
| **Why Sandbox** | Validates filesystem MCP integration pattern. Path-bounded to `40_Services/mcp/sandbox/test-data/` only. |
| **Sandbox Test** | Run against sandbox test-data folder. Verify only test file accessible. Attempt read outside sandbox — confirm blocked. Filesystem permissions should be read-only. |
| **Production Path** | **Never** — custom LifeOS MCP tools preferred for production. API-backed tools avoid filesystem access entirely. |
| **Notes** | No per-operation allowlist — only path-based. Write operations exist by default. Production replacement: `lifeos.status`, `lifeos.git_status`, etc. |

---

## Group 2: Deferred

Infrastructure or policy prerequisites not met. Wait.

### 5. github/github-mcp-server

| Field | Value |
|-------|-------|
| **Source** | `github/github-mcp-server` |
| **Category** | mcp-server |
| **Risk Tier** | **A4** — PAT required, read-only still exposes private repos, write tools exist |
| **Why Deferred** | Requires GitHub PAT with documented scope policy, token management, and A4 approval for token creation. No AI agents to drive GitHub operations in V1. |
| **Prerequisites** | PAT scope policy, fine-grained token with minimal scope, test repo (not LifeOS), explicit A4 approval. |
| **Re-evaluate When** | AI agents need programmatic GitHub access (V3+). Custom `lifeos.git_status` tool is planned for V1. |
| **Notes** | `lifeos_services.py` already reports git status. Existing scripts serve V1 needs. Remote vs local server modes have different risk profiles. |

### 6. czlonkowski/n8n-mcp

| Field | Value |
|-------|-------|
| **Source** | Existing candidate catalog entry #8 |
| **Category** | mcp-server |
| **Risk Tier** | **A4** — requires n8n API key, can activate/deactivate workflows |
| **Why Deferred** | n8n API key has broad access. Custom LifeOS tool calling n8n API with restricted scope is preferred. n8n not yet adopted under unified compose. |
| **Prerequisites** | n8n adoption into unified compose, API key scope management policy, n8n API endpoint proxy with restricted scope. |
| **Re-evaluate When** | n8n is unified- compose-owned and API key scoping is implemented. |

### 7. n8n Official MCP Path

| Field | Value |
|-------|-------|
| **Source** | Existing candidate catalog entry #9 |
| **Category** | mcp-server (n8n as MCP consumer or server) |
| **Risk Tier** | **A3-A4** — community nodes carry supply-chain risk, API key required |
| **Why Deferred** | LifeOS prefers n8n → API → Service over n8n → MCP → Service. The APIs (Status, Action) are the stable boundary. No community nodes installed. |
| **Prerequisites** | n8n adoption into unified compose, HTTP Request + Webhook node pattern validated. |
| **Re-evaluate When** | After n8n internal workflow design (next step #10). |

### 8. @modelcontextprotocol/server-sqlite

| Field | Value |
|-------|-------|
| **Source** | Existing candidate catalog entry #5 |
| **Category** | mcp-server |
| **Risk Tier** | **A4** — unrestricted SQL including DROP, DELETE |
| **Why Deferred** | No SQLite databases in LifeOS production yet. Write-capable SQL = data corruption risk. Read-only mode required for first deployment. |
| **Prerequisites** | SQLite state stores in LifeOS, read-only mode (`-ro` flag) verified, parameterized queries enforced. |
| **Re-evaluate When** | LifeOS has SQLite state stores (V2+). Custom LifeOS MCP tool wrapping specific queries is preferred. |

### 9. Search/Brave Search MCP

| Field | Value |
|-------|-------|
| **Source** | Existing candidate catalog entry #14 |
| **Category** | mcp-server |
| **Risk Tier** | **A2** — read-only search, API key required |
| **Why Deferred** | Requires Brave Search API key management. Search for agent context can be done via n8n HTTP Request nodes. |
| **Prerequisites** | API key management policy, audit logging for search queries. |
| **Re-evaluate When** | API key management is standardized across LifeOS. |

### 10. Memory MCP Servers

| Field | Value |
|-------|-------|
| **Source** | Existing candidate catalog entry #15 |
| **Category** | mcp-server |
| **Risk Tier** | **A3** — persistent write to disk, memory corruption risk |
| **Why Deferred** | No AI agents running in V1. Event log + Current_Working_State.md serve as structured memory. LifeOS memory strategy: event log + vector search + SQLite, not ad-hoc MCP memory. |
| **Prerequisites** | AI workers active (V3+), memory strategy finalized, structured state stores (SQLite) deployed. |
| **Re-evaluate When** | AI workers are active and need cross-session memory. |

### 11. OpenHands/openhands

| Field | Value |
|-------|-------|
| **Source** | `OpenHands/openhands` (Repo Radar candidate #7) |
| **Category** | agent-platform (NOT an MCP server — reclassified) |
| **Risk Tier** | **A5-equivalent** — code execution, container spawning, filesystem access, cloud backends |
| **Why Deferred** | Docker socket requirement conflicts with LifeOS permanent prohibition. LLM API key required. Every LifeOS constraint (bounded mounts, export pipeline, A4 approval) is aspirational — none implemented. |
| **Prerequisites** | Docker socket policy resolution, LLM API key management, artifact review pipeline implementation, sandbox mount restriction verification. |
| **Re-evaluate When** | AI Agent Infrastructure policy exists. Docker socket policy resolved. |
| **Notes** | Reclassified from MCP Radar to AI Agent Infrastructure. Scaffold exists at `40_Services/openhands/`. Do not activate. |

---

## Group 3: High-Risk Quarantine

Requires explicit A4 approval + full security review before any test.

### 12. @modelcontextprotocol/server-git

| Field | Value |
|-------|-------|
| **Source** | Existing candidate catalog entry #3 |
| **Category** | mcp-server |
| **Risk Tier** | **A4** — write-capable by default (commit, branch, push). Read-only status/diff/log is A1. |
| **Why Quarantine** | Write operations exist by default. Git push requires SSH key — MCP server would have access to keys. Custom `lifeos.git_status` tool preferred for production. |
| **Sandbox Conditions** | Read-only only (`--no-commit`). Test repo that IS NOT the LifeOS repo. No SSH keys mounted. |
| **Notes** | Read-only git porcelain already available via `lifeos_services.py`. Custom MCP tool exposes only status/diff/log, never write. |

### 13. Microsoft MarkItDown (as MCP Server)

| Field | Value |
|-------|-------|
| **Source** | `microsoft/markitdown` (Repo Radar candidate #6) |
| **Category** | library (reclassified as Capture Processor) |
| **Risk Tier** | **A4** as MCP server — file parsing attack surface, cloud backends, plugin execution |
| **Why Quarantine** | As an MCP tool, AI agents could submit any file for conversion — including files they shouldn't access. Cloud backends (Azure, OpenAI) exfiltrate data. Plugins = arbitrary code. |
| **Notes** | **Reclassified.** Evaluate as Capture Processor (bounded Docker container with restricted mounts), not as MCP server. See Capture Processor Roadmap — Markdown Formatter processor. |

---

## Group 4: Discovery Indexes

Reference lists for ecosystem awareness. Never use as "recommended" or "vetted."

### 14. punkpeye/awesome-mcp-servers

| Field | Value |
|-------|-------|
| **Source** | `punkpeye/awesome-mcp-servers` (Repo Radar candidate #9) |
| **Category** | discovery-index |
| **Risk Tier** | **A0** (reference only). Usage risk: A3 — installing unvetted servers. |
| **Why Discovery** | Broad ecosystem awareness. Community-curated list of hundreds of MCP servers. |
| **Usage Rule** | NEVER install a server solely because it appears in this list. Always apply LifeOS evaluation framework. |
| **Notes** | 8,500+ commits, 2,400+ open PRs. Includes servers LifeOS has already rejected (browser automation, shell execution, Docker socket). No security review. Use for awareness only. |

### 15. tolkonepiu/best-of-mcp-servers

| Field | Value |
|-------|-------|
| **Source** | `tolkonepiu/best-of-mcp-servers` (Repo Radar candidate #10) |
| **Category** | discovery-index |
| **Risk Tier** | **A0** (reference only). Usage risk: A3 — quality scores measure GitHub popularity, not LifeOS safety. |
| **Why Discovery** | Structured YAML data (`projects.yaml`) enables programmatic filtering. More useful than awesome-mcp-servers for automated discovery. |
| **Usage Rule** | Use `projects.yaml` as discovery input. NEVER use the quality score for LifeOS decision-making. The #1 ranked server (Playwright MCP) is permanently rejected by LifeOS policy. |
| **Notes** | Quality score = GitHub stars + downloads + activity. Equating popularity with safety is dangerous. Build a LifeOS-specific scoring system. |

---

## Group 5: Rejected for Now

Critical risk, permanently prohibited, or infrastructure mismatch.

### 16. Playwright/Puppeteer MCP (Browser Automation)

| Field | Value |
|-------|-------|
| **Source** | `microsoft/playwright-mcp`, existing catalog entry #10 |
| **Category** | mcp-server |
| **Risk Tier** | **Critical** — RCE-equivalent, file system access, proxy, persistent sessions, CDP hijacking |
| **Why Rejected** | MCP Security Policy permanently prohibits browser automation. Microsoft's own docs: "Playwright MCP is NOT a security boundary." `browser_run_code_unsafe` is RCE-equivalent. `--allowed-origins` does not block redirects. |
| **Re-evaluate Never** | Permanently rejected. Do not re-evaluate. |

### 17. Docker MCP Servers

| Field | Value |
|-------|-------|
| **Source** | Existing candidate catalog entry #12 |
| **Category** | mcp-server |
| **Risk Tier** | **Critical** — Docker socket = root-level system access |
| **Why Rejected** | Docker socket MCP is permanently prohibited. Container escape, volume access, host compromise. Container status through Status API and health endpoints. Log access through Dozzle (read-only). Service management through explicit compose commands or n8n workflows. |
| **Re-evaluate Never** | Permanently rejected. Do not re-evaluate. |

### 18. Obsidian/Vault MCP Servers

| Field | Value |
|-------|-------|
| **Source** | Existing candidate catalog entry #13 |
| **Category** | mcp-server |
| **Risk Tier** | **Critical** — full vault access = total compromise of LifeOS knowledge layer |
| **Why Rejected** | Vault contains personal notes, identity observations, decisions, policies. Always goes through capture → review → approve → controlled processor pipeline. |
| **Re-evaluate When** | V2 minimum — limited vault-search MCP tool (read-only, path-bounded, title-only) after content sensitivity classification. Custom LifeOS tool only, never a generic Obsidian MCP. |

### 19. kubernetes-sigs/agent-sandbox

| Field | Value |
|-------|-------|
| **Source** | `kubernetes-sigs/agent-sandbox` (Repo Radar candidate #8) |
| **Category** | sandbox-infrastructure (reclassified — NOT an MCP server) |
| **Risk Tier** | **Cannot evaluate** — requires Kubernetes |
| **Why Rejected** | Requires Kubernetes cluster. LifeOS runs on Docker Compose. Kubernetes explicitly deferred. Deploying even a minimal test cluster (minikube/kind) would consume 2-4GB RAM and 20GB+ disk — unreasonable. |
| **Re-evaluate When** | LifeOS adopts Kubernetes (V4+ minimum). Remove from MCP Radar entirely. |

### 20. qdrant/mcp-server-qdrant

| Field | Value |
|-------|-------|
| **Source** | `qdrant/mcp-server-qdrant` (Repo Radar candidate #4, existing catalog entry #6) |
| **Category** | mcp-server |
| **Risk Tier** | **Cannot evaluate** — Qdrant not deployed. Write-by-default. Runtime model download. |
| **Why Rejected for V1** | Infrastructure doesn't exist. No Qdrant, no indices, no embedding pipeline. Runtime model download from Hugging Face = supply-chain risk. Write-capable by default (`QDRANT_READ_ONLY=false`). |
| **Re-evaluate When** | (1) Qdrant deployed and stable, (2) document indexing pipeline exists, (3) embedding model pre-downloaded and verified, (4) `QDRANT_READ_ONLY=true` verified as default, (5) disk usage allows. |
| **Notes** | Upgraded from existing catalog's "Defer" to "Rejected for V1" — infrastructure gap is too large for defer. |

---

## Catalog Summary

| Group | Count |
|-------|-------|
| **Approved for Sandbox Test** | 4 |
| **Deferred** | 7 |
| **High-Risk Quarantine** | 2 |
| **Discovery Indexes** | 2 |
| **Rejected for Now** | 5 |
| **Total** | 20 |

### Migration Notes from Existing Candidate Catalog

The existing `MCP_Candidate_Catalog.md` (15 entries) has been consolidated into this catalog. Changes:

| Original Entry | Old Decision | New Decision | Reason |
|---------------|-------------|-------------|--------|
| Official MCP Servers (suite) | Sandbox (blanket) | Sandbox (individual) | Each sub-server needs independent evaluation |
| Qdrant MCP | Defer | Rejected for V1 | Infrastructure gap too large — no Qdrant, no indices, no pipeline |
| GitHub MCP | Defer | Defer (unchanged) | PAT scope policy still needed |
| n8n-mcp (czlonkowski) | Defer | Defer (unchanged) | n8n not unified-compose-owned |
| n8n Official MCP Path | Defer | Defer (unchanged) | API boundary preferred |
| SQLite MCP | Defer | Defer (unchanged) | No SQLite state yet |
| Playwright MCP | Reject | Rejected for Now | Permanently rejected (unchanged — upgraded to reflect RCE risks) |
| Docker MCP | Reject | Rejected for Now | Permanently rejected (unchanged) |
| Obsidian/Markdown MCP | Reject | Rejected for Now | Permanently prohibited (unchanged) |
| Browser/Search MCP | Defer | Defer (unchanged) | API key management needed |
| Memory MCP | Defer | Defer (unchanged) | Event log + structured state preferred |

### Cross-References

- [LifeOS Repo Radar](LifeOS_Repo_Radar.md) — full candidate entries with 16-dimension evaluation
- [MCP Candidate Catalog](../mcp/catalog/MCP_Candidate_Catalog.md) — original 15-entry catalog
- [MCP Security Policy](MCP_Security_Policy.md) — deny-by-default, prohibition list, mount checklist
- [MCP Roadmap](MCP_Roadmap.md) — V1/V2/V3 tool catalog
- [External Tool Evaluation Checklist](LifeOS_External_Tool_Evaluation_Checklist.md) — 14-point evaluation checklist
- [Capture Processor Roadmap](Capture_Processor_Roadmap.md) — processor catalog (MarkItDown target)
