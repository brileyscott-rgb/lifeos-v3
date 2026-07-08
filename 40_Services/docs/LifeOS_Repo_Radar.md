# LifeOS Repo Radar V1

> Safe candidate tracking and evaluation system for interesting GitHub repos,
> MCP servers, Docker tools, n8n templates, and AI-agent frameworks.
> No external repos cloned. No packages installed. No services activated.
> Created: 2026-07-08

## Purpose

The Repo Radar is a documentation + scoring utility that builds a safe,
reviewable backlog of external tools **before** any installation or runtime
activation. Every candidate is evaluated against LifeOS security policies,
permission tiers (A0-A5), and infrastructure readiness.

No candidate in this radar is approved for production deployment. All
require sandbox-staging-production gating per MCP Security Policy.

## Evaluation Framework

Each candidate is assessed on 16 dimensions:

| Dimension | Description |
|-----------|-------------|
| **Risk Tier** | A0 (read-only observe) through A5 (system mutation) |
| **Install Status** | not-installed / scaffold / docker-image-pulled / installed |
| **Activation Status** | inactive / sandbox-test / staging / production |
| **Allowed Sandbox Path** | Where it may run safely |
| **Forbidden Paths** | Mounts/paths it must never access |
| **Network Exposure Risk** | none / localhost / internal-network / tailscale / internet |
| **Secret/Auth Requirement** | Whether it needs API keys, tokens, or credentials |
| **Docker/Socket Requirement** | Whether it needs Docker or Docker socket |
| **First Safe Test** | The minimal safe test, if infrastructure supports it |
| **Rollback Notes** | How to cleanly remove if tested |
| **Recommendation** | sandbox / defer / reject / reclassify |
| **Category** | mcp-server / proxy / agent-platform / sandbox / discovery / library |
| **Why Interesting** | What value it could bring to LifeOS |
| **Proposed LifeOS Use** | How it fits LifeOS architecture |
| **Infrastructure Prerequisites** | What must exist before testing |
| **Supply-Chain Risk** | Runtime downloads, cloud backends, plugin systems |

---

## Candidate Entries

### 1. modelcontextprotocol/servers (Official MCP Reference Servers)

| Field | Value |
|-------|-------|
| **Name** | MCP Official Reference Servers |
| **URL/Name** | `https://github.com/modelcontextprotocol/servers` |
| **Category** | mcp-server suite |
| **Risk Tier** | Varies: filesystem=**A3** (write-capable), git=**A3** (write by default), fetch=**A1**, sqlite=**A3** (write-capable), memory=**A3** (persistent write), time=**A0** |
| **Install Status** | **not-installed** |
| **Activation Status** | **inactive** |
| **Why Interesting** | Reference implementations for MCP protocol. Foundation for understanding what MCP servers look like and how they work. |
| **Proposed LifeOS Use** | Sandbox-test individual servers (filesystem, git, fetch, time) to validate MCP integration pattern. Not for production — custom LifeOS MCP tools preferred per MCP Roadmap. |
| **Allowed Sandbox Path** | `40_Services/mcp/sandbox/test-data/` |
| **Forbidden Paths** | `10_Vaults/`, `50_Event_Log/`, `~/.ssh/`, `~/.config/`, `/home/lifeos/*`, `.env` |
| **Network Exposure Risk** | **localhost** (stdio transport) for local servers. **outbound** for fetch/search servers. |
| **Secret/Auth Requirement** | Some sub-servers require API keys (Brave Search, GitHub token, Postgres credentials). Read-only servers (filesystem, git, time, memory) require no secrets. |
| **Docker/Socket Requirement** | No Docker socket required. Individual servers may run in Docker containers with bounded mounts for sandbox testing. |
| **First Safe Test** | Run `@modelcontextprotocol/server-time` via stdio transport. Fully read-only, no filesystem, no network, no secrets. Proves MCP client/server integration with zero risk. |
| **Rollback Notes** | `npm uninstall` or `pip uninstall` per-server packages. Remove sandbox test-data files. No Docker volumes to clean. |
| **Infrastructure Prerequisites** | MCP client (OpenCode or Claude Desktop) configured. Sandbox MCP runtime tested (not yet done — mcpo sandbox test deferred). Node.js + npx or Python + uvx available. |
| **Supply-Chain Risk** | npm packages with transitive dependencies. Archived servers (puppeteer, postgres, github, etc.) indicate maintenance churn. Each sub-server requires individual dependency review. |
| **Recommendation** | **Sandbox** individual servers, not the entire suite. Start with `server-time` (safest, read-only, no deps). Never promote to production — custom LifeOS MCP tools preferred for production per MCP Roadmap. |

