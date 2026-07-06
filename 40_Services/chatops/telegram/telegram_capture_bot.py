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
EVENT_LOG = os.path.join(LIFEOS_ROOT, '50_Event_Log', 'events.jsonl')

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


def make_event_id(event_type):
    now = datetime.now(timezone.utc)
    suffix = event_type.replace('.', '_')
    return f"evt_{now.strftime('%Y%m%dT%H%M%S')}_{suffix}"


def append_event(event_type, details):
    lines = validate_event_log()
    event_id = make_event_id(event_type)
    event = {
        'event_id': event_id,
        'event_type': event_type,
        'occurred_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'actor': {
            'type': 'human',
            'id': f'telegram:{ALLOWED_USER_ID}'
        },
        'approval_tier': 'A1' if event_type == 'chatops.telegram.capture_received' else 'A0',
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
    msg = update.get('message', {})
    chat = msg.get('chat', {})
    sender_id = msg.get('from', {}).get('id')
    text = msg.get('text', '')
    chat_id = chat.get('id')

    if sender_id is None or chat_id is None:
        return

    if sender_id != ALLOWED_USER_ID:
        print(f"Unauthorized sender: {sender_id}")
        tg_api('sendMessage', {
            'chat_id': chat_id,
            'text': 'Unauthorized'
        })
        append_event('chatops.telegram.unauthorized_sender_rejected', {
            'source': 'telegram',
            'sender_rejected': True,
        })
        return

    cmd = (text or '').strip().lower().split()[0] if text else ''
    if cmd == '/capture':
        handle_capture(text, chat_id, sender_id, msg)
    elif cmd == '/help':
        handle_help(chat_id)
    elif cmd == '/status':
        handle_status(chat_id)
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
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    slug = slugify(content)
    capture_id = f"cap_{timestamp}_telegram_note_{slug}"

    file_base = f"{timestamp}_telegram_note_{slug}"
    note_path = os.path.join(NOTES_DIR, f"{file_base}.md")
    pending_path = os.path.join(PENDING_DIR, f"{file_base}.md")

    note_content = f"""# Telegram Capture Source

**Captured at:** {now.isoformat()}

```
{content}
```
"""
    with open(note_path, 'w') as f:
        f.write(note_content)

    event_id = make_event_id('telegram_capture_received')
    pending = f"""---
capture_id: {capture_id}
source: telegram
capture_type: note
status: pending_review
approval_required: true
created_at: {now.isoformat()}
processed_at:
target_domain:
target_project:
event_id: {event_id}
---

# Capture Summary

## Raw Message

```
{content}
```

## Parsed Intent

Quick note capture.

## Suggested Routing

Pending human review.

## Approval Decision

Pending.

## Processing Notes

Captured by local Telegram bot handler.
"""
    with open(pending_path, 'w') as f:
        f.write(pending)

    append_event('chatops.telegram.capture_received', {
        'capture_id': capture_id,
        'source': 'telegram',
        'capture_type': 'note',
        'pending_review': True,
        'bot_token_logged': False,
        'docker_services_started': False,
        'docker_images_pulled_or_built': False,
        'real_secrets_added': False,
        'old_lifeos_migration_started': False,
        'n8n_workflow_activated': False,
    })

    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': f'Captured: {capture_id}'
    })
    print(f"Captured: {capture_id}")
    print(f"  Note: {note_path}")
    print(f"  Pending: {pending_path}")


def handle_help(chat_id):
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': 'LifeOS ChatOps commands:\n/capture <text>\n/status\n/help'
    })
    append_event('chatops.telegram.help_requested', {
        'source': 'telegram',
    })


def handle_status(chat_id):
    pending_count = len([f for f in os.listdir(PENDING_DIR) if f.endswith('.md') and f != 'README.md'])
    note_count = len([f for f in os.listdir(NOTES_DIR) if f.endswith('.md') and f != 'README.md'])
    tg_api('sendMessage', {
        'chat_id': chat_id,
        'text': f'LifeOS ChatOps status:\nPending reviews: {pending_count}\nCaptures recorded: {note_count}'
    })
    append_event('chatops.telegram.status_requested', {
        'source': 'telegram',
        'pending_review_count': pending_count,
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


def main():
    parser = argparse.ArgumentParser(description='LifeOS Telegram Capture Bot - Local Test Handler')
    parser.add_argument('--check', action='store_true', help='Verify configuration and connectivity')
    parser.add_argument('--once', action='store_true', help='Process new updates once')
    parser.add_argument('--poll', action='store_true', help='Poll mode (foreground, Ctrl+C to stop)')
    parser.add_argument('--interval', type=int, default=3, help='Poll interval in seconds (default: 3)')
    args = parser.parse_args()

    if args.check:
        cmd_check()
    elif args.once:
        cmd_once()
    elif args.poll:
        cmd_poll(args.interval)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
