# Telegram Review Button UX V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add inline keyboard buttons to the Telegram review flow so users can approve/reject pending captures without typing command text.

**Architecture:** Stateless HMAC callback tokens embedded in inline keyboard `callback_data` (max 64 bytes). A new `process_callback_query` handler dispatches button taps through auth, review-mode, and token verification gates. All mutations route through the existing Action API. No new runtime state, no new env vars, no new services.

**Tech Stack:** Python 3.12+, stdlib `hashlib`/`hmac` for tokens, stdlib `unittest.mock` for offline tests. Existing Action API endpoints (`GET /captures/pending`, `POST /captures/<id>/approve`, `POST /captures/<id>/reject`) unchanged.

## Global Constraints

- No new environment variables (HMAC key derived from `BOT_TOKEN` via SHA256).
- All tokens are stateless — no runtime storage, no database, no Redis.
- All callback tokens expire after 600 seconds (10 minutes).
- `callback_data` MUST stay under Telegram's 64-byte limit.
- All test files use `unittest.mock.patch` — never connect to live Telegram or Action API.
- No new Python dependencies beyond stdlib.
- No changes to Action API, Status API, Docker, n8n, Cloudflare, or any other service.
- No direct filesystem access in callback handlers — all mutations through Action API.
- Every callback path calls `answerCallbackQuery` exactly once.

---
### Task 1: Stateless Callback Token Helpers and Tests

**Files:**
- Modify: `40_Services/chatops/telegram/telegram_capture_bot.py` (add `hashlib`/`hmac` imports + token functions + `_make_cap_ref`)
- Modify: `40_Services/chatops/telegram/tests/test_telegram_bot.py` (add token test class)

**Interfaces:**
- Consumes: `BOT_TOKEN` (global), `hashlib`, `hmac`, `time` (stdlib)
- Produces:
  - `TOKEN_VERSION = "rv1"`
  - `TOKEN_TTL = 600`
  - `MAC_TRUNC = 12`
  - `ALL_ACTIONS = ("v", "a", "r", "ca", "cr", "n")`
  - `_hmac_key() -> bytes`
  - `_make_cap_ref(capture_id: str) -> str`
  - `_make_token(action: str, sender_id: int, cap_ref: str) -> str`
  - `_verify_token(callback_sender_id: int, callback_data: str) -> dict | None`

- [ ] **Step 1: Write the failing tests**

  To file `40_Services/chatops/telegram/tests/test_telegram_bot.py`, add:

  ```python
  class TestCallbackTokenHelpers(unittest.TestCase):
      """Offline token generation and verification tests."""

      TOKEN_TTL = 600

      def setUp(self):
          self.sender_id = 12345
          self.capture_id = "cap_20260707_120000_a1b2c3"
          self.cap_ref = "a1b2c3d4e5f6"   # first 12 hex of SHA256(capture_id)
          self.action = "a"
          # Fixed HMAC key for deterministic test output
          self.patcher = patch.object(bot, 'BOT_TOKEN', "test_token_12345")
          self.patcher.start()

      def tearDown(self):
          self.patcher.stop()

      def test_make_cap_ref_is_first_12_hex_chars(self):
          ref = bot._make_cap_ref(self.capture_id)
          self.assertEqual(len(ref), 12)
          self.assertTrue(all(c in "0123456789abcdef" for c in ref))

      def test_make_cap_ref_is_deterministic(self):
          self.assertEqual(
              bot._make_cap_ref(self.capture_id),
              bot._make_cap_ref(self.capture_id),
          )

      def test_make_cap_ref_differs_for_different_ids(self):
          ref2 = bot._make_cap_ref("cap_other")
          self.assertNotEqual(bot._make_cap_ref(self.capture_id), ref2)

      def test_token_format_has_5_parts(self):
          cap_ref = bot._make_cap_ref(self.capture_id)
          token = bot._make_token(self.action, self.sender_id, cap_ref)
          parts = token.split("|")
          self.assertEqual(len(parts), 5)

      def test_token_starts_with_version(self):
          cap_ref = bot._make_cap_ref(self.capture_id)
          token = bot._make_token(self.action, self.sender_id, cap_ref)
          self.assertTrue(token.startswith("rv1|"))

      def test_token_contains_action_and_cap_ref(self):
          cap_ref = bot._make_cap_ref(self.capture_id)
          token = bot._make_token(self.action, self.sender_id, cap_ref)
          self.assertIn(f"|{self.action}|{cap_ref}|", token)

      def test_token_under_64_bytes(self):
          cap_ref = bot._make_cap_ref(self.capture_id)
          for act in ("v", "a", "r", "ca", "cr", "n"):
              token = bot._make_token(act, self.sender_id, cap_ref)
              self.assertLessEqual(len(token), 64, f"token for action {act} exceeds 64 bytes")

      def test_verify_token_valid(self):
          cap_ref = bot._make_cap_ref(self.capture_id)
          token = bot._make_token(self.action, self.sender_id, cap_ref)
          result = bot._verify_token(self.sender_id, token)
          self.assertIsNotNone(result)
          self.assertEqual(result["action"], self.action)
          self.assertEqual(result["cap_ref"], cap_ref)

      def test_verify_token_rejects_wrong_sender(self):
          cap_ref = bot._make_cap_ref(self.capture_id)
          token = bot._make_token(self.action, self.sender_id, cap_ref)
          result = bot._verify_token(99999, token)
          self.assertIsNone(result)

      def test_verify_token_rejects_malformed_parts(self):
          result = bot._verify_token(self.sender_id, "bad|data")
          self.assertIsNone(result)

      def test_verify_token_rejects_wrong_version(self):
          result = bot._verify_token(self.sender_id, "badver|a|caf|690f2a10|deadbeef")
          self.assertIsNone(result)

      def test_verify_token_rejects_unknown_action(self):
          cap_ref = bot._make_cap_ref(self.capture_id)
          # Build a token-like string with an invalid action
          exp_hex = format(int(time.time()) + 600, "x")
          payload = f"rv1|x|{self.sender_id}|{cap_ref}|{exp_hex}"
          key = hashlib.sha256(b"test_token_12345").digest()
          mac = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()[:12]
          token = f"rv1|x|{cap_ref}|{exp_hex}|{mac}"
          result = bot._verify_token(self.sender_id, token)
          self.assertIsNone(result)

      def test_verify_token_action_bound(self):
          """Token for action 'a' fails verification when checked as action 'r'."""
          cap_ref = bot._make_cap_ref(self.capture_id)
          token_a = bot._make_token("a", self.sender_id, cap_ref)
          # Verification reconstructs payload using the same action from token — so this
          # test verifies the action is embedded in the MAC and cannot be swapped.
          # A token created for 'a' has action 'a' in its visible data, so verify_token
          # uses token's own action field from the visible data. If someone modifies the
          # visible action char, MAC will mismatch.
          parts = token_a.split("|")
          tampered = f"rv1|r|{parts[2]}|{parts[3]}|{parts[4]}"
          result = bot._verify_token(self.sender_id, tampered)
          self.assertIsNone(result)

      def test_verify_token_rejects_expired_token(self):
          cap_ref = bot._make_cap_ref(self.capture_id)
          # Manually create an expired token
          exp_hex = format(int(time.time()) - 1, "x")
          payload = f"rv1|{self.action}|{self.sender_id}|{cap_ref}|{exp_hex}"
          key = hashlib.sha256(b"test_token_12345").digest()
          mac = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()[:12]
          token = f"rv1|{self.action}|{cap_ref}|{exp_hex}|{mac}"
          result = bot._verify_token(self.sender_id, token)
          self.assertIsNone(result)
  ```

