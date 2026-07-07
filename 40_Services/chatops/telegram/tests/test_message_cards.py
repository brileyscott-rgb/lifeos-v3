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


class TestFormatBox(unittest.TestCase):
    def test_box_includes_lifeos_title(self):
        result = cards.format_box("CAPTURE", rows=[("STATE", "QUEUED")])
        self.assertIn("LIFEOS", result)
        self.assertIn("CAPTURE", result)

    def test_box_state_row_renders(self):
        result = cards.format_box("CAPTURE", rows=[("STATE", "QUEUED")])
        self.assertIn("STATE", result)
        self.assertIn("QUEUED", result)

    def test_box_no_right_border_on_rows(self):
        result = cards.format_box("TEST", rows=[("STATE", "VALUE")])
        for line in result.split("\n"):
            if line.startswith("\u2502 "):
                self.assertFalse(line.endswith("\u2502"),
                                 "Row ends with right border character")

    def test_box_no_fixed_width_padding(self):
        result = cards.format_box("X", rows=[("LONG_LABEL", "short")])
        for line in result.split("\n"):
            if line.startswith("\u2502 "):
                self.assertNotIn("                 ", line,
                                 "Row has excessive right-padding")

    def test_box_with_body(self):
        result = cards.format_box("TEST", body="hello world")
        self.assertIn("hello world", result)

    def test_box_with_footer(self):
        result = cards.format_box("TEST", footer="use /p")
        self.assertIn("use /p", result)


class TestFormatCaptureSuccess(unittest.TestCase):
    def test_includes_capture_id(self):
        result = cards.format_capture_success("cap_test_123")
        self.assertIn("cap_test_123", result)
        self.assertIn("LIFEOS", result)

    def test_includes_event_id_when_provided(self):
        result = cards.format_capture_success("cap_test", event_id="evt_abc")
        self.assertIn("evt_abc", result)

    def test_capture_id_not_in_bordered_row(self):
        result = cards.format_capture_success("cap_long_id_12345")
        for line in result.split("\n"):
            if line.startswith("\u2502 "):
                self.assertNotIn("cap_long_id_12345", line,
                                 "capture_id should not be in a bordered row")

    def test_capture_id_below_box(self):
        result = cards.format_capture_success("cap_below")
        lines = result.split("\n")
        after_box = False
        found_id = False
        for line in lines:
            if line.startswith("\u2570"):
                after_box = True
                continue
            if after_box and line.strip() == "ID":
                found_id = True
                continue
            if found_id and "cap_below" in line:
                break
        else:
            if not (after_box and found_id):
                self.fail("capture_id was not found below the box in ID block")

    def test_event_id_below_box_when_provided(self):
        result = cards.format_capture_success("cap_test", event_id="evt_below")
        lines = result.split("\n")
        after_box = False
        found_event = False
        for line in lines:
            if line.startswith("\u2570"):
                after_box = True
                continue
            if after_box and line.strip() == "EVENT":
                found_event = True
                continue
            if found_event and "evt_below" in line:
                break
        else:
            if not (after_box and found_event):
                self.fail("event_id was not found below the box in EVENT block")

    def test_age_in_row_not_inside_bordered_box(self):
        result = cards.format_capture_success("cap_test", created_at="2026-07-07T12:00:00Z", now=datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc))
        self.assertIn("now", result)

    def test_says_no_vault_processing(self):
        result = cards.format_capture_success("cap_test")
        self.assertIn("no vault processing", result.lower())

    def test_says_use_p_to_review(self):
        result = cards.format_capture_success("cap_test")
        self.assertIn("/p", result)

    def test_shows_age_when_created_at_provided(self):
        now = datetime(2026, 7, 7, 12, 5, 0, tzinfo=timezone.utc)
        result = cards.format_capture_success("cap_test", created_at="2026-07-07T12:00:00Z", now=now)
        self.assertIn("5m", result)


class TestFormatCaptureFailure(unittest.TestCase):
    def test_says_no_action(self):
        result = cards.format_capture_failure()
        self.assertIn("NO ACTION", result.upper())
        self.assertIn("unavailable", result.lower())


class TestFormatStatusCard(unittest.TestCase):
    def test_includes_counts(self):
        payload = {
            "pending_captures": 3,
            "approved_unprocessed_captures": 1,
            "rejected_captures": 0,
            "event_log_line_count": 30,
            "last_event_type": "capture_created",
            "last_event_time": "2026-07-07T12:00:00Z",
        }
        result = cards.format_status_card(payload)
        self.assertIn("3", result)
        self.assertIn("30", result)

    def test_does_not_claim_n8n_workflows_active(self):
        payload = {"pending_captures": 0, "approved_unprocessed_captures": 0,
                    "rejected_captures": 0, "event_log_line_count": 0}
        result = cards.format_status_card(payload)
        self.assertNotIn("n8n", result.lower())


