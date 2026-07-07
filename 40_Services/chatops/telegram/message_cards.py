"""Pure formatting layer for LifeOS Telegram Operator Cards.

No I/O, no API calls, no state. Every function returns a formatted string.
"""

from datetime import datetime, timezone

CARD_WIDTH = 37


def _iso_to_dt(iso_str):
    """Parse an ISO 8601 timestamp string to a datetime object."""
    if not iso_str:
        return None
    try:
        s = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def format_age(created_at, now=None):
    """Return a human-readable age like '5m' or '3h' from an ISO timestamp.

    now is provided for test injection; defaults to datetime.now(timezone.utc).
    """
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
    """Build the top border: ╭─ LIFEOS :: {title} ─...╮"""
    prefix = "\u256d\u2500 LIFEOS :: "
    inner = f"{prefix}{title}"
    pad = CARD_WIDTH - len(inner) - 2
    if pad < 1:
        pad = 1
    return inner + "\u2500" * pad + "\u256e"


def _bottom_line():
    return "\u2570" + "\u2500" * (CARD_WIDTH - 2) + "\u256f"


def _row(label, value):
    """Build a content row: │ LABEL   value ...│"""
    inner = f"{label}:".ljust(10) + str(value)
    return "\u2502 " + inner.ljust(CARD_WIDTH - 4) + "\u2502"


def format_box(title, rows=None, body=None, footer=None):
    """Build a LifeOS Operator Card.

    title: card title (shown as LIFEOS :: {title})
    rows: list of (label, value) tuples
    body: plain text appended below the box
    footer: plain text appended below the box after body
    """
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
    """Operator Card for a successful capture."""
    rows = [("STATE", "QUEUED"), ("ID", capture_id)]
    age = format_age(created_at, now=now) if created_at else "now"
    rows.insert(1, ("AGE", age))
    rows.append(("SOURCE", "Telegram"))
    if event_id:
        rows.append(("EVENT", event_id))
    body = "Captured for review."
    footer = "No vault processing was performed.\nUse /p to review the queue."
    return format_box("CAPTURE", rows=rows, body=body, footer=footer)


def format_capture_failure():
    """Operator Card when capture cannot be created."""
    body = "LifeOS capture unavailable."
    footer = "NO ACTION"
    return format_box("CAPTURE", rows=[("STATE", "FAILED")], body=body, footer=footer)


def format_status_card(payload, now=None):
    """Operator Card for /status response."""
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
    """Operator Card for /p (pending queue listing)."""
    count = count if count is not None else len(items)
    if count == 0:
        return format_box("REVIEW QUEUE", body="No pending captures.")
    rows = [("PENDING", str(count))]
    listing = []
    for item in items:
        idx = item.get("index", "?")
        preview = item.get("preview", "") or item.get("capture_id", "")
        age_str = ""
        created_at = item.get("created_at")
        if created_at:
            age_str = "  " + format_age(created_at, now=now)
        listing.append(f" {idx}. {preview[:40]}{age_str}")
    body = "\n".join(listing)
    footer = "/view 1  /a 1  /r 1"
    return format_box("REVIEW QUEUE", rows=rows, body=body, footer=footer)


def format_review_disabled():
    """Message shown when review commands are blocked in capture-first mode."""
    body = "Review commands are disabled in capture-first mode."
    footer = "No files were moved. No action was taken."
    return format_box("REVIEW", rows=[("STATE", "DISABLED")], body=body, footer=footer)


def format_unauthorized():
    """Message shown when an unauthorized sender is detected."""
    return format_box("ACCESS", rows=[("STATE", "DENIED")],
                      body="You are not authorized to use this bot.",
                      footer="NO ACTION")


def format_action_api_unavailable():
    """Message shown when the Action API cannot be reached."""
    return format_box("ACTION API", rows=[("STATE", "UNAVAILABLE")],
                      body="LifeOS review unavailable.",
                      footer="NO ACTION")


def format_status_api_unavailable():
    """Message shown when the Status API cannot be reached."""
    return format_box("STATUS API", rows=[("STATE", "UNAVAILABLE")],
                      body="LifeOS status unavailable.",
                      footer="NO ACTION")