- [ ] **Step 2: Run tests to verify they fail**

  Run: `python3 -m unittest 40_Services/chatops/telegram/tests/test_telegram_bot.py -v`
  Expected: `FAIL` / `ERROR` — token functions not yet defined

- [ ] **Step 3: Add imports + token helper functions to telegram_capture_bot.py**

  Add to top-level imports:
  ```python
  import hashlib
  import hmac
  ```

  Add after `ALLOW_REVIEW_COMMANDS = False`:
  ```python
  # --- Callback token constants ---
  TOKEN_VERSION = "rv1"
  TOKEN_TTL = 600       # 10 minutes
  MAC_TRUNC = 12        # hex chars
  ALL_ACTIONS = ("v", "a", "r", "ca", "cr", "n")
  ```

  Add after `call_action_api`:
  ```python
  def _hmac_key():
      return hashlib.sha256(BOT_TOKEN.encode("utf-8")).digest()


  def _make_cap_ref(capture_id):
      return hashlib.sha256(capture_id.encode("utf-8")).hexdigest()[:12]


  def _make_token(action, sender_id, cap_ref):
      exp_ts = int(time.time()) + TOKEN_TTL
      exp_hex = format(exp_ts, "x")
      payload = f"{TOKEN_VERSION}|{action}|{sender_id}|{cap_ref}|{exp_hex}"
      key = _hmac_key()
      mac = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:MAC_TRUNC]
      return f"{TOKEN_VERSION}|{action}|{cap_ref}|{exp_hex}|{mac}"


  def _verify_token(callback_sender_id, callback_data):
      parts = callback_data.split("|")
      if len(parts) != 5:
          return None
      version, action, cap_ref, exp_hex, mac = parts

      if version != TOKEN_VERSION:
          return None
      if action not in ALL_ACTIONS:
          return None

      try:
          exp_ts = int(exp_hex, 16)
      except ValueError:
          return None
      if time.time() > exp_ts:
          return None

      payload = f"{version}|{action}|{callback_sender_id}|{cap_ref}|{exp_hex}"
      key = _hmac_key()
      expected = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:MAC_TRUNC]
      if not hmac.compare_digest(mac, expected):
          return None

      return {"action": action, "cap_ref": cap_ref, "version": version}
  ```

- [ ] **Step 4: Run tests to verify they pass**

  Run: `python3 -m unittest 40_Services/chatops/telegram/tests/test_telegram_bot.py -v`
  Expected: all `TestCallbackTokenHelpers` tests PASS

- [ ] **Step 5: Commit**

  ```bash
  git add 40_Services/chatops/telegram/telegram_capture_bot.py
  git add 40_Services/chatops/telegram/tests/test_telegram_bot.py
  git commit -m "feat: add stateless callback token helpers with offline tests"
  ```

  Verify: `git status --short` shows clean

---
### Task 2: Callback Query Dispatch and Safety Guards

**Files:**
- Modify: `40_Services/chatops/telegram/telegram_capture_bot.py` (add `process_callback_query`, `_handle_cancel`, update `process_update`)
- Modify: `40_Services/chatops/telegram/tests/test_telegram_bot.py` (add callback dispatch + safety tests)
- Modify: `40_Services/chatops/telegram/tests/test_telegram_bot_boundaries.py` (add boundary tests for callback handler safety)

**Interfaces:**
- Consumes: `_verify_token`, `ALLOW_REVIEW_COMMANDS`, `tg_api`, `is_authorized_sender`
- Produces:
  - `process_callback_query(update: dict) -> None`
  - `_handle_cancel(chat_id: int, msg_id: int) -> None`
  - `_resolve_cap_ref(cap_ref: str) -> tuple[str | None, str | None]` — returns `(capture_id | None, error_text | None)`

  Handler stubs (implemented in later tasks):
  - `_handle_view_full(chat_id, cap_ref)` — stub that logs and returns
  - `_handle_approve_intent(chat_id, msg_id, sender_id, cap_ref)` — stub
  - `_handle_reject_intent(chat_id, msg_id, sender_id, cap_ref)` — stub
  - `_handle_confirm_approve(chat_id, msg_id, sender_id, cap_ref)` — stub
  - `_handle_confirm_reject(chat_id, msg_id, sender_id, cap_ref)` — stub

