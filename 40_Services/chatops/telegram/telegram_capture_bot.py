#!/usr/bin/env python3
import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

import message_cards as cards

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIFEOS_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..', '..'))
ENV_PATH = os.path.join(LIFEOS_ROOT, '40_Services', 'config', 'telegram', '.env')
RUNTIME_DIR = os.path.join(LIFEOS_ROOT, '40_Services', 'config', 'telegram', 'runtime')
OFFSET_PATH = os.path.join(RUNTIME_DIR, 'update_offset.json')
CAPTURE_DIR = os.path.join(LIFEOS_ROOT, '30_Capture')
NOTES_DIR = os.path.join(CAPTURE_DIR, 'notes')
PENDING_DIR = os.path.join(CAPTURE_DIR, 'pending_review')
APPROVED_DIR = os.path.join(CAPTURE_DIR, 'approved')
REJECTED_DIR = os.path.join(CAPTURE_DIR, 'rejected')
EVENT_LOG = os.path.join(LIFEOS_ROOT, '50_Event_Log', 'events.jsonl')
STATUS_API_URL = "http://localhost:8787/status"
ACTION_API_URL = "http://localhost:8788"

ALLOWED_USER_ID = None
BOT_TOKEN = None
ALLOW_REVIEW_COMMANDS = False

# --- Callback token constants ---
TOKEN_VERSION = "rv1"
TOKEN_TTL = 600       # 10 minutes
MAC_TRUNC = 12        # hex chars
ALL_ACTIONS = ("v", "p", "a", "r", "ca", "cr", "n")

def load_env():
    global BOT_TOKEN, ALLOWED_USER_ID, ALLOW_REVIEW_COMMANDS
    if not os.path.exists(ENV_PATH):
        print("FATAL: .env not found at", ENV_PATH)
        sys.exit(1)
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, val = line.partition('=')
                env[key.strip()] = val.strip()
    BOT_TOKEN = env.get('TELEGRAM_BOT_TOKEN', '')
    user_id_str = env.get('TELEGRAM_ALLOWED_USER_ID', '')
    allow_review_env = env.get('TELEGRAM_ALLOW_REVIEW', '0')
    if allow_review_env.lower() in ('1', 'true', 'yes'):
        ALLOW_REVIEW_COMMANDS = True
    if not BOT_TOKEN or not user_id_str:
        print("FATAL: TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_USER_ID missing in .env")
        sys.exit(1)
    try:
        ALLOWED_USER_ID = int(user_id_str)
    except ValueError:
        print("FATAL: TELEGRAM_ALLOWED_USER_ID must be an integer")
        sys.exit(1)


def extract_sender_id(update):
    msg = update.get('message', {})
    sender_id = msg.get('from', {}).get('id')
    chat_id = msg.get('chat', {}).get('id')
    return sender_id, chat_id


def is_authorized_sender(sender_id):
    return sender_id is not None and sender_id == ALLOWED_USER_ID


def reject_unauthorized(chat_id):
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': cards.format_unauthorized()
    })
    append_event('chatops.telegram.unauthorized_sender_rejected', {
        'source': 'telegram',
        'sender_rejected': True,
        'raw_message_logged': False,
    })


def tg_api(method, payload=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return json.loads(body)
    except Exception as e:
        return {"ok": False, "description": str(e)}


def call_action_api(endpoint, payload=None):
    url = f"{ACTION_API_URL}{endpoint}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
    except Exception:
        return None


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


def action_api_unavailable_reply(chat_id):
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': cards.format_action_api_unavailable()
    })


def _extract_preview_line(content_text):
    for line in content_text.split('\n'):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('```') and not stripped.startswith('---'):
            return stripped[:80]
    return content_text[:80].replace('\n', ' ')


def validate_event_log():
    if not os.path.exists(EVENT_LOG):
        print("FAIL: event log not found at", EVENT_LOG)
        sys.exit(1)
    with open(EVENT_LOG) as f:
        content = f.read()
    if not content.strip():
        return []
    lines = content.strip().split('\n')
    ids = set()
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        obj = json.loads(line)
        eid = obj.get('event_id')
        if not eid:
            print(f"FAIL: event_log line {i+1} missing event_id")
            sys.exit(1)
        if eid in ids:
            print(f"FAIL: duplicate event_id {eid} at line {i+1}")
            sys.exit(1)
        ids.add(eid)
    return lines