**Reality Check Notes**: The candidate catalog's blanket "Sandbox" rating for the entire suite masks individual server risks. Each sub-server needs independent evaluation. The `server-memory` persists knowledge graph to disk (write-capable). `server-filesystem` has no per-operation allowlist — only path-based restrictions. Prefer LifeOS custom MCP tools for production (`lifeos.status`, `lifeos.git_status`, etc.).

---

### 2. open-webui/mcpo (MCP-to-OpenAPI Proxy)

| Field | Value |
|-------|-------|
| **Name** | mcpo |
| **URL/Name** | `https://github.com/open-webui/mcpo` |
| **Category** | proxy |
| **Risk Tier** | **A2** (privilege amplifier — inherits risk of proxied MCP servers) |
| **Install Status** | **scaffold** — `docker-compose.example.yml` and `config.example.json` exist |
| **Activation Status** | **inactive** |
| **Why Interesting** | Bridges MCP servers to OpenAI-compatible chat UIs. Central MCP routing for Open WebUI, local models, and future AI chat interfaces. |
| **Proposed LifeOS Use** | When Open WebUI is deployed (V2+), mcpo connects it to LifeOS MCP tools (status, git, captures) without custom Open WebUI tool integrations. |
| **Allowed Sandbox Path** | `40_Services/mcp/sandbox/` — only sandbox MCP servers |
| **Forbidden Paths** | `10_Vaults/`, `50_Event_Log/`, `~/.ssh/`, `~/.config/`, `/home/lifeos/*`, production MCP servers, `.env` |
| **Network Exposure Risk** | **localhost** (binds 127.0.0.1). SSE transport creates outbound connections to remote MCP servers if configured — must be blocked in V1. |
| **Secret/Auth Requirement** | API key optional but strongly recommended. Without `--api-key`, mcpo exposes all MCP tools as unauthenticated REST endpoints. OAuth token storage in `~/.mcpo/tokens/` is a concern. |
| **Docker/Socket Requirement** | No Docker socket. Docker container deployment available via `ghcr.io/open-webui/mcpo`. |
| **First Safe Test** | Start mcpo + `mcp-server-time` with `--api-key` set, verify only time tools available, confirm localhost binding, verify `deny_by_default: true` in config. The mcpo scaffold README documents this test. |
| **Rollback Notes** | `docker-compose -f 40_Services/mcpo/docker-compose.example.yml down -v`. Remove mcpo files. No persistent data. |
| **Infrastructure Prerequisites** | MCP server to proxy (none active in production). MCP client to consume the proxy (none active — Open WebUI not deployed). Test requires: (1) sandbox MCP server running, (2) mcpo connecting to it, (3) curl verification of REST endpoints. |
| **Supply-Chain Risk** | Docker image from ghcr.io. Python package from PyPI. Hot-reload feature watches config files for changes — could load new MCP servers at runtime. OAuth token storage path could accumulate credentials. |
| **Recommendation** | **Sandbox** (scaffold exists). mcpo is infrastructure for a future phase. Do not activate in production until: (1) LifeOS has MCP servers worth proxying, (2) LifeOS has an AI chat interface to consume them, (3) `--api-key` authentication is mandatory, (4) config hot-reload is off or gated. |

**Reality Check Notes**: mcpo is a privilege amplifier, not a neutral proxy. It spawns MCP servers as child processes — if configured with root filesystem MCP, it grants root filesystem access. It has NO tool-level access control of its own. The scaffold exists but no test has been run. This is a tool looking for a problem in LifeOS V1.

---

### 3. github/github-mcp-server (Official GitHub MCP)