- [ ] **Step 1: Write the failing tests**

  Add to `test_telegram_bot.py`:

  ```python
  class TestCallbackQueryDispatch(unittest.TestCase):
      """Callback query handler dispatch and safety gates."""

      def make_callback_update(self, callback_data, sender_id=AUTHORIZED_SENDER, chat_id=CHAT_ID, msg_id=100):
          return {
              "update_id": 2,
              "callback_query": {
                  "id": "cb_test_1",
                  "from": {"id": sender_id, "first_name": "TestUser"},
                  "message": {
                      "message_id": msg_id,
                      "chat": {"id": chat_id},
                  },
                  "data": callback_data,
              }
          }

      def make_valid_token(self, action, sender_id=AUTHORIZED_SENDER):
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              cap_ref = bot._make_cap_ref("cap_test_123")
              return bot._make_token(action, sender_id, cap_ref)

      @patch.object(bot, 'tg_api')
      def test_unauthorized_callback_answers_and_returns(self, mock_tg):
          cb_data = self.make_valid_token("n")
          update = self.make_callback_update(cb_data, sender_id=UNAUTHORIZED_SENDER)
          with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
              bot.process_callback_query(update)
          mock_tg.assert_called_once_with("answerCallbackQuery", {"callback_query_id": "cb_test_1"})

      @patch.object(bot, 'tg_api')
      def test_review_disabled_answers_with_text_and_returns(self, mock_tg):
          cb_data = self.make_valid_token("n")
          update = self.make_callback_update(cb_data)
          bot.ALLOW_REVIEW_COMMANDS = False
          with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
              bot.process_callback_query(update)
          mock_tg.assert_called_once_with("answerCallbackQuery", {
              "callback_query_id": "cb_test_1",
              "text": "Review mode is disabled. Please /p to refresh."
          })

      @patch.object(bot, 'tg_api')
      def test_invalid_token_answers_with_text_and_returns(self, mock_tg):
          update = self.make_callback_update("invalid|data|here|too|short")
          bot.ALLOW_REVIEW_COMMANDS = True
          with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
              bot.process_callback_query(update)
          mock_tg.assert_called_once_with("answerCallbackQuery", {
              "callback_query_id": "cb_test_1",
              "text": "Invalid or expired button. Please /p to refresh."
          })

      @patch.object(bot, 'tg_api')
      def test_cancel_action_answers_no_text_and_handles(self, mock_tg):
          cb_data = self.make_valid_token("n")
          update = self.make_callback_update(cb_data)
          bot.ALLOW_REVIEW_COMMANDS = True
          with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
              with patch.object(bot, '_handle_cancel') as mock_cancel:
                  bot.process_callback_query(update)
                  mock_cancel.assert_called_once_with(CHAT_ID, 100)
                  # answerCallbackQuery called once with no text (success path)
                  mock_tg.assert_called_once_with("answerCallbackQuery", {"callback_query_id": "cb_test_1"})

      @patch.object(bot, 'tg_api')
      def test_success_path_answers_once_no_text(self, mock_tg):
          """Valid token + review enabled = answerCallbackQuery called once with no text."""
          cb_data = self.make_valid_token("n")
          update = self.make_callback_update(cb_data)
          bot.ALLOW_REVIEW_COMMANDS = True
          with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
              with patch.object(bot, '_handle_cancel'):
                  bot.process_callback_query(update)
          self.assertEqual(mock_tg.call_count, 1)
          args = mock_tg.call_args[0]
          self.assertEqual(args[0], "answerCallbackQuery")
          # No text in the success answer
          self.assertNotIn("text", args[1])

      @patch.object(bot, 'tg_api')
      def test_process_update_dispatches_callback_query(self, mock_tg):
          """process_update routes callback_query updates to process_callback_query."""
          cb_data = self.make_valid_token("n")
          update = self.make_callback_update(cb_data)
          bot.ALLOW_REVIEW_COMMANDS = True
          with patch.object(bot, 'ALLOWED_USER_ID', AUTHORIZED_SENDER):
              with patch.object(bot, 'process_callback_query') as mock_dispatch:
                  bot.process_update(update)
                  mock_dispatch.assert_called_once_with(update)
  ```

  Add to `test_telegram_bot_boundaries.py`:

  ```python
  class TestCallbackBoundaries(unittest.TestCase):
      def make_callback_update(self, callback_data, sender_id=AUTHORIZED_SENDER):
          return {
              "update_id": 2,
              "callback_query": {
                  "id": "cb_test_1",
                  "from": {"id": sender_id, "first_name": "TestUser"},
                  "message": {
                      "message_id": 100,
                      "chat": {"id": CHAT_ID},
                  },
                  "data": callback_data,
              }
          }

      def test_callback_handler_does_not_contain_filesystem_ops(self):
          source = inspect.getsource(bot.process_callback_query)
          forbidden = [
              "open(", "os.rename", "shutil.move", "CAPTURE_DIR",
              "PENDING_DIR", "APPROVED_DIR", "REJECTED_DIR",
          ]
          for token in forbidden:
              with self.subTest(token=token):
                  self.assertNotIn(token, source)

      @patch.object(bot, 'tg_api')
      def test_cancel_handler_uses_editMessageReplyMarkup(self, mock_tg):
          bot._handle_cancel(CHAT_ID, 100)
          mock_tg.assert_called_once_with("editMessageReplyMarkup", {
              "chat_id": CHAT_ID,
              "message_id": 100,
              "reply_markup": {"inline_keyboard": []},
          })
  ```

- [ ] **Step 2: Run tests to verify they fail**

  Run: `python3 -m unittest discover -s 40_Services/chatops/telegram/tests -v`
  Expected: FAIL — `process_callback_query`, `_handle_cancel` not defined; `process_update` not dispatching callback queries