def load_offset():
    if os.path.exists(OFFSET_PATH):
        with open(OFFSET_PATH) as f:
            return json.load(f).get('offset', 0)
    return 0


def save_offset(offset):
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    with open(OFFSET_PATH, 'w') as f:
        json.dump({'offset': offset}, f)


def make_event_id(event_type, existing_ids=None):
    now = datetime.now(timezone.utc)
    suffix = event_type.replace('.', '_')
    base = f"evt_{now.strftime('%Y%m%dT%H%M%SZ')}_{suffix}"
    if existing_ids is None:
        return base
    candidate = base
    counter = 1
    while candidate in existing_ids:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def append_event(event_type, details):
    """
    Appends local operational telemetry/security events to the local log.
    All state mutations and audit events must be dispatched via the Action API
    rather than being logged directly by the Telegram bot.
    """
    allowed_operational_events = {
        'chatops.telegram.unauthorized_sender_rejected',
        'chatops.telegram.help_requested',
    }
    if event_type not in allowed_operational_events:
        raise ValueError(f"Direct logging of non-operational event '{event_type}' is forbidden. Mutations must go through Action API.")

    lines = validate_event_log()
    existing_ids = set()
    for line in lines:
        obj = json.loads(line)
        eid = obj.get('event_id')
        if eid:
            existing_ids.add(eid)
    event_id = make_event_id(event_type, existing_ids=existing_ids)
    event = {
        'event_id': event_id,
        'event_type': event_type,
        'occurred_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'actor': {
            'type': 'human',
            'id': f'telegram:{ALLOWED_USER_ID}'
        },
        'approval_tier': 'A0',
        'status': 'completed',
        'summary': '',
        'details': details
    }
    if event_type == 'chatops.telegram.unauthorized_sender_rejected':
        event['summary'] = 'Rejected unauthorized Telegram sender.'
    elif event_type == 'chatops.telegram.help_requested':
        event['summary'] = 'Telegram help requested.'

    with open(EVENT_LOG, 'a+') as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        needs_newline = True
        if pos > 0:
            f.seek(pos - 1)
            needs_newline = f.read(1) != '\n'
        if needs_newline:
            f.write('\n')
        f.write(json.dumps(event, ensure_ascii=False))
    return event_id



def slugify(text):
    s = text.lower().strip()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s[:40]


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
    elif action == "p":
        _handle_proposal_button(chat_id, cap_ref)
    elif action == "a":
        _handle_approve_intent(chat_id, msg_id, sender_id, cap_ref)
    elif action == "r":
        _handle_reject_intent(chat_id, msg_id, sender_id, cap_ref)
    elif action == "ca":
        _handle_confirm_approve(chat_id, msg_id, sender_id, cap_ref)
    elif action == "cr":
        _handle_confirm_reject(chat_id, msg_id, sender_id, cap_ref)


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


def _handle_proposal_button(chat_id, cap_ref):
    capture_id, error = _resolve_cap_ref(cap_ref)
    if capture_id is None:
        tg_api("sendMessage", {"chat_id": chat_id, "text": error})
        return

    result = call_action_api(f"/captures/{capture_id}")
    if result is None or not result.get("success"):
        tg_api("sendMessage", {
            "chat_id": chat_id,
            "text": "Capture not found. No action was taken.",
        })
        return

    capture = result["capture"]
    cid = capture.get("capture_id", capture_id)
    content = capture.get("content", "")
    title = cards.infer_title(content)
    ctype, route = cards.classify_capture(content)
    next_action = next_action_for_type(ctype)
    index = capture.get("index")

    text = cards.format_proposal(
        capture_id=cid, index=index, title=title,
        capture_type=ctype, suggested_route=route,
        next_action=next_action,
    )
    tg_api("sendMessage", {"chat_id": chat_id, "text": text})