| Field | Value |
|-------|-------|
| **Name** | GitHub MCP Server |
| **URL/Name** | `https://github.com/github/github-mcp-server` |
| **Category** | mcp-server |
| **Risk Tier** | **A4** (read = A1, but write = A4: create issues, manage PRs, Copilot agent invocation). Read-only tools still expose private repo contents if PAT has `repo` scope. |
| **Install Status** | **not-installed** |
| **Activation Status** | **inactive** |
| **Why Interesting** | Official GitHub-maintained MCP server. Deep GitHub integration — repos, issues, PRs, Copilot code review. Two deployment modes: local (PAT/OAuth app) and remote (`api.githubcopilot.com/mcp/`). |
| **Proposed LifeOS Use** | Agent-driven GitHub operations: check repo status, create issues, review PRs. Read-only status via existing `lifeos_services.py` is sufficient for V1. |
| **Allowed Sandbox Path** | N/A — no filesystem mounts needed. |
| **Forbidden Paths** | N/A — no filesystem mounts. But token scope must be restricted to a test repo only, never the LifeOS repo. |
| **Network Exposure Risk** | **outbound** to GitHub API. Remote mode connects to `api.githubcopilot.com` — data exfiltration risk. OAuth callback port (`127.0.0.1:8085`) could be exposed if misconfigured. |
| **Secret/Auth Requirement** | **YES** — GitHub PAT or OAuth app credentials. Token scope management is critical. `GITHUB_PERSONAL_ACCESS_TOKEN` in environment variable — LifeOS policy prohibits secrets in MCP-accessible env vars. |
| **Docker/Socket Requirement** | No Docker socket. Go binary or Docker container. |
| **First Safe Test** | Create a fine-grained PAT scoped to a test sanity repo (not LifeOS). Run in `--read-only` mode with `--toolsets repos`. Verify no write operations succeed. Verify token scope doesn't expose private repos. **The PAT creation itself is an A4-tier action requiring explicit approval.** |
| **Rollback Notes** | Stop the MCP server. Revoke the GitHub PAT immediately. Remove any OAuth app credentials. No persistent data. |
| **Infrastructure Prerequisites** | GitHub PAT with explicitly documented scope. Test repo that IS NOT the LifeOS repo. Go runtime or Docker for binary. MCP client configured. |
| **Supply-Chain Risk** | Go binary dependencies. Remote mode depends on GitHub's hosted infrastructure (`api.githubcopilot.com`). Copilot agent tools (`assign_copilot_to_issue`, `request_copilot_review`) trigger AI code generation on GitHub's side. |
| **Recommendation** | **Defer** — requires GitHub PAT with scope management policy before any test. LifeOS git needs are served by existing scripts and planned custom `lifeos.git_status` tool. `lifeos_services.py` already reports git dirty state. Re-evaluate when AI agents need programmatic GitHub access (V3+). |

**Reality Check Notes**: The distinction between local and remote server modes is critical — they have completely different risk profiles. "Read-only" is misleading if the PAT has broad scopes. The `assign_copilot_to_issue` tool can trigger AI code generation on GitHub's side, consuming quota and producing changes. LifeOS has no AI agents to drive GitHub operations in V1. The PAT creation is itself an A4-tier action.

---

### 4. qdrant/mcp-server-qdrant (Qdrant Vector DB MCP)

| Field | Value |
|-------|-------|
| **Name** | Qdrant MCP Server |
| **URL/Name** | `https://github.com/qdrant/mcp-server-qdrant` |
| **Category** | mcp-server |
| **Risk Tier** | **Cannot evaluate** — Qdrant not deployed in LifeOS. Inherent risks: write-capable by default (`QDRANT_READ_ONLY=false`), runtime ML model download, `QDRANT_LOCAL_PATH` grants direct disk access. |
| **Install Status** | **not-installed** |
| **Activation Status** | **inactive** |
| **Why Interesting** | Official Qdrant MCP server. Enables AI agents to query and manage vector database collections for semantic search over indexed vault content. |
| **Proposed LifeOS Use** | Semantic search over indexed vault content. Semantic Janitor agent uses vector search to find duplicates, cross-links, and similar notes. Read-only search first, write-gated collection management in V3. |
| **Allowed Sandbox Path** | N/A — Qdrant not deployed. |
| **Forbidden Paths** | `10_Vaults/`, `50_Event_Log/`, `.env`, production data paths. |
| **Network Exposure Risk** | **internal-network** (to Qdrant). SSE transport could expose HTTP endpoint if misconfigured. Docker deployment guide uses `FASTMCP_SERVER_HOST=0.0.0.0` — must be overridden to `127.0.0.1`. |
| **Secret/Auth Requirement** | Qdrant API key if auth enabled. |
| **Docker/Socket Requirement** | No Docker socket. Requires network access to Qdrant container. |
| **First Safe Test** | Run with `QDRANT_URL=":memory:"` and `COLLECTION_NAME="test"` using `fastmcp dev`. In-memory mode avoids needing a Qdrant server. **But**: the default `EMBEDDING_PROVIDER=fastembed` downloads an ~80MB ML model from Hugging Face at first use — an outbound network call and disk write. |
| **Rollback Notes** | Stop server. Remove in-memory data (no persistence). Clear downloaded models from `~/.cache/huggingface/` if needed. |
| **Infrastructure Prerequisites** | Qdrant deployed and stable (not done — decision exists, no deployment). Vault content indexed as vectors (not done — no embedding pipeline). Disk ≥ 90% — Qdrant + models + indices would push it higher. |
| **Supply-Chain Risk** | Runtime model download from Hugging Face at first use — untrusted binary, supply-chain attack vector. Embedding model is downloaded without pre-vetting. Default write-capable could poison vector database. |
| **Recommendation** | **Reject for V1** — infrastructure doesn't exist. The candidate catalog's "Defer" rating understates the gap. No Qdrant, no indices, no embedding pipeline. Re-evaluate only when: (1) Qdrant is deployed and stable, (2) document indexing pipeline exists, (3) embedding model is pre-downloaded and verified, (4) `QDRANT_READ_ONLY=true` is verified as default, (5) disk usage allows. |