- [ ] **Step 3: Add callback handler, cancel handler, update process_update**

  In `telegram_capture_bot.py`, add before `process_update`:

  ```python
  def _resolve_cap_ref(cap_ref):
      """Resolve cap_ref to capture_id via GET /captures/pending.
      Returns (capture_id | None, error_text | None).
      """
      result = call_action_api("/captures/pending")
      if result is None or not result.get("success"):
          return None, "Capture list unavailable."
      pending = result.get("pending", [])
      matches = []
      for item in pending:
          cid = item.get("capture_id", "")
          if _make_cap_ref(cid) == cap_ref:
              matches.append(cid)
      if len(matches) == 0:
          return None, "Capture no longer pending. Please /p to refresh."
      if len(matches) > 1:
          return None, "Ambiguous capture reference. Please /p to refresh."
      return matches[0], None


  def _handle_cancel(chat_id, msg_id):
      tg_api("editMessageReplyMarkup", {
          "chat_id": chat_id,
          "message_id": msg_id,
          "reply_markup": {"inline_keyboard": []},
      })


  def process_callback_query(update):
      cb = update.get("callback_query", {})
      sender_id = cb.get("from", {}).get("id")
      chat_id = cb.get("message", {}).get("chat", {}).get("id")
      msg_id = cb.get("message", {}).get("message_id")
      callback_data = cb.get("data", "")
      cb_id = cb.get("id")

      # 1. Authorization gate
      if not is_authorized_sender(sender_id):
          tg_api("answerCallbackQuery", {"callback_query_id": cb_id})
          return

      # 2. Review-mode guard — protects against stale buttons
      if not ALLOW_REVIEW_COMMANDS:
          tg_api("answerCallbackQuery", {
              "callback_query_id": cb_id,
              "text": "Review mode is disabled. Please /p to refresh.",
          })
          return

      # 3. Token verification (expiry, sender mismatch, etc.)
      token = _verify_token(sender_id, callback_data)
      if token is None:
          tg_api("answerCallbackQuery", {
              "callback_query_id": cb_id,
              "text": "Invalid or expired button. Please /p to refresh.",
          })
          return

      # 4. Answer the callback (no text) to stop the loading spinner.
      tg_api("answerCallbackQuery", {"callback_query_id": cb_id})

      action = token["action"]
      cap_ref = token["cap_ref"]

      if action == "n":
          _handle_cancel(chat_id, msg_id)
      elif action == "v":
          _handle_view_full(chat_id, cap_ref)
      elif action == "a":
          _handle_approve_intent(chat_id, msg_id, sender_id, cap_ref)
      elif action == "r":
          _handle_reject_intent(chat_id, msg_id, sender_id, cap_ref)
      elif action == "ca":
          _handle_confirm_approve(chat_id, msg_id, sender_id, cap_ref)
      elif action == "cr":
          _handle_confirm_reject(chat_id, msg_id, sender_id, cap_ref)
  ```

  Add stub handlers (placeholders filled in Tasks 3-4):
  ```python
  def _handle_view_full(chat_id, cap_ref):
      pass


  def _handle_approve_intent(chat_id, msg_id, sender_id, cap_ref):
      pass


  def _handle_reject_intent(chat_id, msg_id, sender_id, cap_ref):
      pass


  def _handle_confirm_approve(chat_id, msg_id, sender_id, cap_ref):
      pass


  def _handle_confirm_reject(chat_id, msg_id, sender_id, cap_ref):
      pass
  ```

  In `process_update`, add callback query dispatch at the top of the function (before message extraction):

  Replace:
  ```python
  def process_update(update):
      sender_id, chat_id = extract_sender_id(update)
      if sender_id is None or chat_id is None:
          return

      if not is_authorized_sender(sender_id):
          print("Unauthorized sender rejected")
          reject_unauthorized(chat_id)
          return

      msg = update.get('message', {})
      text = msg.get('text', '')
  ```

  With:
  ```python
  def process_update(update):
      # Callback queries are dispatched before message commands
      if "callback_query" in update:
          process_callback_query(update)
          return

      sender_id, chat_id = extract_sender_id(update)
      if sender_id is None or chat_id is None:
          return

      if not is_authorized_sender(sender_id):
          print("Unauthorized sender rejected")
          reject_unauthorized(chat_id)
          return

      msg = update.get('message', {})
      text = msg.get('text', '')
  ```

- [ ] **Step 4: Run tests to verify they pass**

  Run: `python3 -m unittest discover -s 40_Services/chatops/telegram/tests -v`
  Expected: all callback dispatch + safety tests PASS; existing tests still PASS

- [ ] **Step 5: Commit**

  ```bash
  git add 40_Services/chatops/telegram/telegram_capture_bot.py
  git add 40_Services/chatops/telegram/tests/test_telegram_bot.py
  git add 40_Services/chatops/telegram/tests/test_telegram_bot_boundaries.py
  git commit -m "feat: add callback query dispatch with auth, review guard, and cancel handler"
  ```

  Verify: `git status --short` shows clean

---
### Task 3: /view Summary + Buttons and View-Full Flow

**Files:**
- Modify: `40_Services/chatops/telegram/telegram_capture_bot.py` (modify `handle_view`, implement `_handle_view_full`, add inline keyboard helpers)
- Modify: `40_Services/chatops/telegram/tests/test_telegram_bot.py` (add summary + buttons + view-full tests)

**Interfaces:**
- Consumes: `_make_token`, `_make_cap_ref`, `_resolve_cap_ref`, `tg_api`, `call_action_api`
- Produces:
  - Modified `handle_view(text, chat_id)` — sends summary + inline keyboard instead of full content
  - `_handle_view_full(chat_id, cap_ref)` — resolves cap_ref and sends full content as new message
  - `_make_summary_keyboard(capture, sender_id) -> dict` — builds inline keyboard markup

