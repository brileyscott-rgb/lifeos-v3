# Telegram Review Enablement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Live-validate Telegram review commands (`/view`, `/a`, `/r`) and enable `--allow-review` in the live polling service.

**Architecture:** The Inline Review Button UX V1 is already implemented, offline-tested (96 tests passing), and committed. No code changes are needed. The live polling service is stopped first so `--review-test` can process queued messages without competition. After validation, `--allow-review` is added to the service and restarted. Inline button callbacks are validated in live mode (cannot be tested via `--review-test` as it only handles message updates).

**Tech Stack:** Python 3.12+, systemd user service, Telegram Bot API, Action API.

## Global Constraints

- All mutations route through Action API — no direct filesystem access
- Callback tokens are stateless HMAC, expire after 10 minutes
- Sender authorization enforced on all callbacks
- Cancel button available on all confirmations
- No new environment variables, no new dependencies, no code changes
- Do not break existing capture functionality
- Rollback: remove `--allow-review`, restart service

---

### Task 1: Stop live polling service

The live polling service (3-second interval) would consume test messages before `--review-test` can process them. Stop it first.

- [ ] **Step 1: Stop the Telegram bot service**

```bash
systemctl --user stop lifeos-telegram-bot.service
systemctl --user status lifeos-telegram-bot.service --no-pager -l | head -5
```

Expected: inactive (dead).

- [ ] **Step 2: Send a test capture via Telegram for review testing**

Send `/capture review enablement smoke test` from Telegram mobile. Wait for capture_id confirmation.

- [ ] **Step 3: Send `/p` to queue a pending-list request**

Send `/p` from Telegram mobile. This queues an update; it will not be processed until we run `--review-test`.

### Task 2: Safe `--review-test` validation

`--review-test` only processes `message` updates (not `callback_query`). Inline button taps cannot be validated through this mode — they will be tested live after enablement.

- [ ] **Step 1: Validate `/p` via `--review-test`**

```bash
cd /home/lifeos
python3 40_Services/chatops/telegram/telegram_capture_bot.py --review-test
```

Expected: Fetches the queued `/p` update. Responds with numbered pending list. Outputs processed update to stdout. Exits cleanly.

- [ ] **Step 2: Send `/view 1` and validate**

Send `/view 1` from Telegram mobile, then run:

```bash
python3 40_Services/chatops/telegram/telegram_capture_bot.py --review-test
```

Expected: Returns capture summary with inline buttons [View Full Text] [Approve] [Reject].

- [ ] **Step 3: Confirm validation passed**

If both `/p` and `/view 1` returned expected responses, the Action API is correctly serving review commands. Proceed to enablement.

### Task 3: Enable `--allow-review` in live polling service

- [ ] **Step 1: Verify service is still stopped**

```bash
systemctl --user is-active lifeos-telegram-bot.service
```

Expected: inactive.

- [ ] **Step 2: Read current ExecStart**

```bash
grep ExecStart /home/lifeos/.config/systemd/user/lifeos-telegram-bot.service
```

Expected: `ExecStart=/usr/bin/python3 /home/lifeos/40_Services/chatops/telegram/telegram_capture_bot.py --poll --interval 3`

- [ ] **Step 3: Add `--allow-review` to ExecStart**

```bash
sed -i '/ExecStart/s/--poll --interval 3/--poll --interval 3 --allow-review/' /home/lifeos/.config/systemd/user/lifeos-telegram-bot.service
```

Note: The authoritative service template is at `40_Services/chatops/telegram/systemd/lifeos-telegram-bot.service`. The template stays capture-first as default. Only the runtime copy is updated. If the template is ever re-deployed, `--allow-review` must be re-applied.

- [ ] **Step 4: Verify the edit**

```bash
grep ExecStart /home/lifeos/.config/systemd/user/lifeos-telegram-bot.service
```

Expected: `ExecStart=... --poll --interval 3 --allow-review`

- [ ] **Step 5: Reload systemd and start service**

