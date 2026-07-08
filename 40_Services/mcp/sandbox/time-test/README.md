# MCP Time Server Sandbox Test V1

> Sandbox-only. No production MCP activation. No data exposed.

## Test Overview

First LifeOS MCP sandbox test. Validated that the MCP (Model Context Protocol)
stdio protocol works on this system using a read-only time server.

## Test Mode

**Mode A** — Direct stdio MCP server smoke test. No mcpo, no Docker, no network port.

## Package Used

`@guanxiong/mcp-server-time` (community npm package, v1.0.0) — a read-only MCP
server exposing time-related tools. This is NOT the official
`@modelcontextprotocol/server-time` package (which does not exist as an
npm package) or the official Python `mcp-server-time` package (which
requires `uvx` or `pip install`).

The community package was chosen because:
- `uvx` is not installed on this system (official Python invocation unavailable)
- `@modelcontextprotocol/server-time` npm package does not exist (404 from npm registry)
- Global `pip install` is prohibited by LifeOS policy
- `npx -y @guanxiong/mcp-server-time` works ephemerally with no installation

## Safety Profile

| Property | Value |
|----------|-------|
| Read-only | Yes — exposes only time tools |
| Filesystem access | None |
| Network access | None (stdio transport only) |
| Docker socket | None |
| Secrets required | None |
| Browser automation | None |
| Shell execution | None |
| Permanent installation | None (npx ephemeral) |
| Port binding | None (stdio only) |

## Results

See [results.md](results.md) for full test details.

## Next Phase

mcpo sandbox test deferred — no MCP consumer (Open WebUI, AI chat interface)
exists in LifeOS V1. Custom LifeOS MCP server (`lifeos.status`) is the
recommended next MCP milestone after an MCP client is configured.
