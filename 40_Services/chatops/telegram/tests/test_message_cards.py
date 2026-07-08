"""Tests for message_cards.py formatting layer."""

import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import message_cards as cards


class TestFormatAge(unittest.TestCase):
    def test_age_now_for_recent(self):
        now = datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(cards.format_age("2026-07-07T12:00:00Z", now=now), "now")

    def test_age_minutes(self):
        now = datetime(2026, 7, 7, 12, 5, 0, tzinfo=timezone.utc)
        self.assertEqual(cards.format_age("2026-07-07T12:00:00Z", now=now), "5m")

    def test_age_hours(self):
        now = datetime(2026, 7, 7, 15, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(cards.format_age("2026-07-07T12:00:00Z", now=now), "3h")

    def test_age_hours_with_minutes(self):
        now = datetime(2026, 7, 7, 15, 20, 0, tzinfo=timezone.utc)
        self.assertEqual(cards.format_age("2026-07-07T12:00:00Z", now=now), "3h 20m")

    def test_age_days(self):
        now = datetime(2026, 7, 9, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(cards.format_age("2026-07-07T12:00:00Z", now=now), "2d")

    def test_age_empty_returns_question(self):
        self.assertEqual(cards.format_age(""), "?")
        self.assertEqual(cards.format_age(None), "?")


class TestFormatCard(unittest.TestCase):
    def test_card_includes_title(self):
        result = cards.format_card("CAPTURE", rows=[("Status", "QUEUED")])
        self.assertIn("CAPTURE", result)

    def test_card_kv_row_renders(self):
        result = cards.format_card("CAPTURE", rows=[("Status", "QUEUED")])
        self.assertIn("Status", result)
        self.assertIn("QUEUED", result)

    def test_card_with_body(self):
        result = cards.format_card("TEST", body="hello world")
        self.assertIn("hello world", result)

    def test_card_with_footer(self):
        result = cards.format_card("TEST", footer="use /p")
        self.assertIn("use /p", result)

    def test_card_no_box_drawing_chars(self):
        result = cards.format_card("TEST", rows=[("K", "V")])
        self.assertNotIn("\u2502", result)
        self.assertNotIn("\u256d", result)
        self.assertNotIn("\u2570", result)

    def test_format_box_delegates_to_format_card(self):
        result = cards.format_box("CAPTURE", rows=[("K", "V")])
        self.assertIn("CAPTURE", result)
        self.assertIn("K", result)


class TestFormatCaptureSuccess(unittest.TestCase):
    def test_includes_capture_id(self):
        result = cards.format_capture_success("cap_test_123")
        self.assertIn("cap_test_123", result)
        self.assertIn("Capture saved", result)

    def test_includes_event_id_when_provided(self):
        result = cards.format_capture_success("cap_test", event_id="evt_abc")
        self.assertIn("evt_abc", result)

    def test_shows_status_pending(self):
        result = cards.format_capture_success("cap_test")
        self.assertIn("pending_review", result)

    def test_suggests_next_commands(self):
        result = cards.format_capture_success("cap_test")
        self.assertIn("/p", result)
        self.assertIn("/proposal", result)


class TestFormatCaptureFailure(unittest.TestCase):
    def test_says_unavailable(self):
        result = cards.format_capture_failure()
        self.assertIn("unavailable", result.lower())

    def test_says_no_action(self):
        result = cards.format_capture_failure()
        self.assertIn("NO ACTION", result)


class TestFormatStatusCard(unittest.TestCase):
    def test_includes_counts(self):
        payload = {
            "pending_captures": 3,
            "approved_unprocessed_captures": 1,
            "rejected_captures": 0,
            "event_log_line_count": 30,
            "event_log_valid": True,
        }
        result = cards.format_status_card(payload)
        self.assertIn("3", result)
        self.assertIn("30", result)

    def test_shows_status_ok(self):
        payload = {"pending_captures": 0, "approved_unprocessed_captures": 0,
                    "rejected_captures": 0, "event_log_line_count": 0,
                    "event_log_valid": True}
        result = cards.format_status_card(payload)
        self.assertIn("Status", result)
        self.assertIn("OK", result)

    def test_shows_mode_local_operator(self):
        payload = {"pending_captures": 0, "approved_unprocessed_captures": 0,
                    "rejected_captures": 0, "event_log_line_count": 0,
                    "event_log_valid": True}
        result = cards.format_status_card(payload)
        self.assertIn("local operator", result.lower())

    def test_suggests_next_commands(self):
        payload = {"pending_captures": 0, "approved_unprocessed_captures": 0,
                    "rejected_captures": 0, "event_log_line_count": 0,
                    "event_log_valid": True}
        result = cards.format_status_card(payload)
        self.assertIn("/p", result)
        self.assertIn("/capture", result)


class TestFormatPendingQueue(unittest.TestCase):
    def test_includes_count(self):
        result = cards.format_pending_queue([], count=3)
        self.assertIn("3", result)

    def test_empty_queue_message(self):
        result = cards.format_pending_queue([], count=0)
        self.assertIn("no pending", result.lower())

    def test_uses_numbered_index_format(self):
        items = [{"index": 1, "preview": "test capture", "capture_id": "cap_1"}]
        result = cards.format_pending_queue(items, count=1)
        self.assertIn("1.", result)

    def test_shows_capture_id(self):
        items = [{"index": 1, "preview": "test", "capture_id": "cap_abc"}]
        result = cards.format_pending_queue(items, count=1)
        self.assertIn("cap_abc", result)

    def test_suggests_next_command(self):
        items = [{"index": 1, "preview": "test", "capture_id": "cap_x"}]
        result = cards.format_pending_queue(items, count=1)
        self.assertIn("/view", result)

    def test_review_mode_includes_a_and_r_hints(self):
        items = [{"index": 1, "preview": "test", "capture_id": "cap_x"}]
        result = cards.format_pending_queue(items, count=1, mode="review")
        self.assertIn("/view", result)

    def test_capture_first_footer_mentions_read_only(self):
        items = [{"index": 1, "preview": "test", "capture_id": "cap_x"}]
        result = cards.format_pending_queue(items, count=1, mode="capture-first")
        self.assertIn("/view", result)

    def test_no_age_in_pending_queue(self):
        items = [{"index": 1, "preview": "test", "capture_id": "cap_x",
                   "created_at": "2026-07-07T12:00:00Z"}]
        result = cards.format_pending_queue(items, count=1)
        self.assertNotIn("m", result.split("\n")[1])  # no age suffix on first item line


class TestFormatCaptureFirstBlocked(unittest.TestCase):
    def test_says_disabled(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("disabled", result.lower())

    def test_shows_mode(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("capture-first", result.lower())

    def test_suggests_read_only(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("/p", result)
        self.assertIn("/view", result)

    def test_says_no_action(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("No action was taken", result)


class TestFormatReviewDisabled(unittest.TestCase):
    def test_says_disabled(self):
        result = cards.format_review_disabled()
        self.assertIn("review", result.lower())
        self.assertIn("disabled", result.lower())


class TestFormatNeedsIndex(unittest.TestCase):
    def test_says_needs_index(self):
        result = cards.format_needs_index("view")
        self.assertIn("NEEDS INDEX", result)

    def test_shows_view_usage(self):
        result = cards.format_needs_index("view")
        self.assertIn("/view 1", result)

    def test_shows_a_usage(self):
        result = cards.format_needs_index("a")
        self.assertIn("/a 1", result)

    def test_shows_r_usage(self):
        result = cards.format_needs_index("r")
        self.assertIn("/r 1", result)

    def test_says_no_action(self):
        result = cards.format_needs_index("view")
        self.assertIn("No action was taken", result)


class TestFormatUnauthorized(unittest.TestCase):
    def test_does_not_expose_internals(self):
        result = cards.format_unauthorized()
        self.assertNotIn("BOT_TOKEN", result)
        self.assertNotIn("ALLOWED_USER_ID", result)


class TestFormatReviewFailed(unittest.TestCase):
    def test_shows_reason(self):
        result = cards.format_review_failed("capture_not_found")
        self.assertIn("capture not found", result.lower())

    def test_converts_underscores_to_spaces(self):
        result = cards.format_review_failed("mutation_failed")
        self.assertIn("mutation failed", result.lower())

    def test_says_no_action(self):
        result = cards.format_review_failed("not_found")
        self.assertIn("No action was taken", result)


class TestFormatApiUnavailable(unittest.TestCase):
    def test_action_api_unavailable_says_no_action(self):
        result = cards.format_action_api_unavailable()
        self.assertIn("NO ACTION", result)

    def test_status_api_unavailable_says_no_action(self):
        result = cards.format_status_api_unavailable()
        self.assertIn("NO ACTION", result)


class TestFormatProposal(unittest.TestCase):
    def test_includes_capture_id(self):
        result = cards.format_proposal("cap_test", title="Test", capture_type="note")
        self.assertIn("cap_test", result)

    def test_includes_type_and_title(self):
        result = cards.format_proposal("cap_x", title="Hello", capture_type="idea")
        self.assertIn("Hello", result)
        self.assertIn("idea", result)

    def test_includes_route(self):
        result = cards.format_proposal("cap_x", title="T", capture_type="note",
                                        suggested_route="Inbox")
        self.assertIn("Inbox", result)

    def test_includes_approval_reminder(self):
        result = cards.format_proposal("cap_x", title="T", capture_type="note")
        self.assertIn("approve", result.lower())
        self.assertIn("no vault write", result.lower())

    def test_includes_next_action_when_provided(self):
        result = cards.format_proposal("cap_x", title="T", capture_type="task",
                                        next_action="Review and decide.")
        self.assertIn("Review and decide", result)

    def test_includes_index_when_provided(self):
        result = cards.format_proposal("cap_x", index=3, title="T", capture_type="note")
        self.assertIn("3", result.split("\n")[1])

    def test_proposal_invalid(self):
        result = cards.format_proposal_invalid("bad")
        self.assertIn("Could not find", result)

    def test_proposal_api_unavailable(self):
        result = cards.format_proposal_api_unavailable()
        self.assertIn("NO ACTION", result)


class TestClassifyCapture(unittest.TestCase):
    def test_link_type(self):
        ctype, route = cards.classify_capture("https://example.com/page")
        self.assertEqual(ctype, "link")
        self.assertEqual(route, "Reference/source")

    def test_idea_type(self):
        ctype, _ = cards.classify_capture("idea: build a new dashboard")
        self.assertEqual(ctype, "idea")

    def test_task_type(self):
        ctype, _ = cards.classify_capture("task: fix the login bug")
        self.assertEqual(ctype, "task")

    def test_todo_type(self):
        ctype, _ = cards.classify_capture("todo: clean up code")
        self.assertEqual(ctype, "task")

    def test_project_update_type(self):
        ctype, _ = cards.classify_capture("project milestone reached")
        self.assertEqual(ctype, "project_update")

    def test_note_type(self):
        ctype, _ = cards.classify_capture("just a quick note")
        self.assertEqual(ctype, "note")

    def test_unknown_type_long_text(self):
        ctype, _ = cards.classify_capture("x" * 150)
        self.assertEqual(ctype, "unknown")

    def test_empty_text(self):
        ctype, _ = cards.classify_capture("")
        self.assertEqual(ctype, "unknown")


class TestInferTitle(unittest.TestCase):
    def test_short_title(self):
        self.assertEqual(cards.infer_title("hello world"), "hello world")

    def test_title_from_first_line(self):
        self.assertEqual(cards.infer_title("first line\nsecond line"), "first line")

    def test_long_title_truncated(self):
        title = cards.infer_title("x" * 80)
        self.assertTrue(len(title) <= 60)

    def test_empty_title(self):
        self.assertEqual(cards.infer_title(""), "(untitled)")

    def test_url_title(self):
        self.assertEqual(cards.infer_title("https://example.com/page"), "https://example.com/page")


if __name__ == '__main__':
    unittest.main()