```bash
systemctl --user daemon-reload
systemctl --user start lifeos-telegram-bot.service
systemctl --user status lifeos-telegram-bot.service --no-pager -l | head -10
```

Expected: active (running). ExecStart shows `--allow-review`.

Note: After restart, any stale callback queries (e.g., button taps from before the stop) still in the update queue will be processed. HMAC expiry (10 minutes) protects against stale mutations. The user may see "Invalid or expired button" messages — this is harmless.

### Task 4: Live verification

- [ ] **Step 1: Verify capture still works**

Send `/capture post-enablement smoke test` from Telegram mobile. Wait for capture_id confirmation and pending_review status. Expected: capture created, event logged, normal reply.

- [ ] **Step 2: Verify review commands work in live polling**

Send `/p` from Telegram mobile. Wait for pending list reply. Then `/view 1` — expect summary with inline buttons.

- [ ] **Step 3: Verify inline button flow (live)**

Tap [View Full Text] — expect full capture content. Tap [Approve] — expect confirmation with [Confirm Approve] [Cancel]. Tap [Cancel] — expect no-op. Then repeat approve flow and tap [Confirm Approve] — expect mutation success with event_id.

- [ ] **Step 4: Run full health check**

```bash
echo "=== Containers ==="
docker ps --no-trunc --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | grep -E 'lifeos|n8n|status|action' || true
echo "=== API health ==="
curl -sS --max-time 5 http://localhost:8787/health
echo
curl -sS --max-time 5 http://localhost:8788/health
echo "=== Telegram service ==="
systemctl --user is-active lifeos-telegram-bot.service
systemctl --user status lifeos-telegram-bot.service --no-pager -l | head -10
echo "=== Port bindings ==="
ss -ltnp | grep -E ':5678|:8787|:8788'
echo "=== Public ingress ==="
docker-compose -f 40_Services/compose/lifeos.yaml config | grep "0.0.0.0" && echo "ERROR" || echo "OK: no 0.0.0.0"
```

- [ ] **Step 5: Run offline tests still pass**

```bash
python3 -m unittest 40_Services/chatops/telegram/tests/test_telegram_bot.py 2>&1 | grep -E "FAIL|ERROR|OK|Ran"
```

Expected: Ran N tests, OK.

### Task 5: Documentation updates

- [ ] **Step 1: Update Current_Working_State.md**

Add entry after the Docker closeout entry:
> **Telegram review commands live-validated and `--allow-review` enabled (2026-07-07)**: Review commands `/p`, `/view`, `/a`, and `/r` were live-validated using `--review-test` mode, then the live polling service was updated with `--allow-review` flag and restarted. Inline review button UX (approve/reject with confirmation, cancel, view full text) is now active in live polling. All mutations route through Action API. Capture functionality unchanged. Status API and Action API remain healthy on unified compose. n8n remains tolerated localhost-only drift.

- [ ] **Step 2: Update `40_Services/chatops/telegram/README.md`**

Update to reflect that `--allow-review` is now active in the live service.

### Task 6: Rollback (only if needed)

If review commands fail in live mode:

- [ ] **Step 1: Stop service**

```bash
systemctl --user stop lifeos-telegram-bot.service
```

- [ ] **Step 2: Remove `--allow-review` from ExecStart**

```bash
sed -i '/ExecStart/s/ --allow-review//' /home/lifeos/.config/systemd/user/lifeos-telegram-bot.service
```

- [ ] **Step 3: Verify the edit**

```bash
grep ExecStart /home/lifeos/.config/systemd/user/lifeos-telegram-bot.service
```

Expected: No `--allow-review` flag.

- [ ] **Step 4: Reload systemd and start service**

```bash
systemctl --user daemon-reload
systemctl --user start lifeos-telegram-bot.service
systemctl --user status lifeos-telegram-bot.service --no-pager -l | head -5
```

Expected: active, no `--allow-review`, capture-first.

- [ ] **Step 5: Verify capture still works**

Send `/capture rollback test` from Telegram. Expected: capture created successfully.