**Reality Check Notes**: Even the "safe" in-memory test requires downloading an ML model at runtime — an outbound network call that establishes supply-chain dependency. The write-by-default behavior (`QDRANT_READ_ONLY=false`) is dangerous. Qdrant access should go through a LifeOS Search API, not direct MCP — same conclusion as the existing candidate catalog.

---

### 5. microsoft/playwright-mcp (Playwright Browser Automation MCP)

| Field | Value |
|-------|-------|
| **Name** | Playwright MCP |
| **URL/Name** | `https://github.com/microsoft/playwright-mcp` |
| **Category** | mcp-server |
| **Risk Tier** | **A5-critical** (RCE-equivalent, file access, proxy, persistent browser sessions). Microsoft's own docs: "Playwright MCP is NOT a security boundary." |
| **Install Status** | **not-installed** |
| **Activation Status** | **inactive** |
| **Why Interesting** | Powerful browser automation for screenshots, web scraping, form filling, and testing. Official Microsoft Playwright team project. |
| **Proposed LifeOS Use** | None in V1. Browser automation for capture intake would go through n8n HTTP Request nodes with domain restrictions, not full browser MCP. |
| **Allowed Sandbox Path** | N/A |
| **Forbidden Paths** | Everything — permanently prohibited under MCP Security Policy. |
| **Network Exposure Risk** | **Critical** — browser can navigate anywhere, execute JavaScript, make network requests. Can exfiltrate data via redirects bypassing `--allowed-origins`. |
| **Secret/Auth Requirement** | `--secrets` flag reads a dotenv file — MCP server accesses secrets. `--cdp-endpoint` can hijack existing Chrome sessions with logged-in services. |
| **Docker/Socket Requirement** | Docker mode requires `--no-sandbox` (disables Chromium sandbox). Docker deployment without `--no-sandbox` requires `--cap-add=SYS_ADMIN`. Both increase container escape risk. |
| **First Safe Test** | **No safe test exists.** Even a "screenshot of localhost:8787/health" requires: (1) Chromium download (~300MB), (2) browser process spawned, (3) JavaScript execution, (4) network access. It normalizes browser automation capability in LifeOS — a capability the Security Policy explicitly rejected. |
| **Rollback Notes** | Stop MCP server. Remove Chromium binaries. Clear `~/.cache/ms-playwright/`. Remove persistent browser profiles containing cookies and session data. |
| **Infrastructure Prerequisites** | Node.js 18+. Chromium download (~300MB, disk impact at 91%). Container escape hardening if Docker deployment. |
| **Supply-Chain Risk** | Chromium download at first use (~300MB untrusted binary). `--no-sandbox` disables browser security sandbox. Persistent profiles store cookies/sessions across sessions. `browser_run_code_unsafe` is RCE-equivalent — labeled "unsafe" by Microsoft. |
| **Recommendation** | **Permanently rejected** — the MCP Security Policy already prohibits browser automation in V1. Playwright MCP's own documentation says it is NOT a security boundary. `browser_run_code_unsafe` is described by Microsoft as "RCE-equivalent." The `--allowed-origins` flag does not block redirects. Even "read-only screenshots" execute JavaScript and can exfiltrate data. Do not re-evaluate. |

**Reality Check Notes**: This is the single most dangerous MCP candidate in the entire ecosystem. The vendor explicitly states it is not a security boundary. Persistent browser profiles store cookies. CDP endpoint hijacking can control existing Chrome sessions. Any attempt to override this rejection with "read-only screenshots" or "strict domain binding" is fantasy — Microsoft's own docs refute the effectiveness of origin restrictions for security.

---

### 6. Microsoft MarkItDown MCP

