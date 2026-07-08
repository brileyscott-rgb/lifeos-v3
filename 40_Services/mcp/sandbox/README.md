# MCP Sandbox

> Scaffold-only. No MCP servers running, no data exposed.
> The sandbox folder is for testing MCP servers in isolation before production.

## Purpose

The MCP sandbox provides a controlled environment for testing MCP server
integrations without exposing LifeOS production data. Every new MCP tool
must pass through sandbox testing before staging or production.

## Folder Structure

```
40_Services/mcp/sandbox/
├── README.md          # This file
├── test-data/         # Harmless test data for filesystem MCP tests
│   └── readme.json
└── .gitkeep
```

## Sandbox Rules

1. **Mount only this folder.** No test MCP server may mount `10_Vaults/`,
   `30_Capture/`, `50_Event_Log/`, or any other LifeOS data path.
2. **Read-only first.** Test MCP servers must start with read-only access.
3. **No network MCP without explicit test data.** Servers that make network
   calls must have dummy endpoints or domain allowlists.
4. **No secrets.** No real API keys, tokens, or credentials in sandbox tests.
5. **No Docker socket.** No sandbox MCP server may access Docker socket.
6. **localhost-only.** All sandbox MCP servers bind `127.0.0.1` only.
7. **Disposable.** Sandbox data and containers are disposable. Nothing in the
   sandbox should require backup or preservation.

## Test Flow

1. Create harmless test data in `test-data/`.
2. Start MCP server pointed at `test-data/` with read-only mount.
3. Verify tool returns expected data.
4. Verify tool is blocked from reading paths outside the sandbox.
5. Verify tool cannot write to the sandbox (if read-only).
6. Log results.
7. Stop and remove containers.
8. If successful, promote to staging review.

## Files to Ignore

Add to `.gitignore`:
```
40_Services/mcp/sandbox/test-data/
40_Services/mcp/sandbox/*.db
40_Services/mcp/sandbox/*.log
```
