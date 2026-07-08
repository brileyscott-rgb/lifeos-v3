# LifeOS External Tool Evaluation Checklist

> Standard 14-point checklist for evaluating any external tool, MCP server,
> Docker service, n8n template, or AI-agent framework before sandbox testing
> or production activation.
> Created: 2026-07-08

## Purpose

Every external tool proposed for LifeOS must pass this checklist before any
installation, sandbox test, or runtime activation. The checklist is designed to
surface hidden risks that a casual evaluation might miss.

Use this checklist alongside the [MCP Security Policy](MCP_Security_Policy.md)
and [LifeOS Tool Permission Tiers](LifeOS_Tool_Permission_Tiers.md).

## The 14-Point Checklist

For each candidate tool, answer every question. A single "yes" on a high-risk
question may be grounds for deferral, quarantine, or rejection.

### 1. Does it require secrets?

Does the tool need API keys, tokens, OAuth credentials, passwords, or any
secret-bearing environment variables to function?

- [ ] **No secrets required** — safe for sandbox test.
- [ ] **Secrets required** — document which secrets and their scope. Requires
  A4 approval for secret creation. Secrets must use environment variables
  in Docker Compose, never committed config files.

**Examples:**
- `server-time`: No secrets. Safe.
- `github-mcp-server`: GitHub PAT required. A4 approval for token creation.
- `server-brave-search`: Brave Search API key required.

**Red flags:** Secrets stored in config files, secrets in environment variables
accessible by MCP servers, OAuth token storage paths.

---

### 2. Does it require Docker socket?

Does the tool need `/var/run/docker.sock` — read-only or read-write?

- [ ] **No Docker socket** — safe.
- [ ] **Docker socket read-only** — documented risk. Requires justification.
- [ ] **Docker socket read-write** — **permanently prohibited** per MCP
  Security Policy.

**Examples:**
- `lifeos-status-api`: No Docker socket. Safe.
- `lifeos-dozzle`: Read-only Docker socket. Controlled, documented risk.
- `docker-mcp-server`: Read-write Docker socket. Permanently rejected.

**Red flags:** Any Docker socket access without explicit security justification.
Docker socket read-write = host compromise.

---

### 3. Does it require filesystem access?

Does the tool need host filesystem mounts? What paths? Read-only or read-write?

- [ ] **No filesystem access** — safe.
- [ ] **Bounded read-only mount** — document the exact path. Verify no parent
  directory access.
- [ ] **Bounded read-write mount** — document the path. Must be a sandbox or
  buffer vault path, never canonical vault.
- [ ] **Broad filesystem access** — high risk. Re-evaluate necessity.

**Examples:**
- `server-filesystem`: Bounded read-write to allowed directory. Sandbox only.
- `markitdown`: Read-only input mount + write-only buffer output. Capture
  Processor pattern.
- `obsidian-mcp`: Full vault mount. Permanently prohibited.

**Red flags:** Mounts to `/home/lifeos`, `10_Vaults/`, `~/.ssh/`, `~/.config/`,
or any path containing `.env` files.

---

### 4. Does it write to repos?

Does the tool modify git repositories — commit, branch, push, merge?

- [ ] **No git write access** — safe.
- [ ] **Git write within sandbox** — allowed for sandbox experiments only.
  Never against the LifeOS repo.
- [ ] **Git write to production repos** — requires A4 approval. Never via
  MCP without explicit gate.

**Examples:**
- `server-git`: Write-capable by default. Read-only mode required for sandbox.
- `lifeos_services.py`: Git porcelain only (read-only). Safe.

**Red flags:** Git push capability, commit access to LifeOS repos, SSH key
access for git operations.

---

### 5. Does it write to external services?

Does the tool create, modify, or delete data in external services (GitHub API,
Slack, cloud storage, SaaS platforms)?

- [ ] **No external writes** — safe.
- [ ] **Read-only external access** — document the service and scope.
- [ ] **Write to external services** — high risk. Requires A4 approval,
  audit logging, and rollback procedure for every operation.

