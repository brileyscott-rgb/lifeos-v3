# Temporary Tunnel Proof-of-Concept — Cloudflare Quick Tunnel

## Purpose

Temporary public tunnel proof-of-concept without a Cloudflare-managed domain.
Uses `trycloudflare.com` (Cloudflare Quick Tunnel) to create an ephemeral public URL
that forwards to local n8n webhooks. No credentials, no config, no domain.

## Warning

- This is a **temporary** public URL — do not rely on it.
- **Do not register Telegram webhook** against this URL — it will break when the tunnel stops.
- **Do not expose n8n UI intentionally** — the tunnel forwards the entire n8n service.
- **Do not route Status API or Action API publicly** — they are not part of this test.
- **Stop the tunnel after testing** — Ctrl+C terminates the session.
- Anyone with the temporary URL can reach your n8n instance until the tunnel stops.

## Prerequisites

- [ ] Local n8n running at `http://127.0.0.1:5678` (confirmed: Up)
- [ ] Docker available for running cloudflared
- [ ] Internet access (cloudflared connects outbound to Cloudflare edge)

## Manual n8n Test Workflow

Create a temporary n8n workflow manually in the n8n UI:

1. Open local n8n UI:
   http://127.0.0.1:5678

2. Create a new workflow:
   - Add a **Webhook** node
   - Method: `GET` (or `POST`)
   - Path: `test`
   - Respond: immediately
   - Response body (JSON):
     ```json
     {"ok":true,"source":"lifeos-temporary-tunnel-test"}
     ```

3. **Activate** only this temporary test workflow.

4. Delete or deactivate it after testing.

> **Important:** n8n production webhook path: `/webhook/test`
>
> The temporary public test URL will be:
> `https://<temporary-trycloudflare-url>/webhook/test`

## Quick Tunnel Commands

### Option A — cloudflared installed locally

```bash
cloudflared tunnel --url http://127.0.0.1:5678
```

### Option B — Docker (recommended since cloudflared is not installed)

```bash
docker run --rm --network host cloudflare/cloudflared:latest tunnel --url http://127.0.0.1:5678
```

**Explanation:**
- `--network host` — allows the container to reach n8n at `127.0.0.1:5678` on the host.
- `--rm` — container is removed after exit (no persistent state).
- No volumes mounted, no Docker socket mounted, no credentials used.
- Stop with **Ctrl+C**.
- Cloudflare will print the temporary URL to stdout: `https://<random>.trycloudflare.com`

### Pull the image first if not cached

```bash
docker pull cloudflare/cloudflared:latest
```

## Test Commands

### 1. Test the generic webhook

After cloudflared prints the temporary URL, run:

```bash
curl -i https://<temporary-trycloudflare-url>/webhook/test
```

**Expected:**
- HTTP `200 OK`
- Response body:
  ```json
  {"ok":true,"source":"lifeos-temporary-tunnel-test"}
  ```

### 2. Check root exposure (document only)

```bash
curl -i https://<temporary-trycloudflare-url>/
```

**Expected:**
- Returns n8n UI HTML or login redirect (because Quick Tunnel forwards the entire service).
- This is **acceptable only for this short temporary POC**.
- **Stop the tunnel immediately after testing.**
- **Do not use Quick Tunnel as a production solution.**

## Result Recording

| Check | Result |
|---|---|
| Test date | |
| Public URL reached `/webhook/test` | |
| Root exposed n8n UI/login | |
| Tunnel stopped after test | |
| Next recommendation | |

Do not record the full temporary URL if you consider it sensitive.

## Cleanup

1. **Stop cloudflared** — Ctrl+C in the terminal where it is running.
2. **Deactivate or delete** the temporary n8n test workflow in n8n UI.
3. **Verify** n8n is no longer publicly reachable (the temporary URL is gone).
4. **Verify** local n8n still works at `http://127.0.0.1:5678`.