def _handle_approve_intent(chat_id, msg_id, sender_id, cap_ref):
    capture_id, error = _resolve_cap_ref(cap_ref)
    if capture_id is None:
        tg_api("sendMessage", {"chat_id": chat_id, "text": error})
        return

    token_ca = _make_token("ca", sender_id, cap_ref)
    token_n = _make_token("n", sender_id, cap_ref)

    result = call_action_api(f"/captures/{capture_id}")
    preview = capture_id
    if result and result.get("success"):
        capture = result.get("capture", {})
        content = capture.get("content", "")
        preview = _extract_preview_line(content)[:120]

    text = cards.format_card("Confirm Approval", rows=[
        ("ID", capture_id),
    ])
    tg_api("editMessageText", {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text,
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

    token_cr = _make_token("cr", sender_id, cap_ref)
    token_n = _make_token("n", sender_id, cap_ref)

    result = call_action_api(f"/captures/{capture_id}")
    preview = capture_id
    if result and result.get("success"):
        capture = result.get("capture", {})
        content = capture.get("content", "")
        preview = _extract_preview_line(content)[:120]

    text = cards.format_card("Confirm Rejection", rows=[
        ("ID", capture_id),
    ])
    tg_api("editMessageText", {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text,
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
    event_id = result.get("event_id")
    rows = [("ID", cid)]
    if event_id:
        rows.append(("Event", event_id))
    text_reply = cards.format_card("Approved", rows=rows,
                                   footer="No vault write performed.")

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
    event_id = result.get("event_id")
    rows = [("ID", cid)]
    if event_id:
        rows.append(("Event", event_id))
    text_reply = cards.format_card("Rejected", rows=rows,
                                   footer="No vault write performed.")

    tg_api("editMessageText", {
        "chat_id": chat_id,
        "message_id": msg_id,
        "text": text_reply,
        "reply_markup": {"inline_keyboard": []},
    })


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

    cmd = (text or '').strip().lower().split()[0] if text else ''
    if '@' in cmd:
        cmd = cmd.split('@')[0]

    m = re.match(r'^/(r|a|view)(\d+)$', cmd)
    if m:
        text = f'/{m.group(1)} {m.group(2)}'
        cmd = f'/{m.group(1)}'

    read_only_cmds = {'/p', '/view', '/proposal'}
    mutation_cmds = {'/a', '/r', '/list_pending', '/approve', '/reject'}

    if cmd in mutation_cmds and not ALLOW_REVIEW_COMMANDS:
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': cards.format_capture_first_blocked()
        })
        print(f"Capture-first mode: blocked mutation command '{cmd}'")
        return

    if cmd == '/capture':
        handle_capture(text, chat_id, sender_id, msg)
    elif cmd == '/help':
        handle_help(chat_id)
    elif cmd == '/status':
        handle_status(chat_id)
    elif cmd == '/list_pending':
        handle_list_pending(chat_id)
    elif cmd == '/approve':
        handle_approve(text, chat_id)
    elif cmd == '/reject':
        handle_reject(text, chat_id)
    elif cmd == '/p':
        handle_p(chat_id)
    elif cmd == '/view':
        handle_view(text, chat_id)
    elif cmd == '/a':
        handle_a(text, chat_id)
    elif cmd == '/r':
        handle_r(text, chat_id)
    elif cmd == '/proposal':
        handle_proposal(text, chat_id)
    else:
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': 'Unknown command. Try /help'
        })


def handle_capture(text, chat_id, sender_id, msg):
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': 'Usage: /capture <text>'
        })
        return

    content = parts[1].strip()
    result = call_action_api('/captures', {'text': content})
    if result is None or not result.get('success'):
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': cards.format_capture_failure()
        })
        return

    capture_id = result.get('capture_id', 'unknown')
    event_id = result.get('event_id')
    text_reply = cards.format_capture_success(capture_id, event_id=event_id)
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': text_reply
    })


def handle_help(chat_id):
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': (
            'LifeOS ChatOps commands:\n'
            '/capture <text>\n'
            '/p — list pending (numbered)\n'
            '/view <n> — view pending details\n'
            '/a [n|latest] — approve\n'
            '/r [n|latest] — reject\n'
            '/proposal <n> — get proposal\n'
            '/list_pending\n'
            '/approve <capture_id>\n'
            '/reject <capture_id>\n'
            '/status\n'
            '/help'
        )
    })
    append_event('chatops.telegram.help_requested', {
        'source': 'telegram',
    })