| Field | Value |
|-------|-------|
| **Name** | MarkItDown |
| **URL/Name** | `https://github.com/microsoft/markitdown` |
| **Category** | **library** (NOT an MCP server natively) |
| **Risk Tier** | **A3** as Capture Processor (bounded read-only input, write-only buffer output). **A4** if cloud backends or plugins enabled. |
| **Install Status** | **not-installed** |
| **Activation Status** | **inactive** |
| **Why Interesting** | Converts PDF, DOCX, PPTX, XLSX, HTML, EPUB, ZIP, images, audio to Markdown. Microsoft-maintained Python library. Genuinely useful for Capture Pipeline document ingestion. |
| **Proposed LifeOS Use** | **Capture Processor** — convert captured documents to Markdown for vault import. Not an MCP tool. Should run as a Docker container with bounded file access (read-only input mount, write-only buffer vault output), cloud backends disabled, plugins disabled. Fits the Capture Processor Roadmap's "Markdown Formatter" processor. |
| **Allowed Sandbox Path** | As processor: read-only input from `30_Capture/` or buffer vault. Write-only output to `LifeOS_Capture_Buffer/`. |
| **Forbidden Paths** | `10_Vaults/`, `~/.ssh/`, `~/.config/`, `.env`, internet for cloud backends. |
| **Network Exposure Risk** | **none** (local-only conversion). **Critical** if Azure Document Intelligence or OpenAI image description backends are enabled — data exfiltration to Microsoft cloud. |
| **Secret/Auth Requirement** | None for local conversion. OpenAI API key if image description enabled (must not be enabled). Azure credentials if Document Intelligence enabled (must not be enabled). |
| **Docker/Socket Requirement** | No Docker socket. Docker container deployment recommended with bounded mounts. |
| **First Safe Test** | Convert a known-safe test PDF/DOCX to Markdown. Local conversion only (`convert_local()`). Cloud backends disabled. Plugins disabled. Read-only input mount, write-only output mount. Verify no outbound network calls. |
| **Rollback Notes** | Stop container. Remove pip package. Remove any downloaded plugin dependencies. No persistent data. |
| **Infrastructure Prerequisites** | Python 3.10+. Capture Processor pipeline (scaffold only — not implemented). Buffer vault exists at `LifeOS_Capture_Buffer/`. |
| **Supply-Chain Risk** | `pip install markitdown[all]` pulls pdfplumber, python-pptx, and other parsing libraries — moderate dependency surface. Image description uses OpenAI API (cloud exfiltration). Azure backends send documents to Microsoft. Plugin system (`enable_plugins=True`) allows arbitrary code execution. ZIP file recursion could be exploited with zip bombs. |
| **Recommendation** | **Reclassify — evaluate as Capture Processor, not MCP server.** MarkItDown is a Python library, not an MCP server natively. Community MCP wrappers exist but add supply-chain risk. The LifeOS use case (document → Markdown conversion) fits the Capture Processor model. As a Docker container with: (1) bounded read-only input mount, (2) write-only buffer vault output, (3) cloud backends disabled, (4) plugins disabled, (5) limited to `convert_local()` — this is a reasonable V2 capture processor. As an MCP tool available to AI agents, it is HIGH RISK. |

**Reality Check Notes**: MarkItDown is the most genuinely useful candidate for LifeOS among the 10. But evaluating it as an "MCP server" is a category error. It's a library that should be wrapped as a Capture Processor, not exposed as an AI-agent tool. The cloud backends (Azure, OpenAI) are data exfiltration paths. Microsoft's own security note: "Do not pass untrusted input directly to MarkItDown" — important when processing captured files.

---

### 7. OpenHands/openhands (AI-Driven Development Platform)

| Field | Value |
|-------|-------|
| **Name** | OpenHands (formerly OpenDevin) |
| **URL/Name** | `https://github.com/OpenHands/openhands` |
| **Category** | **agent-platform** (NOT an MCP server — it CONSUMES MCP) |
| **Risk Tier** | **A5-equivalent** — code execution, container spawning, filesystem access, cloud agent backends, third-party integrations (Slack, GitHub, Linear). |
| **Install Status** | **scaffold** — `docker-compose.example.yml` and `Sandbox_Policy.md` exist |
| **Activation Status** | **inactive** |
| **Why Interesting** | Full AI-powered software engineering platform. Agent Canvas for multi-agent coding. Docker sandbox mode for isolated execution. |
| **Proposed LifeOS Use** | **Sandboxed agent lab** — not main LifeOS executor. Test unknown repos, prototype MCP servers, evaluate dependencies, learning projects. Output exported as patches/reports/artifacts, reviewed by human or OpenCode before production use. |
| **Allowed Sandbox Path** | `60_Sandboxes/OpenHands/workspaces/` — isolated per experiment |
| **Forbidden Paths** | `10_Vaults/`, `/home/lifeos/.ssh/`, `/home/lifeos/.config/`, any `.env` file, any production repo, Docker socket write. |
| **Network Exposure Risk** | **localhost** (binds 127.0.0.1). Outbound internet for package installs and git clone (acceptable within sandbox container). Cloud agent backends = data exfiltration. |
| **Secret/Auth Requirement** | LLM API key required for any agent to function (e.g., Anthropic API key for Claude). Optional: GitHub token, Slack token, Linear token, Notion token for integrations. |
| **Docker/Socket Requirement** | Sandbox mode requires Docker socket (`/var/run/docker.sock:ro`). LifeOS MCP Security Policy PERMANENTLY PROHIBITS Docker socket access. This creates a fundamental conflict. Non-sandbox mode runs with "full filesystem access" — explicitly warned against. |
| **First Safe Test** | **No safe test exists without an LLM API key.** Without an API key, agents can't function — the test would be a web UI with no functional agents. Docker socket requirement conflicts with LifeOS security policy. Every LifeOS constraint (bounded mounts, export pipeline, A4 approval) requires implementation that doesn't exist. |
| **Rollback Notes** | `docker-compose -f 40_Services/openhands/docker-compose.example.yml down -v`. Remove workspace data. Remove exports. Remove LLM API key from environment. |
| **Infrastructure Prerequisites** | Node.js 22.12+. LLM API key (A4-tier decision — not configured). Docker (available). 4-8GB+ additional disk. The "export patches, review, apply" pipeline doesn't exist. The "sandbox with bounded mounts" configuration is untested. |
| **Supply-Chain Risk** | Docker image from `docker.all-hands-dev`. Code in transition (source being reorganized across repos). Cloud agent backends send code/data to OpenHands infrastructure. Third-party integrations require multiple API tokens. |
| **Recommendation** | **Defer — reclassify as AI Agent Infrastructure, not MCP server.** OpenHands is a coding agent platform that consumes MCP. It should be evaluated under AI Agent Infrastructure policy, not MCP Radar. Every LifeOS constraint in the Sandbox_Policy.md is aspirational — none have been implemented or tested. Before re-evaluation: (1) Docker socket policy conflict must be resolved, (2) LLM API key management policy must exist, (3) Artifact review pipeline must be implemented, (4) Sandbox mount restrictions must be verified. |