- [ ] **Step 1: Write the failing tests**

  Add to `test_telegram_bot.py`:

  ```python
  class TestViewSummaryAndButtons(unittest.TestCase):
      """Modified /view sends summary + inline keyboard with tokens."""

      SAMPLE_CAPTURE = {
          "capture_id": "cap_20260707_120000_a1b2c3_slug",
          "status": "pending_review",
          "created_at": "2026-07-07T12:00:00Z",
          "content": "My quick note about something important.\n\nSecond line.",
      }

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_view_sends_summary_instead_of_full_content(self, mock_tg, mock_api):
          mock_api.return_value = {"success": True, "capture": self.SAMPLE_CAPTURE}
          bot.handle_view("/view 1", CHAT_ID)
          mock_tg.assert_called_once()
          text = mock_tg.call_args[0][1]["text"]
          # Should contain summary fields but NOT full content body
          self.assertIn("Capture: cap_20260707_120000_a1b2c3_slug", text)
          self.assertIn("Status: pending_review", text)
          self.assertIn("Created: 2026-07-07T12:00:00Z", text)
          # Should contain preview line
          self.assertIn("My quick note about something important.", text)
          # Should NOT contain full second line
          self.assertNotIn("Second line.", text)

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_view_includes_inline_keyboard(self, mock_tg, mock_api):
          mock_api.return_value = {"success": True, "capture": self.SAMPLE_CAPTURE}
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              bot.handle_view("/view 1", CHAT_ID)
          args = mock_tg.call_args[0]
          self.assertEqual(args[0], "sendMessage")
          payload = args[1]
          self.assertIn("reply_markup", payload)
          kb = payload["reply_markup"]
          self.assertIn("inline_keyboard", kb)
          buttons = kb["inline_keyboard"]
          # Should have 2 rows: [View Full Text], [Approve] [Reject]
          self.assertEqual(len(buttons), 2)
          self.assertEqual(len(buttons[0]), 1)  # View Full Text
          self.assertEqual(len(buttons[1]), 2)  # Approve + Reject
          self.assertEqual(buttons[0][0]["text"], "View Full Text")
          self.assertEqual(buttons[1][0]["text"], "Approve")
          self.assertEqual(buttons[1][1]["text"], "Reject")

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_view_keyboard_has_callback_data(self, mock_tg, mock_api):
          mock_api.return_value = {"success": True, "capture": self.SAMPLE_CAPTURE}
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              bot.handle_view("/view 1", CHAT_ID)
          payload = mock_tg.call_args[0][1]
          buttons = payload["reply_markup"]["inline_keyboard"]
          # All buttons should have callback_data
          for row in buttons:
              for btn in row:
                  self.assertIn("callback_data", btn)
                  data = btn["callback_data"]
                  self.assertGreater(len(data), 0)
                  self.assertLessEqual(len(data), 64)

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_view_keyboard_action_chars(self, mock_tg, mock_api):
          mock_api.return_value = {"success": True, "capture": self.SAMPLE_CAPTURE}
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              bot.handle_view("/view 1", CHAT_ID)
          payload = mock_tg.call_args[0][1]
          buttons = payload["reply_markup"]["inline_keyboard"]
          # View Full Text should have action 'v'
          v_data = buttons[0][0]["callback_data"]
          self.assertTrue(v_data.startswith("rv1|v|"))
          # Approve should have action 'a'
          a_data = buttons[1][0]["callback_data"]
          self.assertTrue(a_data.startswith("rv1|a|"))
          # Reject should have action 'r'
          r_data = buttons[1][1]["callback_data"]
          self.assertTrue(r_data.startswith("rv1|r|"))

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_view_full_resolves_and_sends_content(self, mock_tg, mock_api):
          """_handle_view_full resolves cap_ref and sends full content as new message."""
          cap_ref = bot._make_cap_ref("cap_test_123")
          mock_api.side_effect = [
              # First call for _resolve_cap_ref: GET /captures/pending
              {"success": True, "pending": [
                  {"capture_id": "cap_test_123", "index": 1, "status": "pending_review", "created_at": "", "preview": ""},
              ], "count": 1},
              # Second call for full capture data
              {"success": True, "capture": {
                  "capture_id": "cap_test_123",
                  "status": "pending_review",
                  "created_at": "2026-07-07T12:00:00Z",
                  "content": "Full content line 1.\nLine 2.\nLine 3.",
              }},
          ]
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              bot._handle_view_full(CHAT_ID, cap_ref)
          self.assertEqual(mock_tg.call_count, 1)
          text = mock_tg.call_args[0][1]["text"]
          self.assertIn("Full content line 1.", text)
          self.assertIn("Line 2.", text)
          self.assertIn("Line 3.", text)
          # Should NOT have approve/reject buttons
          payload = mock_tg.call_args[0][1]
          self.assertNotIn("reply_markup", payload)

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_view_full_no_matches_sends_error(self, mock_tg, mock_api):
          cap_ref = bot._make_cap_ref("nonexistent")
          mock_api.return_value = {"success": True, "pending": [], "count": 0}
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              bot._handle_view_full(CHAT_ID, cap_ref)
          mock_tg.assert_called_once()
          text = mock_tg.call_args[0][1]["text"]
          self.assertIn("no longer pending", text)

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_view_truncates_preview_line(self, mock_tg, mock_api):
          long_text = "A" * 200
          mock_api.return_value = {"success": True, "capture": {
              "capture_id": "cap_long",
              "status": "pending_review",
              "created_at": "2026-07-07T12:00:00Z",
              "content": long_text,
          }}
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              bot.handle_view("/view 1", CHAT_ID)
          text = mock_tg.call_args[0][1]["text"]
          # Preview should not contain the full 200-char line — it will be truncated
          self.assertLessEqual(len(text.split("\n")[-1]) if "\n" in text else len(text), 130)
  ```

- [ ] **Step 2: Run tests to verify they fail**

  Run: `python3 -m unittest 40_Services/chatops/telegram/tests/test_telegram_bot.py -v`
  Expected: FAIL — `handle_view` still sends full content, `_handle_view_full` is a no-op stub

- [ ] **Step 3: Modify handle_view + implement _handle_view_full**

  Replace existing `handle_view`:
  ```python
  def handle_view(text, chat_id):
      parts = text.strip().split(maxsplit=1)
      if len(parts) < 2 or not parts[1].strip():
          tg_api("sendMessage", {"chat_id": chat_id, "text": "Usage: /view <number> or /view latest or /view <capture_id>"})
          return
      ref = parts[1].strip()
      if ref == "latest":
          endpoint = "/captures/pending/latest"
      elif ref.isdigit():
          endpoint = f"/captures/pending/{ref}"
      elif ref.startswith("cap_"):
          endpoint = f"/captures/{ref}"
      else:
          tg_api("sendMessage", {"chat_id": chat_id, "text": "Invalid argument. Use a number, \"latest\", or a capture_id."})
          return
      result = call_action_api(endpoint)
      if result is None or not result.get("success"):
          tg_api("sendMessage", {"chat_id": chat_id, "text": "Capture not found or unavailable. No action was taken."})
          return

      capture = result["capture"]
      cid = capture.get("capture_id", "")
      ctype = capture.get("status", "")
      created = capture.get("created_at", "")
      content = capture.get("content", "")

      # Build summary (first non-empty content line, truncated to 120 chars)
      preview = _extract_preview_line(content)[:120]

      summary = (
          f"Capture: {cid}\n"
          f"Status: {ctype}\n"
          f"Created: {created}\n"
          f"Preview: {preview}"
      )

      # Generate tokens for view-full, approve-intent, reject-intent
      cap_ref = _make_cap_ref(cid)
      token_v = _make_token("v", ALLOWED_USER_ID, cap_ref)
      token_a = _make_token("a", ALLOWED_USER_ID, cap_ref)
      token_r = _make_token("r", ALLOWED_USER_ID, cap_ref)

      inline_kb = {
          "inline_keyboard": [
              [{"text": "View Full Text", "callback_data": token_v}],
              [
                  {"text": "Approve", "callback_data": token_a},
                  {"text": "Reject", "callback_data": token_r},
              ],
          ]
      }

      tg_api("sendMessage", {
          "chat_id": chat_id,
          "text": summary,
          "reply_markup": inline_kb,
      })
  ```

  Replace `_handle_view_full` stub:
  ```python
  def _handle_view_full(chat_id, cap_ref):
      capture_id, error = _resolve_cap_ref(cap_ref)
      if capture_id is None:
          tg_api("sendMessage", {"chat_id": chat_id, "text": error})
          return

      result = call_action_api(f"/captures/{capture_id}")
      if result is None or not result.get("success"):
          tg_api("sendMessage", {
              "chat_id": chat_id,
              "text": "Capture not found or unavailable. No action was taken.",
          })
          return

      capture = result["capture"]
      content = capture.get("content", "")
      max_len = 3500
      if len(content) > max_len:
          content = content[:max_len] + "\n... (truncated)"

      tg_api("sendMessage", {"chat_id": chat_id, "text": content})
  ```