def handle_status(chat_id):
    try:
        req = urllib.request.Request(STATUS_API_URL)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
    except Exception:
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': cards.format_status_api_unavailable()
        })
        return

    status_text = cards.format_status_card(data)
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': status_text
    })


def handle_list_pending(chat_id):
    result = call_action_api('/captures/pending')
    if result is None or not result.get('success'):
        action_api_unavailable_reply(chat_id)
        return
    pending = result.get('pending', [])
    count = result.get('count', 0)
    text_reply = cards.format_pending_queue(pending, count=count)
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': text_reply
    })


def handle_approve(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': 'Usage: /approve <capture_id>'
        })
        return
    capture_id = parts[1].strip()
    result = call_action_api(f'/captures/{capture_id}/approve', {})
    if result is None:
        action_api_unavailable_reply(chat_id)
        return
    if not result.get('success'):
        error = result.get('error', 'unknown')
        tg_api('sendMessage', {'chat_id': chat_id, 'text': cards.format_review_failed(error)})
        return
    cid = result.get("capture_id", capture_id)
    event_id = result.get('event_id')
    pairs = [("ID", cid)]
    if event_id:
        pairs.append(("Event", event_id))
    text_reply = cards.format_card("Approved", rows=pairs,
                                   footer="No vault write performed.")
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': text_reply
    })


def handle_reject(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': 'Usage: /reject <capture_id>'
        })
        return
    capture_id = parts[1].strip()
    result = call_action_api(f'/captures/{capture_id}/reject', {})
    if result is None:
        action_api_unavailable_reply(chat_id)
        return
    if not result.get('success'):
        error = result.get('error', 'unknown')
        tg_api('sendMessage', {'chat_id': chat_id, 'text': cards.format_review_failed(error)})
        return
    cid = result.get("capture_id", capture_id)
    event_id = result.get('event_id')
    pairs = [("ID", cid)]
    if event_id:
        pairs.append(("Event", event_id))
    text_reply = cards.format_card("Rejected", rows=pairs,
                                   footer="No vault write performed.")
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': text_reply
    })


def handle_p(chat_id):
    result = call_action_api('/captures/pending')
    if result is None or not result.get('success'):
        action_api_unavailable_reply(chat_id)
        return
    items = result.get('pending', [])
    count = result.get('count', 0)
    mode = "review" if ALLOW_REVIEW_COMMANDS else "capture-first"
    text_reply = cards.format_pending_queue(items, count=count, mode=mode)
    tg_api('sendMessage', {'chat_id': chat_id, 'text': text_reply})