**Reality Check Notes**: OpenHands is the most elaborate fantasy in the candidate list. The LifeOS Sandbox_Policy.md defines beautiful constraints — bounded mounts, export pipeline, A4 approval — none of which exist. The Docker socket requirement conflicts with LifeOS's permanent prohibition. Without an LLM API key, OpenHands does nothing. Every "allowed" constraint requires active enforcement that OpenHands doesn't natively provide.

---

### 8. kubernetes-sigs/agent-sandbox (Kubernetes Sandbox Operator)

| Field | Value |
|-------|-------|
| **Name** | agent-sandbox |
| **URL/Name** | `https://github.com/kubernetes-sigs/agent-sandbox` |
| **Category** | **sandbox-infrastructure** (Kubernetes operator — NOT an MCP server) |
| **Risk Tier** | **Cannot evaluate** — requires Kubernetes. LifeOS explicitly deferred Kubernetes and runs on Docker Compose. |
| **Install Status** | **not-installed** |
| **Activation Status** | **inactive** |
| **Why Interesting** | Kubernetes-native sandbox for AI agents. Strong isolation (gVisor, Kata Containers). Warm pools for instant sandbox creation. CRD-based management. |
| **Proposed LifeOS Use** | None in current architecture. LifeOS uses Docker Compose for service orchestration. Kubernetes/homelab expansion is explicitly deferred per Current Working State. |
| **Allowed Sandbox Path** | N/A — requires Kubernetes cluster. |
| **Forbidden Paths** | N/A |
| **Network Exposure Risk** | **cluster-internal** (Kubernetes networking). |
| **Secret/Auth Requirement** | Kubernetes cluster credentials (`kubectl` config). |
| **Docker/Socket Requirement** | Kubernetes cluster (minikube, kind, k3s, or full cluster). gVisor/Kata Containers for strong isolation require special container runtime configuration. |
| **First Safe Test** | **No test exists without Kubernetes.** Deploying minikube/kind on the LifeOS machine would consume 2-4GB RAM and 20GB+ disk — unreasonable at 91% disk usage. This is an A5-tier system mutation requiring admin approval. |
| **Rollback Notes** | Delete Kubernetes cluster. Remove kubectl config. Clean up persistent volumes. |
| **Infrastructure Prerequisites** | Kubernetes cluster — explicitly deferred. Container runtime with gVisor/Kata support. PersistentVolume provisioner. 2-4GB RAM, 20GB+ disk. Go SDK or Python SDK for programmatic control. |
| **Supply-Chain Risk** | Kubernetes operator with CRDs — cluster-admin level access. Requires trusting the operator to not escape its RBAC boundaries. |
| **Recommendation** | **Reject for current architecture** — requires Kubernetes, which LifeOS doesn't have and doesn't plan for. Not an MCP server. Remove from MCP Radar. Re-evaluate only if LifeOS adopts Kubernetes (V4+ minimum). |

**Reality Check Notes**: This is the clearest category error in the list. agent-sandbox is a Kubernetes operator — it requires a Kubernetes cluster, `kubectl`, CRDs, and controllers. LifeOS runs on Docker Compose. Kubernetes is explicitly deferred. Even a minimal test cluster would be an unreasonable infrastructure commitment.