**Examples:**
- `github-mcp-server`: Can create issues, manage PRs. A4-tier operations.
- `server-fetch`: Read-only HTTP GET. Domain allowlist mitigates risk.

**Red flags:** Cloud storage writes (Azure, S3), messaging platform posts
(Slack, Discord), SaaS API mutations without audit trail.

---

### 6. Does it bind a network port?

Does the tool listen on a TCP/IP port? What interface? What authentication?

- [ ] **No network port** — safe (stdio/pipe transport).
- [ ] **127.0.0.1 only** — localhost-only binding. Safe.
- [ ] **Tailscale IP only** — trusted private network. Requires bearer token.
- [ ] **0.0.0.0 binding** — **prohibited** per MCP Security Policy. Must be
  overridden.

**Examples:**
- `lifeos-status-api`: `127.0.0.1:8787`. Safe.
- `lifeos-capture-api`: Tailscale IP only. Bearer token auth. Safe.
- `mcpo` (default): Can bind `0.0.0.0`. Must override to `127.0.0.1`.

**Red flags:** Default `0.0.0.0` binding, no authentication on HTTP endpoint,
SSE/HTTP streaming transport with network exposure.

---

### 7. Does it use browser automation?

Does the tool spawn a browser, execute JavaScript in pages, or navigate to URLs
using Playwright, Puppeteer, or Selenium?

- [ ] **No browser automation** — safe.
- [ ] **Browser automation** — **permanently prohibited** per MCP Security
  Policy. Even "read-only screenshots" execute JavaScript and can exfiltrate
  data.

**Examples:**
- `playwright-mcp`: Full browser automation. Permanently rejected.
- `n8n HTTP Request node`: HTTP fetch, no browser. Safe with domain restrictions.

**Red flags:** Any browser automation capability. The vendor's own security
disclaimers (e.g., "Playwright MCP is NOT a security boundary") confirm the risk.

---

### 8. Does it execute shell commands?

Does the tool use `subprocess.run`, `os.system`, `eval`, `exec`, or any form of
command execution on the host?

- [ ] **No shell execution** — safe.
- [ ] **Shell execution** — **permanently prohibited** per MCP Security
  Policy. No shell MCP under any circumstances.

**Examples:**
- `lifeos_services.py`: Uses `subprocess` for `docker ps`, `systemctl`,
  `git status` — read-only porcelain commands only. No user-provided arguments.
- `shell-mcp-server`: Arbitrary command execution. Permanently rejected.

**Red flags:** Any tool where user input flows into shell command arguments.
Even path-restricted shell execution can be exploited through prompt injection.

---

### 9. Does it have tests?

Does the tool's own repository have a test suite? What's the coverage? Are
tests passing?

- [ ] **Comprehensive tests** — good signal of maintenance quality.
- [ ] **Some tests** — moderate signal. Review test coverage for critical paths.
- [ ] **No tests** — low signal. Higher risk of bugs, regressions, and
  unvalidated behavior.
- [ ] **Tests failing** — **red flag.** Do not install without understanding
  failures.

**Examples:**
- `modelcontextprotocol/servers`: Reference implementations with varying test
  coverage. Archived servers likely have stale tests.
- LifeOS custom tools: All scripts and APIs have comprehensive test suites
  (411+ tests passing).

**Red flags:** Zero tests, failing CI, last commit fixing something with no
regression test.

---

### 10. Does it have recent maintenance?

When was the last commit? Is the project actively maintained or abandoned?

- [ ] **Active (commits this month)** — maintained. Check for churn (rapid
  changes may indicate instability).
- [ ] **Maintained (commits this quarter)** — acceptable. Review changelog
  for breaking changes.
- [ ] **Slow (commits this year)** — risk of abandonment. Check for open
  issues and PR backlog.
- [ ] **Inactive (no commits > 12 months)** — effectively abandoned. High
  risk of unpatched vulnerabilities. Only install if truly exceptional.
- [ ] **Archived** — explicitly unsupported. Do not install.

**Examples:**
- `modelcontextprotocol/servers`: Multiple archived sub-servers (puppeteer,
  postgres, github, etc.) — maintenance churn.