def handle_view(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        tg_api("sendMessage", {"chat_id": chat_id, "text": cards.format_needs_index("view")})
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
    ctype = capture.get("capture_type", "unknown")
    status = capture.get("status", "pending_review")
    content = capture.get("content", "")
    index = capture.get("index", "?")

    title = cards.infer_title(content)
    preview = _extract_preview_line(content)[:120]

    rows = [
        ("Title", title),
        ("Type", ctype),
        ("Status", status),
    ]
    body = f"Preview: {preview}" if preview else ""
    summary = cards.format_card(f"Capture {index}", rows=rows, body=body)

    cap_ref = _make_cap_ref(cid)
    token_v = _make_token("v", ALLOWED_USER_ID, cap_ref)
    token_p = _make_token("p", ALLOWED_USER_ID, cap_ref)
    token_a = _make_token("a", ALLOWED_USER_ID, cap_ref)
    token_r = _make_token("r", ALLOWED_USER_ID, cap_ref)

    inline_kb = {
        "inline_keyboard": [
            [{"text": "View Full", "callback_data": token_v},
             {"text": "Proposal", "callback_data": token_p}],
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


def handle_a(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    index_text = parts[1].strip() if len(parts) > 1 else ''
    if not index_text:
        tg_api("sendMessage", {"chat_id": chat_id, "text": cards.format_needs_index("a")})
        return
    if index_text == 'latest':
        endpoint = '/captures/pending/latest'
    elif index_text.isdigit():
        endpoint = f'/captures/pending/{index_text}'
    else:
        tg_api('sendMessage', {'chat_id': chat_id, 'text': f"Invalid index: '{index_text}'. Use a number or 'latest'."})
        return
    result = call_action_api(endpoint)
    if result is None or not result.get('success'):
        tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Capture not found. No action was taken.'})
        return
    capture_id = result['capture'].get('capture_id', '')
    if not capture_id:
        tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Capture not found. No action was taken.'})
        return
    approve_result = call_action_api(f'/captures/{capture_id}/approve', {})
    if approve_result is None:
        action_api_unavailable_reply(chat_id)
        return
    if not approve_result.get('success'):
        error = approve_result.get('error', 'unknown')
        tg_api('sendMessage', {'chat_id': chat_id, 'text': cards.format_review_failed(error)})
        return
    cid = approve_result.get("capture_id", capture_id)
    event_id = approve_result.get('event_id')
    pairs = [("ID", cid)]
    if event_id:
        pairs.append(("Event", event_id))
    text_reply = cards.format_card("Approved", rows=pairs,
                                   footer="No vault write performed.")
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': text_reply
    })


def handle_r(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    index_text = parts[1].strip() if len(parts) > 1 else ''
    if not index_text:
        tg_api("sendMessage", {"chat_id": chat_id, "text": cards.format_needs_index("r")})
        return
    if index_text == 'latest':
        endpoint = '/captures/pending/latest'
    elif index_text.isdigit():
        endpoint = f'/captures/pending/{index_text}'
    else:
        tg_api('sendMessage', {'chat_id': chat_id, 'text': f"Invalid index: '{index_text}'. Use a number or 'latest'."})
        return
    result = call_action_api(endpoint)
    if result is None or not result.get('success'):
        tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Capture not found. No action was taken.'})
        return
    capture_id = result['capture'].get('capture_id', '')
    if not capture_id:
        tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Capture not found. No action was taken.'})
        return
    reject_result = call_action_api(f'/captures/{capture_id}/reject', {})
    if reject_result is None:
        action_api_unavailable_reply(chat_id)
        return
    if not reject_result.get('success'):
        error = reject_result.get('error', 'unknown')
        tg_api('sendMessage', {'chat_id': chat_id, 'text': cards.format_review_failed(error)})
        return
    cid = reject_result.get("capture_id", capture_id)
    event_id = reject_result.get('event_id')
    pairs = [("ID", cid)]
    if event_id:
        pairs.append(("Event", event_id))
    text_reply = cards.format_card("Rejected", rows=pairs,
                                   footer="No vault write performed.")
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': text_reply
    })


def handle_proposal(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    target = parts[1].strip() if len(parts) > 1 else ''
    if not target:
        tg_api("sendMessage", {"chat_id": chat_id, "text": "Usage: /proposal <index> or /proposal <capture_id>"})
        return
    if target.isdigit():
        endpoint = f'/captures/pending/{target}'
    elif target == 'latest':
        endpoint = '/captures/pending/latest'
    elif target.startswith('cap_'):
        endpoint = f'/captures/{target}'
    else:
        tg_api('sendMessage', {'chat_id': chat_id, 'text': f"Invalid target: '{target}'. Use a number, 'latest', or a capture_id."})
        return
    result = call_action_api(endpoint)
    if result is None:
        action_api_unavailable_reply(chat_id)
        return
    if not result.get('success'):
        tg_api('sendMessage', {'chat_id': chat_id, 'text': cards.format_proposal_invalid(target)})
        return
    capture = result.get('capture', {})
    capture_id = capture.get('capture_id', '')
    if not capture_id:
        tg_api('sendMessage', {'chat_id': chat_id, 'text': cards.format_proposal_invalid(target)})
        return
    content = capture.get('content', '')
    title = cards.infer_title(content)
    ctype, route = cards.classify_capture(content)
    next_action = next_action_for_type(ctype)
    created_at = capture.get('created_at')
    index = capture.get('index')
    text_reply = cards.format_proposal(
        capture_id=capture_id, index=index, title=title,
        capture_type=ctype, suggested_route=route,
        next_action=next_action, created_at=created_at
    )
    tg_api('sendMessage', {'chat_id': chat_id, 'text': text_reply})


def next_action_for_type(ctype):
    actions = {
        'link': 'Review the link and decide if it should be saved to knowledge base.',
        'idea': 'Review the idea. Promising ideas go to Ideas folder after approval.',
        'note': 'Review the note. Useful notes go to Inbox for later processing.',
        'task': 'Review the task. If actionable, it should go to the task board after approval.',
        'project_update': 'Review the update. If significant, append to the project log after approval.',
        'unknown': 'Review this capture and manually decide the next step.',
    }
    return actions.get(ctype, actions['unknown'])


def cmd_check():
    load_env()
    me = tg_api('getMe')
    if me.get('ok'):
        u = me['result']
        print(f"Bot: @{u['username']} ({u['first_name']})")
    else:
        print("FAIL: getMe failed:", me.get('description'))
        sys.exit(1)
    for d in [RUNTIME_DIR, NOTES_DIR, PENDING_DIR]:
        os.makedirs(d, exist_ok=True)
    validate_event_log()
    print("All checks passed.")
    sys.exit(0)


def cmd_once():
    load_env()
    offset = load_offset()
    updates = tg_api('getUpdates', {'offset': offset, 'timeout': 2})
    if not updates.get('ok'):
        print("FAIL: getUpdates failed:", updates.get('description'))
        sys.exit(1)
    result = updates.get('result', [])
    if not result:
        print("No new updates.")
        return
    for update in result:
        process_update(update)
        new_offset = update['update_id'] + 1
        save_offset(new_offset)


def cmd_poll(interval):
    load_env()
    print(f"Polling every {interval}s... Press Ctrl+C to stop.")
    try:
        while True:
            offset = load_offset()
            updates = tg_api('getUpdates', {'offset': offset, 'timeout': 5})
            if updates.get('ok'):
                for update in updates.get('result', []):
                    process_update(update)
                    new_offset = update['update_id'] + 1
                    save_offset(new_offset)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def process_receive_test_update(update):
    """Safe receive-test handler. Never dispatches normal commands or mutates state."""
    msg = update.get('message', {})
    text = msg.get('text', '')
    from_info = msg.get('from', {})
    sender_id, chat_id = extract_sender_id(update)

    if chat_id is None:
        print("Receive test: update has no chat_id, skipping.")
        return

    if not is_authorized_sender(sender_id):
        print("Receive test: unauthorized sender rejected")
        reject_unauthorized(chat_id)
        return

    username = from_info.get('username') or from_info.get('first_name', 'unknown')
    preview = (text or '')[:80]
    print(f"Receive test: message from {username} (id={sender_id}): {preview}")

    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': 'LifeOS receive test OK. No action was taken.'
    })
    print("Receive test: safe acknowledgement sent.")