- [ ] **Step 4: Run tests to verify they pass**

  Run: `python3 -m unittest 40_Services/chatops/telegram/tests/test_telegram_bot.py -v`
  Expected: all `TestViewSummaryAndButtons` tests PASS; existing tests still PASS

- [ ] **Step 5: Run full test suite**

  Run: `python3 -m unittest discover -s 40_Services/chatops/telegram/tests -v`
  Expected: all tests PASS

- [ ] **Step 6: Commit**

  ```bash
  git add 40_Services/chatops/telegram/telegram_capture_bot.py
  git add 40_Services/chatops/telegram/tests/test_telegram_bot.py
  git commit -m "feat: add /view summary buttons and view-full flow"
  ```

---
### Task 4: Approve/Reject Confirmation and Mutation Flow

**Files:**
- Modify: `40_Services/chatops/telegram/telegram_capture_bot.py` (implement `_handle_approve_intent`, `_handle_reject_intent`, `_handle_confirm_approve`, `_handle_confirm_reject`)
- Modify: `40_Services/chatops/telegram/tests/test_telegram_bot.py` (add intent + confirm flow tests)

**Interfaces:**
- Consumes: `_resolve_cap_ref`, `_make_token`, `_make_cap_ref`, `call_action_api`, `tg_api`, `ALLOWED_USER_ID`
- Produces: Full approve/reject confirmation and mutation flow

- [ ] **Step 1: Write the failing tests**

  Add to `test_telegram_bot.py`:

  ```python
  class TestIntentAndConfirmFlows(unittest.TestCase):
      """Approve/reject intent shows confirmation; confirm calls Action API."""

      def setUp(self):
          self.sender_id = AUTHORIZED_SENDER
          self.cap_ref = bot._make_cap_ref("cap_test_123")
          self.chat_id = CHAT_ID
          self.msg_id = 100
          self.pending_list = {
              "success": True,
              "pending": [
                  {"capture_id": "cap_test_123", "index": 1, "status": "pending_review",
                   "created_at": "2026-07-07T12:00:00Z", "preview": "Test capture content"},
              ],
              "count": 1,
          }

      # --- Approve Intent ---

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_approve_intent_shows_confirmation_and_generates_tokens(self, mock_tg, mock_api):
          mock_api.return_value = self.pending_list
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  bot._handle_approve_intent(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)

          # Should edit the original message
          mock_tg.assert_called_once()
          args = mock_tg.call_args[0]
          self.assertEqual(args[0], "editMessageText")
          payload = args[1]
          self.assertEqual(payload["chat_id"], self.chat_id)
          self.assertEqual(payload["message_id"], self.msg_id)
          self.assertIn("Confirm approval?", payload["text"])
          self.assertIn("cap_test_123", payload["text"])

          # Should have Confirm Approve + Cancel buttons
          kb = payload["reply_markup"]["inline_keyboard"]
          self.assertEqual(len(kb), 1)
          self.assertEqual(len(kb[0]), 2)
          self.assertEqual(kb[0][0]["text"], "Confirm Approve")
          self.assertEqual(kb[0][1]["text"], "Cancel")
          # Callback data should be 'ca' and 'n' tokens
          self.assertTrue(kb[0][0]["callback_data"].startswith("rv1|ca|"))
          self.assertTrue(kb[0][1]["callback_data"].startswith("rv1|n|"))

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_approve_intent_no_pending_capture_shows_error(self, mock_tg, mock_api):
          mock_api.return_value = {"success": True, "pending": [], "count": 0}
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  bot._handle_approve_intent(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
          mock_tg.assert_called_once_with("sendMessage", {
              "chat_id": self.chat_id,
              "text": "Capture no longer pending. Please /p to refresh.",
          })

      # --- Reject Intent ---

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_reject_intent_shows_confirmation(self, mock_tg, mock_api):
          mock_api.return_value = self.pending_list
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  bot._handle_reject_intent(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)

          mock_tg.assert_called_once()
          payload = mock_tg.call_args[0][1]
          self.assertIn("Confirm rejection?", payload["text"])
          self.assertEqual(payload["reply_markup"]["inline_keyboard"][0][0]["text"], "Confirm Reject")
          self.assertTrue(payload["reply_markup"]["inline_keyboard"][0][0]["callback_data"].startswith("rv1|cr|"))

      # --- Confirm Approve Mutation ---

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_confirm_approve_calls_action_api_and_shows_event_id(self, mock_tg, mock_api):
          mock_api.side_effect = [
              self.pending_list,  # _resolve_cap_ref
              {"success": True, "capture_id": "cap_test_123", "event_id": "evt_approve_123"},  # POST approve
          ]
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  bot._handle_confirm_approve(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)

          # Should edit the original message
          edit_call = mock_tg.call_args_list[0]
          self.assertEqual(edit_call[0][0], "editMessageText")
          payload = edit_call[0][1]
          self.assertIn("Approved", payload["text"])
          self.assertIn("cap_test_123", payload["text"])
          self.assertIn("evt_approve_123", payload["text"])
          # Keyboard should be removed
          self.assertEqual(payload["reply_markup"], {"inline_keyboard": []})

          # Verify approve was called
          self.assertEqual(mock_api.call_args_list[1][0][0], "/captures/cap_test_123/approve")

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_confirm_approve_no_longer_pending_does_not_mutate(self, mock_tg, mock_api):
          mock_api.return_value = {"success": True, "pending": [], "count": 0}
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  bot._handle_confirm_approve(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
          # Should NOT call approve endpoint
          self.assertEqual(mock_api.call_count, 1)  # only the pending list call
          mock_tg.assert_called_once_with("sendMessage", {
              "chat_id": self.chat_id,
              "text": "Capture no longer pending. Please /p to refresh.",
          })

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_confirm_approve_api_unavailable_does_not_mutate(self, mock_tg, mock_api):
          mock_api.side_effect = [
              self.pending_list,
              None,  # Action API unavailable
          ]
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  bot._handle_confirm_approve(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
          mock_tg.assert_called_once_with("sendMessage", {
              "chat_id": self.chat_id,
              "text": "LifeOS review unavailable. No action was taken.",
          })

      # --- Confirm Reject Mutation ---

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_confirm_reject_calls_action_api_and_shows_event_id(self, mock_tg, mock_api):
          mock_api.side_effect = [
              self.pending_list,  # _resolve_cap_ref
              {"success": True, "capture_id": "cap_test_123", "event_id": "evt_reject_123"},  # POST reject
          ]
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  bot._handle_confirm_reject(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)

          edit_call = mock_tg.call_args_list[0]
          self.assertEqual(edit_call[0][0], "editMessageText")
          payload = edit_call[0][1]
          self.assertIn("Rejected", payload["text"])
          self.assertIn("cap_test_123", payload["text"])
          self.assertIn("evt_reject_123", payload["text"])
          self.assertEqual(payload["reply_markup"], {"inline_keyboard": []})

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_confirm_reject_no_longer_pending_does_not_mutate(self, mock_tg, mock_api):
          mock_api.return_value = {"success": True, "pending": [], "count": 0}
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  bot._handle_confirm_reject(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
          self.assertEqual(mock_api.call_count, 1)

      # --- Boundary: no direct filesystem access ---

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_intent_flow_does_not_touch_filesystem(self, mock_tg, mock_api):
          mock_api.return_value = self.pending_list
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  with patch("builtins.open") as mock_open:
                      bot._handle_approve_intent(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
                      mock_open.assert_not_called()

      @patch.object(bot, 'call_action_api')
      @patch.object(bot, 'tg_api')
      def test_confirm_flow_does_not_touch_filesystem(self, mock_tg, mock_api):
          mock_api.side_effect = [
              self.pending_list,
              {"success": True, "capture_id": "cap_test_123", "event_id": "evt_approve_123"},
          ]
          with patch.object(bot, 'BOT_TOKEN', "test_token"):
              with patch.object(bot, 'ALLOWED_USER_ID', self.sender_id):
                  with patch("builtins.open") as mock_open:
                      bot._handle_confirm_approve(self.chat_id, self.msg_id, self.sender_id, self.cap_ref)
                      mock_open.assert_not_called()
  ```

