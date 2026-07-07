#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

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


def load_env():
    global BOT_TOKEN, ALLOWED_USER_ID
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
        'text': 'Unauthorized'
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


def action_api_unavailable_reply(chat_id):
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': 'LifeOS review unavailable. No action was taken.'
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
        'approval_tier': 'A1' if event_type in {
            'chatops.telegram.capture_received',
            'chatops.telegram.approval_received',
            'chatops.telegram.rejection_received',
        } else 'A0',
        'status': 'completed',
        'summary': '',
        'details': details
    }
    if event_type == 'chatops.telegram.capture_received':
        event['summary'] = 'Received Telegram note capture and queued it for pending review.'
    elif event_type == 'chatops.telegram.unauthorized_sender_rejected':
        event['summary'] = 'Rejected unauthorized Telegram sender.'
    elif event_type == 'chatops.telegram.help_requested':
        event['summary'] = 'Telegram help requested.'
    elif event_type == 'chatops.telegram.status_requested':
        event['summary'] = 'Telegram status requested.'
    elif event_type == 'chatops.telegram.approval_received':
        event['summary'] = 'Approved Telegram capture and moved it to approved queue.'
    elif event_type == 'chatops.telegram.rejection_received':
        event['summary'] = 'Rejected Telegram capture and moved it to rejected queue.'
    elif event_type == 'chatops.telegram.pending_list_requested':
        event['summary'] = 'Listed pending Telegram captures.'
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

    cmd = (text or '').strip().lower().split()[0] if text else ''
    if '@' in cmd:
        cmd = cmd.split('@')[0]
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
            'text': 'LifeOS capture unavailable. No action was taken.'
        })
        return

    capture_id = result.get('capture_id', 'unknown')
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': f'Capture created: {capture_id}\nStatus: pending_review\nNo AI processing has started.'
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
            'text': 'LifeOS status unavailable. No action was taken.'
        })
        return

    pending = data.get('pending_captures', '?')
    approved = data.get('approved_unprocessed_captures', '?')
    rejected = data.get('rejected_captures', '?')
    evt_count = data.get('event_log_line_count', '?')
    evt_type = data.get('last_event_type', 'none')
    evt_time = data.get('last_event_time', '')

    evt_line = f"Last event: {evt_type} at {evt_time}" if evt_time else "Last event: none"
    status_text = (
        f"LifeOS Status\n"
        f"Capture queue:\n"
        f"- pending_review: {pending}\n"
        f"- approved: {approved}\n"
        f"- rejected: {rejected}\n"
        f"\n"
        f"Event log: {evt_count} entries\n"
        f"{evt_line}\n"
        f"\n"
        f"Safety:\n"
        f"- no action taken"
    )
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': status_text
    })


def parse_frontmatter(filepath):
    fm = {}
    with open(filepath) as f:
        lines = f.readlines()
    if not lines or lines[0].strip() != '---':
        return fm
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end = i
            break
    if end is None:
        return fm
    for line in lines[1:end]:
        line = line.strip()
        if not line:
            continue
        if ':' in line:
            key, _, val = line.partition(':')
            fm[key.strip()] = val.strip()
    return fm


def find_pending_capture(capture_id):
    matches = []
    for fname in os.listdir(PENDING_DIR):
        if not fname.endswith('.md') or fname == 'README.md':
            continue
        fpath = os.path.join(PENDING_DIR, fname)
        fm = parse_frontmatter(fpath)
        cid = fm.get('capture_id', '')
        if cid == capture_id:
            return fpath, fm, None
        if cid.endswith(capture_id):
            matches.append((fpath, fm, cid))
    if len(matches) == 1:
        return matches[0][0], matches[0][1], None
    if len(matches) > 1:
        candidates = [m[2] for m in matches]
        return None, None, f"'{capture_id}' matches {len(matches)} captures: {', '.join(candidates)}"
    return None, None, None


def get_first_line_content(filepath):
    try:
        with open(filepath) as f:
            lines = f.readlines()
        in_fm = False
        for line in lines:
            stripped = line.strip()
            if stripped == '---':
                in_fm = not in_fm
                continue
            if not in_fm and stripped and not stripped.startswith('#') and not stripped.startswith('```'):
                return stripped[:80]
    except Exception:
        pass
    return ''