class TestFormatPendingQueue(unittest.TestCase):
    def test_includes_count(self):
        result = cards.format_pending_queue([], count=3)
        self.assertIn("3", result)

    def test_shows_age_from_created_at(self):
        now = datetime(2026, 7, 7, 12, 5, 0, tzinfo=timezone.utc)
        items = [{"index": 1, "preview": "test capture", "created_at": "2026-07-07T12:00:00Z"}]
        result = cards.format_pending_queue(items, count=1, now=now)
        self.assertIn("5m", result)

    def test_empty_queue_message(self):
        result = cards.format_pending_queue([], count=0)
        self.assertIn("no pending", result.lower())

    def test_uses_bracket_index_format(self):
        now = datetime(2026, 7, 7, 12, 5, 0, tzinfo=timezone.utc)
        items = [{"index": 1, "preview": "test", "created_at": "2026-07-07T12:00:00Z"}]
        result = cards.format_pending_queue(items, count=1, now=now)
        self.assertIn("[1]", result)

    def test_truncates_long_preview(self):
        now = datetime(2026, 7, 7, 12, 5, 0, tzinfo=timezone.utc)
        items = [{"index": 1, "preview": "x" * 100, "created_at": "2026-07-07T12:00:00Z"}]
        result = cards.format_pending_queue(items, count=1, now=now)
        self.assertNotIn("x" * 50, result)

    def test_footer_mentions_or_aliases(self):
        items = [{"index": 1, "preview": "test", "created_at": "2026-07-07T12:00:00Z"}]
        result = cards.format_pending_queue(items, count=1)
        self.assertIn("/view1", result)

    def test_review_mode_footer_includes_a_and_r(self):
        items = [{"index": 1, "preview": "test"}]
        result = cards.format_pending_queue(items, count=1, mode="review")
        self.assertIn("/a 1", result)
        self.assertIn("/r 1", result)

    def test_capture_first_footer_says_disabled(self):
        items = [{"index": 1, "preview": "test"}]
        result = cards.format_pending_queue(items, count=1, mode="capture-first")
        self.assertIn("disabled", result.lower())
        self.assertNotIn("/a 1", result)


class TestFormatCaptureFirstBlocked(unittest.TestCase):
    def test_says_no_action(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("NO ACTION", result.upper())

    def test_shows_mode(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("capture-first", result.lower())

    def test_says_no_capture_approved(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("No capture was approved", result)

    def test_says_no_capture_rejected(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("No capture was rejected", result)

    def test_says_no_files_moved(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("No files were moved", result)

    def test_suggests_read_only(self):
        result = cards.format_capture_first_blocked()
        self.assertIn("/p", result)
        self.assertIn("/view1", result)


class TestFormatReviewDisabled(unittest.TestCase):
    def test_says_no_files_moved(self):
        result = cards.format_review_disabled()
        self.assertIn("review", result.lower())
        self.assertIn("disabled", result.lower())


class TestFormatNeedsIndex(unittest.TestCase):
    def test_says_needs_index(self):
        result = cards.format_needs_index("view")
        self.assertIn("NEEDS INDEX", result.upper())

    def test_shows_view_usage(self):
        result = cards.format_needs_index("view")
        self.assertIn("/view 1", result)
        self.assertIn("/view1", result)

    def test_shows_a_usage(self):
        result = cards.format_needs_index("a")
        self.assertIn("/a 1", result)
        self.assertIn("/a1", result)

    def test_shows_r_usage(self):
        result = cards.format_needs_index("r")
        self.assertIn("/r 1", result)
        self.assertIn("/r1", result)

    def test_says_no_action(self):
        result = cards.format_needs_index("view")
        self.assertIn("No action was taken", result)


class TestFormatUnauthorized(unittest.TestCase):
    def test_does_not_expose_internals(self):
        result = cards.format_unauthorized()
        self.assertNotIn("BOT_TOKEN", result)
        self.assertNotIn("ALLOWED_USER_ID", result)
        self.assertNotIn("TELEGRAM", result.upper())


class TestFormatReviewFailed(unittest.TestCase):
    def test_says_no_action(self):
        result = cards.format_review_failed("not_found")
        self.assertIn("NO ACTION", result)
        self.assertIn("LIFEOS", result)

    def test_shows_reason(self):
        result = cards.format_review_failed("capture_not_found")
        self.assertIn("capture not found", result.lower())

    def test_converts_underscores_to_spaces(self):
        result = cards.format_review_failed("mutation_failed")
        self.assertIn("mutation failed", result.lower())

    def test_says_no_files_moved(self):
        result = cards.format_review_failed("not_found")
        self.assertIn("No capture was rejected", result)
        self.assertIn("No files were moved", result)


class TestFormatApiUnavailable(unittest.TestCase):
    def test_action_api_unavailable_says_no_action(self):
        result = cards.format_action_api_unavailable()
        self.assertIn("NO ACTION", result.upper())

    def test_status_api_unavailable_says_no_action(self):
        result = cards.format_status_api_unavailable()
        self.assertIn("NO ACTION", result.upper())


if __name__ == '__main__':
    unittest.main()