- [ ] **Step 2: Run tests to verify they fail**

  Run: `python3 -m unittest 40_Services/chatops/telegram/tests/test_telegram_bot.py -v`
  Expected: `TestIntentAndConfirmFlows` tests FAIL — handlers are stubs

- [ ] **Step 3: Implement the four handlers**

  Replace the four stub handlers (`_handle_approve_intent`, `_handle_reject_intent`, `_handle_confirm_approve`, `_handle_confirm_reject`):

  ```python
  def _handle_approve_intent(chat_id, msg_id, sender_id, cap_ref):
      capture_id, error = _resolve_cap_ref(cap_ref)
      if capture_id is None:
          tg_api("sendMessage", {"chat_id": chat_id, "text": error})
          return

      # Generate confirm approve + cancel tokens
      token_ca = _make_token("ca", sender_id, cap_ref)
      token_n = _make_token("n", sender_id, cap_ref)

      # Fetch capture for preview text
      result = call_action_api(f"/captures/{capture_id}")
      preview = capture_id
      if result and result.get("success"):
          content = result["capture"].get("content", "")
          preview = _extract_preview_line(content)[:120]

      tg_api("editMessageText", {
          "chat_id": chat_id,
          "message_id": msg_id,
          "text": (
              f"Confirm approval?\n\n"
              f"capture_id: {capture_id}\n"
              f"Preview: {preview}"
          ),
          "reply_markup": {
              "inline_keyboard": [
                  [
                      {"text": "Confirm Approve", "callback_data": token_ca},
                      {"text": "Cancel", "callback_data": token_n},
                  ],
              ],
          },
      })


  def _handle_reject_intent(chat_id, msg_id, sender_id, cap_ref):
      capture_id, error = _resolve_cap_ref(cap_ref)
      if capture_id is None:
          tg_api("sendMessage", {"chat_id": chat_id, "text": error})
          return

      # Generate confirm reject + cancel tokens
      token_cr = _make_token("cr", sender_id, cap_ref)
      token_n = _make_token("n", sender_id, cap_ref)

      result = call_action_api(f"/captures/{capture_id}")
      preview = capture_id
      if result and result.get("success"):
          content = result["capture"].get("content", "")
          preview = _extract_preview_line(content)[:120]

      tg_api("editMessageText", {
          "chat_id": chat_id,
          "message_id": msg_id,
          "text": (
              f"Confirm rejection?\n\n"
              f"capture_id: {capture_id}\n"
              f"Preview: {preview}"
          ),
          "reply_markup": {
              "inline_keyboard": [
                  [
                      {"text": "Confirm Reject", "callback_data": token_cr},
                      {"text": "Cancel", "callback_data": token_n},
                  ],
              ],
          },
      })


  def _handle_confirm_approve(chat_id, msg_id, sender_id, cap_ref):
      capture_id, error = _resolve_cap_ref(cap_ref)
      if capture_id is None:
          tg_api("sendMessage", {"chat_id": chat_id, "text": error})
          return

      result = call_action_api(f"/captures/{capture_id}/approve", {})
      if result is None:
          tg_api("sendMessage", {
              "chat_id": chat_id,
              "text": "LifeOS review unavailable. No action was taken.",
          })
          return

      cid = result.get("capture_id", capture_id)
      text_reply = f"Approved: {cid}"
      event_id = result.get("event_id")
      if event_id:
          text_reply += f"\nevent_id: {event_id}"

      tg_api("editMessageText", {
          "chat_id": chat_id,
          "message_id": msg_id,
          "text": text_reply,
          "reply_markup": {"inline_keyboard": []},
      })


  def _handle_confirm_reject(chat_id, msg_id, sender_id, cap_ref):
      capture_id, error = _resolve_cap_ref(cap_ref)
      if capture_id is None:
          tg_api("sendMessage", {"chat_id": chat_id, "text": error})
          return

      result = call_action_api(f"/captures/{capture_id}/reject", {})
      if result is None:
          tg_api("sendMessage", {
              "chat_id": chat_id,
              "text": "LifeOS review unavailable. No action was taken.",
          })
          return

      cid = result.get("capture_id", capture_id)
      text_reply = f"Rejected: {cid}"
      event_id = result.get("event_id")
      if event_id:
          text_reply += f"\nevent_id: {event_id}"

      tg_api("editMessageText", {
          "chat_id": chat_id,
          "message_id": msg_id,
          "text": text_reply,
          "reply_markup": {"inline_keyboard": []},
      })
  ```

