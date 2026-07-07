"""Pure formatting layer for LifeOS Telegram Operator Cards (mobile-safe).

No I/O, no API calls, no state. Every function returns a formatted string.
"""

from datetime import datetime, timezone


def _iso_to_dt(iso_str):
    if not iso_str:
        return None
    try:
        s = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
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


def _top_line(title):
    return "\u256d\u2500 LIFEOS :: " + title


def _bottom_line():
    return "\u2570\u2500"


def _row(label, value):
    return "\u2502 " + label + "  " + str(value)


def format_box(title, rows=None, body=None, footer=None):
    parts = [_top_line(title)]
    if rows:
        for label, value in rows:
            parts.append(_row(label, value))
    parts.append(_bottom_line())
    if body:
        parts.append("")
        parts.append(body)
    if footer:
        parts.append("")
        parts.append(footer)
    return "\n".join(parts)


def format_capture_success(capture_id, event_id=None, queue_index=None,
                           created_at=None, now=None):
    rows = [
        ("STATE", "QUEUED"),
        ("AGE", format_age(created_at, now=now) if created_at else "now"),
        ("SOURCE", "Telegram"),
    ]
    text_parts = ["Captured for review.", "", "ID", capture_id]
    if event_id:
        text_parts.append("")
        text_parts.append("EVENT")
        text_parts.append(event_id)
    body = "\n".join(text_parts)
    footer = "No vault processing was performed.\nUse /p to review the queue."
    return format_box("CAPTURE", rows=rows, body=body, footer=footer)


def format_capture_failure():
    body = "LifeOS capture unavailable."
    footer = "NO ACTION"
    return format_box("CAPTURE", rows=[("STATE", "FAILED")], body=body, footer=footer)


def format_status_card(payload, now=None):
    pending = payload.get("pending_captures", "?")
    approved = payload.get("approved_unprocessed_captures", "?")
    rejected = payload.get("rejected_captures", "?")
    evt_count = payload.get("event_log_line_count", "?")
    evt_type = payload.get("last_event_type", "none")
    evt_time = payload.get("last_event_time", "")

    rows = [
        ("PENDING", str(pending)),
        ("APPROVED", str(approved)),
        ("REJECTED", str(rejected)),
        ("EVENTS", str(evt_count)),
    ]
    evt_line = f"Last: {evt_type} at {evt_time}" if evt_time else "Last: none"
    footer = "No action taken."
    return format_box("STATUS", rows=rows, body=evt_line, footer=footer)


def format_pending_queue(items, count=None, mode="capture-first", now=None):
    count = count if count is not None else len(items)
    if count == 0:
        return format_box("REVIEW QUEUE", body="No pending captures.")
    rows = [("PENDING", str(count))]
    listing = []
    for item in items:
        idx = item.get("index", "?")
        preview = item.get("preview", "") or item.get("capture_id", "")
        created_at = item.get("created_at")
        if created_at:
            age = format_age(created_at, now=now)
            listing.append(f"[{idx}] {age}   {preview[:40]}")
        else:
            listing.append(f"[{idx}] {preview[:40]}")
    body = "\n".join(listing)
    if mode == "review":
        footer = "/view 1 or /view1\n/a 1 or /a1\n/r 1 or /r1"
    else:
        footer = "/view 1 or /view1\n\nApprove/reject are disabled in capture-first mode."
    return format_box("REVIEW QUEUE", rows=rows, body=body, footer=footer)


def format_needs_index(command):
    usage = {"view": "/view 1 or /view1", "a": "/a 1 or /a1", "r": "/r 1 or /r1"}
    hint = usage.get(command, f"/{command} <index>")
    footer = f"Use:\n{hint}\n\nNo action was taken."
    return format_box("REVIEW", rows=[("STATE", "NEEDS INDEX")], footer=footer)


def format_review_failed(reason):
    reason_label = reason.replace("_", " ")
    rows = [("STATE", "NO ACTION"), ("REASON", reason_label)]
    footer = "No capture was rejected. No files were moved."
    return format_box("REVIEW FAILED", rows=rows, footer=footer)


def format_capture_first_blocked():
    rows = [("STATE", "NO ACTION"), ("MODE", "capture-first")]
    body = "Approve/reject commands are disabled right now."
    footer = "No capture was approved. No capture was rejected. No files were moved.\n\nUse /p or /view1 for read-only review."
    return format_box("REVIEW DISABLED", rows=rows, body=body, footer=footer)


def format_review_disabled():
    body = "Review commands are disabled in capture-first mode."
    footer = "No files were moved. No action was taken."
    return format_box("REVIEW", rows=[("STATE", "DISABLED")], body=body, footer=footer)


def format_unauthorized():
    return format_box("ACCESS", rows=[("STATE", "DENIED")],
                      body="You are not authorized to use this bot.",
                      footer="NO ACTION")


def format_action_api_unavailable():
    return format_box("ACTION API", rows=[("STATE", "UNAVAILABLE")],
                      body="LifeOS review unavailable.",
                      footer="NO ACTION")


def format_status_api_unavailable():
    return format_box("STATUS API", rows=[("STATE", "UNAVAILABLE")],
                      body="LifeOS status unavailable.",
                      footer="NO ACTION")