---

### 9. punkpeye/awesome-mcp-servers (Community Discovery Index)

| Field | Value |
|-------|-------|
| **Name** | awesome-mcp-servers |
| **URL/Name** | `https://github.com/punkpeye/awesome-mcp-servers` |
| **Category** | **discovery-index** |
| **Risk Tier** | **A0** (read-only reference list). Usage risk: **A3** — following links and installing unvetted servers. |
| **Install Status** | **not-installed** (no installation — it's a README) |
| **Activation Status** | **inactive** |
| **Why Interesting** | Community-curated list of hundreds of MCP servers. Broad ecosystem awareness. Discover what exists in the MCP landscape. |
| **Proposed LifeOS Use** | Awareness tool — discover what MCP servers exist. NEVER install a server solely because it appears in this list. Always apply the candidate catalog evaluation framework. Prefer the official MCP Registry for structured discovery. |
| **Allowed Sandbox Path** | N/A (it's a README). |
| **Forbidden Paths** | N/A |
| **Network Exposure Risk** | **none** (it's a README on GitHub). Links lead to untrusted repositories. |
| **Secret/Auth Requirement** | None |
| **Docker/Socket Requirement** | None |
| **First Safe Test** | Review the list for awareness. Identify servers that match LifeOS needs. Apply LifeOS evaluation framework before ANY installation. |
| **Rollback Notes** | N/A |
| **Infrastructure Prerequisites** | None — it's a README. |
| **Supply-Chain Risk** | Links to hundreds of untrusted repositories. Some may be abandoned, malicious, or contain vulnerable dependencies. No security review of any listed server. Promotes `glama.ai/mcp/servers` — a third-party commercial MCP registry. |
| **Recommendation** | **Discovery reference only.** Useful for ecosystem awareness. Dangerous if treated as "recommended" or "vetted" list. The quantity (8,500+ commits, 2,400+ open PRs, hundreds of servers) creates false abundance and decision pressure. LifeOS already has a structured candidate catalog with explicit risk assessment per server. Prefer the official MCP Registry (`registry.modelcontextprotocol.io`) for structured discovery. |

**Reality Check Notes**: "Awesome" lists are popularity contests, not security evaluations. Anyone can submit a PR to add their server. No security review, no risk assessment, no quality bar. Includes servers LifeOS has ALREADY REJECTED (browser automation, shell execution, Docker socket). The noise level is very high. Useful for awareness, dangerous as authority.

---

### 10. tolkonepiu/best-of-mcp-servers (Ranked Discovery Index)

| Field | Value |
|-------|-------|
| **Name** | best-of-mcp-servers |
| **URL/Name** | `https://github.com/tolkonepiu/best-of-mcp-servers` |
| **Category** | **discovery-index** |
| **Risk Tier** | **A0** (read-only reference list). Usage risk: **A3** — structured data creates false sense of quality. |
| **Install Status** | **not-installed** |
| **Activation Status** | **inactive** |
| **Why Interesting** | Ranked, categorized list of 400+ MCP servers with quality scores. Structured YAML data (`projects.yaml`). Automated freshness indicators (active/inactive/dead). More useful than awesome-mcp-servers for programmatic discovery. |
| **Proposed LifeOS Use** | Structured discovery source — use `projects.yaml` for programmatic candidate identification. Apply LifeOS evaluation framework to every server, regardless of rank. Build a LifeOS-specific scoring system based on Security Policy compliance. |
| **Allowed Sandbox Path** | N/A |
| **Forbidden Paths** | N/A |
| **Network Exposure Risk** | **none** (it's a generated README + YAML data). |
| **Secret/Auth Requirement** | None |
| **Docker/Socket Requirement** | None |
| **First Safe Test** | Parse `projects.yaml` for server metadata. Build a LifeOS-aware filter (exclude rejected categories, flag high-risk capabilities). Use as discovery input for the candidate catalog. |
| **Rollback Notes** | N/A |
| **Infrastructure Prerequisites** | None — YAML data file is static. |
| **Supply-Chain Risk** | Generated weekly by scraping GitHub metadata — no review of listed servers. "Quality score" measures GitHub popularity (stars, downloads, activity), not security or LifeOS compatibility. |
| **Recommendation** | **Discovery reference — structured data useful, quality scores dangerous.** `projects.yaml` provides structured server metadata that enables programmatic filtering. The quality ranking must NOT be used for LifeOS decision-making. The ranking measures GitHub popularity, not LifeOS safety. A server ranked #1 (Playwright MCP, 35K stars) is permanently rejected by LifeOS policy. Use as discovery input, never as quality authority. |

**Reality Check Notes**: The structured data (`projects.yaml`) is genuinely more useful than awesome-mcp-servers for programmatic discovery. But the ranking system is actively dangerous — it equates GitHub popularity with quality, which would lead LifeOS to trust servers it has already rejected as critical risk. The "active" label is based on commit recency, not security maintenance. Build a LifeOS-specific scoring system instead.

---

## Radar Summary

### Category Breakdown

| Category | Count | Candidates |
|----------|-------|------------|
| **mcp-server** | 3 | Official MCP Servers, GitHub MCP, Qdrant MCP |
| **mcp-server (rejected)** | 1 | Playwright MCP |
| **proxy** | 1 | mcpo |
| **library (misclassified)** | 1 | MarkItDown → reclassify as Capture Processor |
| **agent-platform (misclassified)** | 1 | OpenHands → reclassify as AI Agent Infrastructure |
| **sandbox-infrastructure (misclassified)** | 1 | agent-sandbox → reclassify as Container Orchestration (requires Kubernetes) |
| **discovery-index** | 2 | awesome-mcp-servers, best-of-mcp-servers |

### Recommendation Distribution

| Recommendation | Count | Candidates |
|----------------|-------|------------|
| **Sandbox** | 2 | Official MCP Servers (individual sub-servers only), mcpo |
| **Defer** | 1 | GitHub MCP |
| **Reject for V1** | 1 | Qdrant MCP (infrastructure doesn't exist) |
| **Permanently Rejected** | 1 | Playwright MCP |
| **Reclassify** | 3 | MarkItDown (Capture Processor), OpenHands (AI Agent Infrastructure), agent-sandbox (requires Kubernetes) |
| **Discovery Reference** | 2 | awesome-mcp-servers, best-of-mcp-servers |

### Key Findings

1. **Three of ten candidates are NOT MCP servers.** OpenHands is a coding agent platform that consumes MCP. agent-sandbox is a Kubernetes operator. MarkItDown is a Python library. Evaluating them alongside MCP servers confuses the radar's purpose.

2. **Infrastructure prerequisites gap is severe.** Qdrant requires a deployed Qdrant + embedding pipeline (neither exists). GitHub MCP requires a PAT with documented scope policy (not created). mcpo requires MCP servers + AI chat interface (neither active). Only 2 candidates can be sandbox-tested today: Official MCP sub-servers and mcpo.

3. **Read-only deception is common.** "Read-only" modes hide data exposure risks (GitHub PAT exposes private repos), write-by-default behaviors (Qdrant defaults to read-write), and network exfiltration paths (Playwright JavaScript execution on "read-only" screenshots).

4. **Supply-chain risk is concentrated at runtime.** Qdrant downloads ML models at first use. Playwright downloads Chromium. mcpo supports hot-reload of MCP server configs. MarkItDown has cloud backends that exfiltrate data.

5. **Discovery indexes are useful but dangerous.** awesome-mcp-servers and best-of-mcp-servers help discover what exists, but their popularity-based ranking and lack of security review make them dangerous as decision tools.

### Next Actions

1. Sandbox-test `@modelcontextprotocol/server-time` — the single safest MCP server (read-only, no filesystem, no network, no secrets).
2. Complete the mcpo sandbox test per `40_Services/mcpo/README.md`.
3. Build LifeOS-specific MCP scoring system based on Security Policy compliance.
4. Add MarkItDown to the Capture Processor roadmap (not MCP Radar).
5. Re-evaluate OpenHands under AI Agent Infrastructure policy (not MCP Radar).
6. Remove agent-sandbox from radar — requires Kubernetes which LifeOS doesn't have.
7. Integrate `best-of-mcp-servers/projects.yaml` as a discovery source for future candidate identification.

### Cross-References

- [MCP Candidate Catalog](../mcp/catalog/MCP_Candidate_Catalog.md) — existing 15 entries with V1 decisions
- [MCP Security Policy](MCP_Security_Policy.md) — deny-by-default, mount checklist, prohibition list
- [MCP Roadmap](MCP_Roadmap.md) — V1/V2/V3 tool catalog and activation plan
- [Docker + MCP Service Map](Docker_MCP_Service_Map.md) — current services, ports, MCP exposure
- [LifeOS Tool Registry](LifeOS_Tool_Registry.md) — all active tools with risk tiers
- [LifeOS Tool Permission Tiers](LifeOS_Tool_Permission_Tiers.md) — A0-A5 tier definitions
- [Capture Processor Roadmap](Capture_Processor_Roadmap.md) — processor catalog (MarkItDown target)
- [mcpo README](../mcpo/README.md) — scaffold and safe first-test plan
- [OpenHands README](../openhands/README.md) — sandbox policy and activation gate