- [ ] **Step 4: Run tests to verify they pass**

  Run: `python3 -m unittest 40_Services/chatops/telegram/tests/test_telegram_bot.py -v`
  Expected: all `TestIntentAndConfirmFlows` tests PASS; existing tests still PASS

- [ ] **Step 5: Run full test suite**

  Run: `python3 -m unittest discover -s 40_Services/chatops/telegram/tests -v`
  Expected: all tests PASS

- [ ] **Step 6: Commit**

  ```bash
  git add 40_Services/chatops/telegram/telegram_capture_bot.py
  git add 40_Services/chatops/telegram/tests/test_telegram_bot.py
  git commit -m "feat: add approve/reject confirmation and mutation flow"
  ```

---
### Task 5: Update README and Current-State Docs

**Files:**
- Modify: `40_Services/chatops/telegram/README.md`
- Modify: `docs/superpowers/specs/2026-07-07-telegram-review-button-ux-design.md` (update status from Draft to Final if appropriate; remove Pending Review)

- [ ] **Step 1: Run tests to confirm pre-doc state is clean**

  Run: `python3 -m unittest discover -s 40_Services/chatops/telegram/tests -v`
  Expected: all tests PASS

- [ ] **Step 2: Update README.md**

  At the end of the Review Lifecycle section (before "## Review Test Mode (--review-test)"), add:

  ```markdown
  ### Inline Review Buttons (V1)

  When review mode is active (`--allow-review` or `TELEGRAM_ALLOW_REVIEW=1`),
  `/view <n>` now sends a summary with inline keyboard buttons instead of the
  full capture content:

  ```text
  Capture: cap_20260707_120000_a1b2c3_slug
  Status: pending_review
  Created: 2026-07-07T12:00:00Z
  Preview: My quick note about...

  [View Full Text]  [Approve]  [Reject]
  ```

  Button flow (all stateless, HMAC-signed callback tokens, 10-minute expiry):

  - **[View Full Text]** — sends the complete capture content as a separate
    message with no approve/reject buttons.
  - **[Approve]** — shows a confirmation prompt with [Confirm Approve] and
    [Cancel]. No mutation occurs at this stage.
  - **[Reject]** — same confirmation pattern with [Confirm Reject] and [Cancel].
  - **[Confirm Approve]** — calls `POST /captures/<id>/approve` on the Action
    API and shows the result with `event_id`.
  - **[Confirm Reject]** — calls `POST /captures/<id>/reject` on the Action API
    and shows the result with `event_id`.
  - **[Cancel]** — removes the inline keyboard, no mutation.

  **Boundary enforcement:**
  - Every button path calls `answerCallbackQuery` exactly once.
  - Stale buttons tapped after review mode is disabled receive:
    `Review mode is disabled. Please /p to refresh.`
  - Expired or invalid tokens receive:
    `Invalid or expired button. Please /p to refresh.`
  - Captures that are no longer pending receive:
    `Capture no longer pending. Please /p to refresh.`
  - All mutations route through the Action API — the Telegram bot never
    directly reads, moves, or writes capture files.
  - Callback tokens are sender-bound (different user → MAC mismatch) and
    action-bound (approve token cannot be reused as reject).
  ```

  Replace the `/view` row in the Action API endpoint mapping table:
  ```diff
  -| `/view <n>` | `GET /captures/pending/<n>` | GET |
  +| `/view <n>` | `GET /captures/pending/<n>` | GET (summary + inline buttons) |
  ```

  Add new rows for view-full (callback-resolved):
  ```diff
  +| View Full Text (button) | `GET /captures/pending` → `GET /captures/<id>` | GET + GET (cap_ref resolved) |
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add 40_Services/chatops/telegram/README.md
  git commit -m "docs: document inline review button flow in README"
  ```

---
## Verification

After all tasks complete, run the full verification suite:

```bash
cd /home/lifeos

# Compile check
python3 -m py_compile 40_Services/action_api/server.py
python3 -m py_compile 40_Services/chatops/telegram/telegram_capture_bot.py

# Action API tests
python3 -m unittest 40_Services.action_api.tests.test_action_api

# Telegram tests (full suite)
python3 -m unittest discover -s 40_Services/chatops/telegram/tests -v

# Status API tests
python3 -m unittest 40_Services.status_api.tests.test_status_api

# Verify no tracked changes outside intended files
git status --short
```

Expected: all compiles pass, all tests pass, only `telegram_capture_bot.py`, `test_telegram_bot.py`, `test_telegram_bot_boundaries.py`, and `README.md` have uncommitted changes (if any remain).

---
## Self-Review Checklist

- [ ] **Spec coverage:** Every section in the design doc (1-14) maps to at least one task. Section 1-2 (overview/flow) → Tasks 3-4. Section 3 (tokens) → Task 1. Section 4 (cap_ref) → Task 2. Section 5 (callback handler) → Task 2. Section 6 (view handler) → Task 3. Section 7 (confirmation) → Task 4. Section 8 (error handling) → Tasks 2-4. Section 9 (security) → Task 1. Section 10 (gating) → Task 2. Section 11 (tests) → Tasks 1-4. Section 12-14 (files/changelog) → Task 5.
- [ ] **No placeholders:** Every code step has complete implementation code and complete test code. No "TBD", "TODO", "implement later".
- [ ] **Type consistency:** `_make_token(action, sender_id, cap_ref)` and `_verify_token(sender_id, callback_data)` use the same parameter ordering in all tasks. `_resolve_cap_ref` returns `(capture_id | None, error | None)` consistently.
- [ ] **Callback answering:** Every path answers exactly once — verified in Task 2 handler code and Task 2 tests.
- [ ] **No filesystem access:** All mutation handlers route through `call_action_api` — verified by boundary tests in Tasks 2, 3, 4.
- [ ] **ALLOW_REVIEW_COMMANDS guard:** Tested in Task 2 (`test_review_disabled_answers_with_text_and_returns`). Handler shows correct text.