- `best-of-mcp-servers`: Auto-generated weekly by script. "Active" includes
  auto-generated commits.

**Red flags:** Archived repos, "dead" flags in discovery indexes, last commit
fixing a security vulnerability with no follow-up.

---

### 11. Does it have a clear license?

Is the license OSI-approved? Does it allow the intended LifeOS use?

- [ ] **Clear permissive license** (MIT, Apache 2.0, BSD) — safe.
- [ ] **Clear copyleft license** (GPL, AGPL) — document limitations. AGPL may
  restrict SaaS deployment.
- [ ] **Unclear or missing license** — **do not install.** No license = no
  right to use. Legal risk.
- [ ] **Source-available, non-open-source** (BUSL, SSPL, Elastic License) —
  review for LifeOS use restrictions.

**Examples:**
- `modelcontextprotocol/servers`: MIT license. Safe.
- `playwright-mcp`: Apache 2.0 license. Safe license, but permanently rejected
  on security grounds.

**Red flags:** Missing license file, "all rights reserved" in package.json,
license that restricts private use or self-hosting.

---

### 12. Does it support read-only mode?

Can the tool operate in a mode where it cannot modify data?

- [ ] **Inherently read-only** (e.g., `server-time`) — safest.
- [ ] **Read-only flag/mode available** (e.g., `--read-only`) — verify the
  flag is effective. Test that write operations are blocked.
- [ ] **Read-only configurable** (e.g., permissions, token scope) — harder
  to verify. Test boundaries.
- [ ] **Write-capable only, no read-only mode** — high risk. Requires full
  security review. Sandbox only.

**Examples:**
- `server-git`: Read-only mode available but not default. Must be explicitly
  configured.
- `server-filesystem`: No built-in read-only flag. Relies on OS permissions.
- `qdrant-mcp`: `QDRANT_READ_ONLY=false` by default. Configurable but dangerous.

**Red flags:** "Read-only" flag that doesn't actually block all writes. Tools
that rely on OS permissions for read-only enforcement. Default write-capable
with opt-in read-only.

---

### 13. Can it run in a sandbox?

Can the tool be isolated in a Docker container with bounded mounts, no network
exposure, and no host access?

- [ ] **Trivially sandboxed** — no filesystem, no network, no Docker socket.
  Safe.
- [ ] **Sandboxable with configuration** — requires specific mounts, port
  bindings, or network restrictions. Document the configuration.
- [ ] **Not sandboxable** — requires host-level access, Docker socket, or
  broad filesystem mounts. High risk. Re-evaluate necessity.

**Examples:**
- `server-time`: Trivially sandboxed. No mounts, no network.
- `openhands-sandbox`: Requires Docker socket for sandbox mode — conflicts
  with LifeOS policy.
- `agent-sandbox`: Requires Kubernetes cluster — not sandboxable on LifeOS.

**Red flags:** Tools that require `--privileged`, `--cap-add`, or host network
mode. Tools that spawn child containers. Tools that write to `/var/run/` or
system paths.

---

### 14. Can it be removed cleanly?

What is the removal/rollback procedure? Does it leave behind data, volumes,
cached downloads, persistent state, or configuration files?

- [ ] **Clean removal** — `docker-compose down -v` removes everything.
  No persistent state outside the compose project.
- [ ] **Partial cleanup** — some data persists (cached models, config files,
  token storage). Document what remains and how to clean it.
- [ ] **Messy removal** — significant persistent state. System-level
  configuration changes. Hard to fully remove.

**Examples:**
- `mcpo`: Clean removal. `docker-compose down -v` + delete scaffold files.
- `playwright-mcp`: Messy removal. Persistent browser profiles in
  `~/.cache/ms-playwright/`. Chromium binary download. Config files.
- `qdrant-mcp`: Partial cleanup. Downloaded ML models in
  `~/.cache/huggingface/`. Named volumes with vector data.

**Red flags:** Tools that write to `~/.cache/`, `~/.config/`, `~/.local/`,
or system paths. Tools that modify systemd services, iptables rules, or
Docker daemon configuration. Tools with persistent named volumes containing
user data.