def process_capture_test_update(update):
    """Capture-test handler. Only allows /capture <text>. Never dispatches normal commands."""
    msg = update.get('message', {})
    text = msg.get('text', '')
    sender_id, chat_id = extract_sender_id(update)

    if chat_id is None:
        print("Capture test: update has no chat_id, skipping.")
        return

    if not is_authorized_sender(sender_id):
        print("Capture test: unauthorized sender rejected")
        reject_unauthorized(chat_id)
        return

    cmd = (text or '').strip().lower().split()[0] if text else ''
    if '@' in cmd:
        cmd = cmd.split('@')[0]

    m = re.match(r'^/(r|a|view)(\d+)$', cmd)
    if m:
        text = f'/{m.group(1)} {m.group(2)}'
        cmd = f'/{m.group(1)}'

    if cmd == '/capture':
        handle_capture(text, chat_id, sender_id, msg)
    else:
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': 'LifeOS capture-test mode is active. No action was taken.'
        })
        print(f"Capture test: blocked non-capture command '{cmd}'")


def process_review_test_update(update):
    """Review-test handler. Only allows review commands. Never dispatches normal commands."""
    msg = update.get('message', {})
    text = msg.get('text', '')
    sender_id, chat_id = extract_sender_id(update)

    if chat_id is None:
        print("Review test: update has no chat_id, skipping.")
        return

    if not is_authorized_sender(sender_id):
        print("Review test: unauthorized sender rejected")
        reject_unauthorized(chat_id)
        return

    cmd = (text or '').strip().lower().split()[0] if text else ''
    if '@' in cmd:
        cmd = cmd.split('@')[0]

    m = re.match(r'^/(r|a|view)(\d+)$', cmd)
    if m:
        text = f'/{m.group(1)} {m.group(2)}'
        cmd = f'/{m.group(1)}'

    if cmd == '/p':
        handle_p(chat_id)
    elif cmd == '/list_pending':
        handle_list_pending(chat_id)
    elif cmd == '/view':
        handle_view(text, chat_id)
    elif cmd == '/proposal':
        handle_proposal(text, chat_id)
    elif cmd == '/a':
        handle_a(text, chat_id)
    elif cmd == '/r':
        handle_r(text, chat_id)
    elif cmd == '/approve':
        handle_approve(text, chat_id)
    elif cmd == '/reject':
        handle_reject(text, chat_id)
    else:
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': 'LifeOS review-test mode is active. No action was taken.'
        })
        print(f"Review test: blocked non-review command '{cmd}'")


