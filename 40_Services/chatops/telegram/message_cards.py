"""Pure formatting layer for LifeOS Telegram Operator Cards (mobile-safe).

No I/O, no API calls, no state. Every function returns a formatted string.
"""

from datetime import datetime, timezone


def _iso_to_dt(iso_str):
    if not iso_str:
        return None
    try:
        s = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def format_age(created_at, now=None):
    if not created_at:
        return "?"
    created = _iso_to_dt(created_at)
    if created is None:
        return "?"
    now = now or datetime.now(timezone.utc)
    delta = now - created
    mins = int(delta.total_seconds() / 60)
    if mins < 1:
        return "now"
    if mins < 60:
        return f"{mins}m"
    hours = mins // 60
    mins_rem = mins % 60
    if hours < 24:
        return f"{hours}h {mins_rem}m" if mins_rem else f"{hours}h"
    days = hours // 24
    return f"{days}d"


def _hdr(title):
    return title


def _kv(label, value):
    return f"{label}: {value}"


def format_card(title, rows=None, body=None, footer=None):
    parts = [_hdr(title)]
    if rows:
        for label, value in rows:
            parts.append(_kv(label, value))
    if body:
        parts.append("")
        parts.append(body)
    if footer:
        parts.append("")
        parts.append(footer)
    return "\n".join(parts)


def format_box(title, rows=None, body=None, footer=None):
    """Legacy adapter: delegates to plain-text format_card."""
    return format_card(title, rows=rows, body=body, footer=footer)


def format_capture_success(capture_id, event_id=None, queue_index=None,
                           created_at=None, now=None):
    rows = [
        ("ID", capture_id),
        ("Status", "pending_review"),
    ]
    if event_id:
        rows.append(("Event", event_id))
    footer = "Next: /p or /proposal <number>"
    return format_card("Capture saved", rows=rows, footer=footer)


def format_capture_failure():
    return format_card("Capture failed",
                       body="LifeOS capture unavailable.",
                       footer="NO ACTION")


def format_status_card(payload, now=None):
    pending = payload.get("pending_captures", "?")
    approved = payload.get("approved_unprocessed_captures", "?")
    evt_valid = payload.get("event_log_valid", False)
    evt_count = payload.get("event_log_line_count", "?")

    rows = [
        ("Status", "OK"),
        ("Mode", "local operator"),
    ]
    counts = f"Pending: {pending}  Approved: {approved}"
    evt_status = f"Event log: {'OK' if evt_valid else 'issue'} ({evt_count} lines)"
    body = "\n".join([counts, evt_status])
    footer = "Next: /p or /capture <text>"
    return format_card("LifeOS Status", rows=rows, body=body, footer=footer)


def format_pending_queue(items, count=None, mode="capture-first", now=None):
    count = count if count is not None else len(items)
    if count == 0:
        return format_card("Pending Captures", body="No pending captures.")
    lines = []
    for item in items:
        idx = item.get("index", "?")
        cap_id = item.get("capture_id", "")
        preview = item.get("preview", "") or cap_id
        first_line = preview.split("\n")[0][:60]
        ctype, _ = classify_capture(preview)
        lines.append(f"{idx}. {first_line}")
        lines.append(f"   ID: {cap_id}")
        lines.append(f"   Type: {ctype}")
    body = "\n".join(lines)
    footer = "Next: /view <number>"
    return format_card(f"Pending Captures: {count}", body=body, footer=footer)


def format_needs_index(command):
    usage = {"view": "/view 1", "a": "/a 1", "r": "/r 1"}
    hint = usage.get(command, f"/{command} <index>")
    return format_card("Review", rows=[("Status", "NEEDS INDEX")],
                       footer=f"Use: {hint}\n\nNo action was taken.")


def format_review_failed(reason):
    reason_label = reason.replace("_", " ")
    return format_card("Review failed",
                       rows=[("Reason", reason_label)],
                       footer="No action was taken.")


def format_capture_first_blocked():
    return format_card("Review disabled",
                       rows=[("Mode", "capture-first")],
                       body="Approve/reject commands are disabled right now.",
                       footer="Use /p or /view <n> for read-only review.\nNo action was taken.")


def format_review_disabled():
    return format_card("Review",
                       rows=[("Status", "DISABLED")],
                       body="Review commands are disabled in capture-first mode.",
                       footer="No action was taken.")


def format_unauthorized():
    return format_card("Access denied",
                       body="You are not authorized to use this bot.",
                       footer="NO ACTION")


def format_action_api_unavailable():
    return format_card("Action API",
                       rows=[("Status", "UNAVAILABLE")],
                       body="LifeOS review unavailable.",
                       footer="NO ACTION")


def format_status_api_unavailable():
    return format_card("Status API",
                       rows=[("Status", "UNAVAILABLE")],
                       body="LifeOS status unavailable.",
                       footer="NO ACTION")


def format_proposal(capture_id, index=None, title=None, capture_type=None,
                    suggested_route=None, next_action=None, created_at=None,
                    now=None):
    rows = [("Capture", str(index) if index else capture_id)]
    if title:
        rows.append(("Title", title))
    rows.append(("Type", capture_type or "unknown"))
    rows.append(("Route", suggested_route or "Inbox"))
    footer_parts = []
    if next_action:
        footer_parts.append(f"Next action: {next_action}")
    footer_parts.append("Reminder: approve/reject first; no vault write yet.")
    return format_card("Proposal V1", rows=rows,
                       footer="\n".join(footer_parts))


def format_proposal_invalid(target):
    return format_card("Proposal",
                       rows=[("Status", "INVALID")],
                       body=f"Could not find capture: {target}",
                       footer="Use /p to list pending captures.")


def format_proposal_api_unavailable():
    return format_card("Proposal",
                       rows=[("Status", "UNAVAILABLE")],
                       body="LifeOS proposal unavailable.",
                       footer="NO ACTION")


def classify_capture(text):
    if not text:
        return "unknown", "Inbox"
    t = text.strip().lower()
    if t.startswith(("http://", "https://")):
        return "link", "Reference/source"
    if t.startswith("idea:") or t.startswith("idea ") or "\nidea " in t:
        return "idea", "Ideas"
    if t.startswith("task:") or t.startswith("todo:") or t.startswith("task ") or t.startswith("todo "):
        return "task", "Action/task"
    if any(kw in t for kw in ("project", "update", "progress", "milestone")):
        return "project_update", "Project update"
    if len(t) < 140:
        return "note", "Inbox"
    return "unknown", "Inbox"


def infer_title(text, max_len=60):
    if not text:
        return "(untitled)"
    line = text.strip().split("\n")[0].strip()
    if line.startswith(("http://", "https://")):
        return line
    if len(line) <= max_len:
        return line
    return line[:max_len - 3].rstrip() + "..."