---

## Quick-Scan Summary Table

Use this table for rapid triage of multiple candidates:

| # | Question | Yes = Risk |
|---|----------|-----------|
| 1 | Secrets required? | HIGH |
| 2 | Docker socket required? | CRITICAL (rw) / MEDIUM (ro) |
| 3 | Filesystem access required? | MEDIUM-HIGH |
| 4 | Writes to repos? | HIGH |
| 5 | Writes to external services? | HIGH |
| 6 | Binds network port? | MEDIUM |
| 7 | Browser automation? | CRITICAL |
| 8 | Shell execution? | CRITICAL |
| 9 | Has tests? | LOW (if yes) / MEDIUM (if no) |
| 10 | Recent maintenance? | LOW (if yes) / MEDIUM (if no) |
| 11 | Clear license? | LOW (if yes) / HIGH (if no) |
| 12 | Read-only mode available? | LOW (if yes) / HIGH (if no) |
| 13 | Sandboxable? | LOW (if yes) / HIGH (if no) |
| 14 | Clean removal? | LOW (if yes) / MEDIUM (if no) |

## Applying the Checklist

### To Sandbox Candidates

Candidates approved for sandbox test should score:
- No on questions 1, 2, 7, 8 (secrets, Docker socket, browser, shell)
- Sandboxable (question 13) — ideally "trivially" or "with configuration"
- Clear license (question 11)
- Clean removal (question 14)

Minimum sandbox configuration:
- Docker container with `read_only: true` (if possible)
- `cap_drop: ALL`, `no-new-privileges: true`
- Bounded mounts to sandbox paths only
- `127.0.0.1` port binding only
- No secrets, no Docker socket, no host network

### To Deferred Candidates

Candidates deferred typically fail on:
- Secrets required but API key policy not defined (question 1)
- Infrastructure prerequisites not met (question 13)
- Write-capable with no read-only mode (question 12)
- No clear removal path for risky tools (question 14)

### To Rejected Candidates

Candidates rejected typically fail on:
- Browser automation or shell execution (questions 7, 8) — permanent
- Docker socket write access (question 2) — permanent
- Full vault filesystem access (question 3) — permanent
- Infrastructure mismatch (question 13) — e.g., requires Kubernetes

## Red-Flag Patterns

Watch for these dangerous combinations:

1. **Runtime download + write-capable** — tool downloads untrusted binaries
   (ML models, browsers) at runtime AND can modify data. (e.g., Qdrant MCP)

2. **"Read-only" mode + unverified scope** — tool claims read-only but the
   underlying credential (PAT, API key) has write scope. (e.g., GitHub MCP)

3. **"Sandbox" + Docker socket** — tool claims to be sandboxed but requires
   Docker socket, which breaks container isolation. (e.g., OpenHands sandbox
   mode)

4. **"Proxy" + no access control** — tool routes requests but has no own
   tool-level allowlist. (e.g., mcpo without `--api-key`)

5. **"Library" + MCP wrapper** — library is safe but community MCP wrapper
   adds supply-chain risk. (e.g., MarkItDown MCP wrappers)

6. **Discovery index + quality score** — tool is listed and ranked, but the
   ranking measures GitHub popularity, not LifeOS safety. (e.g.,
   best-of-mcp-servers)

## Cross-References

- [LifeOS Repo Radar](LifeOS_Repo_Radar.md) — full candidate entries
- [LifeOS MCP Catalog](LifeOS_MCP_Catalog.md) — grouped catalog (20 entries)
- [MCP Security Policy](MCP_Security_Policy.md) — deny-by-default, prohibition
  list, mount checklist
- [MCP Roadmap](MCP_Roadmap.md) — V1/V2/V3 tool catalog
- [LifeOS Tool Permission Tiers](LifeOS_Tool_Permission_Tiers.md) — A0-A5
  tier definitions
- [Docker + MCP Service Map](Docker_MCP_Service_Map.md) — current services
  and MCP exposure