def load_pending_capture_summary(path):
    fm = parse_frontmatter(path)
    content_summary = get_first_line_content(path)
    cid = fm.get('capture_id', '')
    ctype = fm.get('capture_type', '')
    created = fm.get('created_at', '')
    return {
        'capture_id': cid,
        'capture_type': ctype or 'unknown',
        'created_at': created,
        'summary': content_summary or cid or '(no content)',
    }


def list_pending_review_files():
    items = []
    for fname in sorted(os.listdir(PENDING_DIR)):
        if not fname.endswith('.md') or fname == 'README.md':
            continue
        fpath = os.path.join(PENDING_DIR, fname)
        summary = load_pending_capture_summary(fpath)
        summary['path'] = fpath
        summary['filename'] = fname
        items.append(summary)
    return items


def format_pending_queue(items):
    if not items:
        return 'No pending captures.'
    lines = ['Pending captures:']
    for i, item in enumerate(items, 1):
        lines.append(f"\n{i}. {item['capture_type']} — {item['summary']}")
    lines.append('\n\nUse:\n/view 1\n/a 1\n/r 1')
    return ''.join(lines)


def resolve_pending_index(index_text, items):
    if not items:
        return None, 'No pending captures.'
    if index_text == 'latest':
        item = dict(items[-1])
        item['index'] = len(items)
        return item, None
    try:
        idx = int(index_text)
    except ValueError:
        return None, f"Invalid index: '{index_text}'. Use a number or 'latest'."
    if idx < 1 or idx > len(items):
        return None, f"Index {idx} out of range. {len(items)} pending capture(s)."
    item = dict(items[idx - 1])
    item['index'] = idx
    return item, None


def list_pending_captures():
    captures = []
    for fname in sorted(os.listdir(PENDING_DIR)):
        if not fname.endswith('.md') or fname == 'README.md':
            continue
        fpath = os.path.join(PENDING_DIR, fname)
        fm = parse_frontmatter(fpath)
        cid = fm.get('capture_id', '')
        ctype = fm.get('capture_type', '')
        created = fm.get('created_at', '')
        if cid:
            captures.append((cid, ctype, created, fname))
    return captures


def update_capture_frontmatter(filepath, status, processed_at=None):
    with open(filepath) as f:
        lines = f.readlines()
    in_fm = False
    new_lines = []
    for line in lines:
        stripped = line.rstrip('\n')
        if stripped == '---':
            in_fm = not in_fm
            new_lines.append(line)
            continue
        if in_fm:
            if stripped.startswith('status:'):
                new_lines.append(f'status: {status}\n')
            elif stripped.startswith('processed_at:'):
                val = processed_at if processed_at else ''
                new_lines.append(f'processed_at: {val}\n')
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    with open(filepath, 'w') as f:
        f.writelines(new_lines)


def move_capture_file(src, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    basename = os.path.basename(src)
    name, ext = os.path.splitext(basename)
    dst = os.path.join(dst_dir, basename)
    counter = 1
    while os.path.exists(dst):
        dst = os.path.join(dst_dir, f"{name}_{counter}{ext}")
        counter += 1
    os.rename(src, dst)
    return dst


def handle_list_pending(chat_id):
    result = call_action_api('/captures/pending')
    if result is None or not result.get('success'):
        action_api_unavailable_reply(chat_id)
        return
    pending = result.get('pending', [])
    count = result.get('count', 0)
    if count == 0:
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': 'No pending captures.'
        })
        return
    lines = [f'Pending captures: {count}']
    for item in pending[:10]:
        lines.append(f"\n{item['index']}. {item.get('capture_id', '')}\n   status: {item.get('status', '')}\n   created: {item.get('created_at', '')}")
    if count > 10:
        lines.append(f'\n... and {count - 10} more')
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': ''.join(lines)
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
        tg_api('sendMessage', {'chat_id': chat_id, 'text': f'Approve failed: {error}'})
        return
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': f'Approved: {result.get("capture_id", capture_id)}'
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
        tg_api('sendMessage', {'chat_id': chat_id, 'text': f'Reject failed: {error}'})
        return
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': f'Rejected: {result.get("capture_id", capture_id)}'
    })