def cmd_capture_test():
    """Capture-test mode: fetch at most one update, only allow /capture, exit."""
    load_env()
    offset = load_offset()
    updates = tg_api('getUpdates', {'offset': offset, 'timeout': 2})
    if not updates.get('ok'):
        print("FAIL: getUpdates failed:", updates.get('description'))
        sys.exit(1)
    result = updates.get('result', [])
    if not result:
        print("No new updates to test.")
        return
    update = result[0]
    process_capture_test_update(update)
    new_offset = update['update_id'] + 1
    save_offset(new_offset)
    print("Capture test complete.")


def cmd_review_test():
    """Review-test mode: fetch at most one update, only allow review commands, exit."""
    load_env()
    offset = load_offset()
    updates = tg_api('getUpdates', {'offset': offset, 'timeout': 2})
    if not updates.get('ok'):
        print("FAIL: getUpdates failed:", updates.get('description'))
        sys.exit(1)
    result = updates.get('result', [])
    if not result:
        print("No new updates to test.")
        return
    update = result[0]
    process_review_test_update(update)
    new_offset = update['update_id'] + 1
    save_offset(new_offset)
    print("Review test complete.")


def cmd_receive_test():
    """Receive-test mode: fetch at most one update, safely acknowledge, exit."""
    load_env()
    offset = load_offset()
    updates = tg_api('getUpdates', {'offset': offset, 'timeout': 2})
    if not updates.get('ok'):
        print("FAIL: getUpdates failed:", updates.get('description'))
        sys.exit(1)
    result = updates.get('result', [])
    if not result:
        print("No new updates to test.")
        return
    update = result[0]
    process_receive_test_update(update)
    new_offset = update['update_id'] + 1
    save_offset(new_offset)
    print("Receive test complete.")


def main():
    parser = argparse.ArgumentParser(description='LifeOS Telegram Capture Bot - Local Test Handler')
    parser.add_argument('--check', action='store_true', help='Verify configuration and connectivity')
    parser.add_argument('--once', action='store_true', help='Process new updates once')
    parser.add_argument('--poll', action='store_true', help='Poll mode (foreground, Ctrl+C to stop)')
    parser.add_argument('--receive-test', action='store_true', help='Receive-test mode: safely acknowledge one update without dispatching commands')
    parser.add_argument('--capture-test', action='store_true', help='Capture-test mode: safely process only /capture from one update, block all other commands')
    parser.add_argument('--review-test', action='store_true', help='Review-test mode: safely process only review commands from one update, block all other commands')
    parser.add_argument('--interval', type=int, default=3, help='Poll interval in seconds (default: 3)')
    parser.add_argument('--allow-review', action='store_true', help='Allow review commands in polling mode')
    args = parser.parse_args()

    if args.allow_review:
        global ALLOW_REVIEW_COMMANDS
        ALLOW_REVIEW_COMMANDS = True

    if args.check:
        cmd_check()
    elif args.once:
        cmd_once()
    elif args.poll:
        cmd_poll(args.interval)
    elif args.capture_test:
        cmd_capture_test()
    elif args.review_test:
        cmd_review_test()
    elif args.receive_test:
        cmd_receive_test()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