def handle_p(chat_id):
    result = call_action_api('/captures/pending')
    if result is None or not result.get('success'):
        action_api_unavailable_reply(chat_id)
        return
    pending = result.get('pending', [])
    count = result.get('count', 0)
    if count == 0:
        tg_api('sendMessage', {'chat_id': chat_id, 'text': 'No pending captures.'})
        return
    lines = [f'Pending captures: {count}']
    for item in pending:
        cid = item.get('capture_id', '')
        preview = item.get('preview', '')
        summary = _extract_preview_line(preview) if preview else cid
        lines.append(f"\n{item['index']}. {summary}")
    lines.append('\n\nUse:\n/view 1\n/a 1\n/r 1')
    tg_api('sendMessage', {'chat_id': chat_id, 'text': ''.join(lines)})


def handle_view(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Usage: /view <number> or /view latest or /view <capture_id>'})
        return
    ref = parts[1].strip()
    if ref == 'latest':
        endpoint = '/captures/pending/latest'
    elif ref.isdigit():
        endpoint = f'/captures/pending/{ref}'
    elif ref.startswith('cap_'):
        endpoint = f'/captures/{ref}'
    else:
        tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Invalid argument. Use a number, "latest", or a capture_id.'})
        return
    result = call_action_api(endpoint)
    if result is None or not result.get('success'):
        tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Capture not found or unavailable. No action was taken.'})
        return
    capture = result['capture']
    cid = capture.get('capture_id', '')
    ctype = capture.get('status', '')
    created = capture.get('created_at', '')
    content = capture.get('content', '')
    max_len = 3500
    if len(content) > max_len:
        content = content[:max_len] + '\n... (truncated)'
    view_text = f"Capture: {cid}\nStatus: {ctype}\nCreated: {created}\n\n{content}"
    tg_api('sendMessage', {'chat_id': chat_id, 'text': view_text})


def handle_a(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    index_text = parts[1].strip() if len(parts) > 1 else ''
    if not index_text:
        result = call_action_api('/captures/pending')
        if result is None or not result.get('success'):
            action_api_unavailable_reply(chat_id)
            return
        pending = result.get('pending', [])
        if len(pending) == 0:
            tg_api('sendMessage', {'chat_id': chat_id, 'text': 'No pending captures.'})
            return
        if len(pending) > 1:
            tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Multiple pending captures. Use /p, then /a 1.'})
            return
        capture_id = pending[0].get('capture_id', '')
    else:
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
        tg_api('sendMessage', {'chat_id': chat_id, 'text': f'Approve failed: {error}'})
        return
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': f'Approved: {approve_result.get("capture_id", capture_id)}'
    })


def handle_r(text, chat_id):
    parts = text.strip().split(maxsplit=1)
    index_text = parts[1].strip() if len(parts) > 1 else ''
    if not index_text:
        result = call_action_api('/captures/pending')
        if result is None or not result.get('success'):
            action_api_unavailable_reply(chat_id)
            return
        pending = result.get('pending', [])
        if len(pending) == 0:
            tg_api('sendMessage', {'chat_id': chat_id, 'text': 'No pending captures.'})
            return
        if len(pending) > 1:
            tg_api('sendMessage', {'chat_id': chat_id, 'text': 'Multiple pending captures. Use /p, then /r 1.'})
            return
        capture_id = pending[0].get('capture_id', '')
    else:
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
        tg_api('sendMessage', {'chat_id': chat_id, 'text': f'Reject failed: {error}'})
        return
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': f'Rejected: {reject_result.get("capture_id", capture_id)}'
    })


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

    if cmd == '/p':
        handle_p(chat_id)
    elif cmd == '/list_pending':
        handle_list_pending(chat_id)
    elif cmd == '/view':
        handle_view(text, chat_id)
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
    args = parser.parse_args()

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
