"""Unit tests for LifeOS Status API."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure parent directory is on sys.path so 'app' can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_CAPTURE = Path(tempfile.mkdtemp(prefix="capture_test_"))
TEST_EVENT_LOG = Path(tempfile.mkdtemp(prefix="eventlog_test_")) / "events.jsonl"

# Patch module-level paths BEFORE importing app
_patcher_capture = patch("app.CAPTURE_BASE", TEST_CAPTURE)
_patcher_eventlog = patch("app.EVENT_LOG", TEST_EVENT_LOG)
_patcher_capture.start()
_patcher_eventlog.start()

# Now safe to import
from app import _count_files, _parse_event_log, _check_path_readable


def _make_subdirs():
    for d in ("pending_review", "approved", "rejected", "processed"):
        (TEST_CAPTURE / d).mkdir(parents=True, exist_ok=True)


def _write_event_log(lines):
    TEST_EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    TEST_EVENT_LOG.write_text("\n".join(lines) + "\n", "utf-8")


def _clear_event_log():
    if TEST_EVENT_LOG.exists():
        TEST_EVENT_LOG.unlink()


class TestCountFiles(unittest.TestCase):
    def setUp(self):
        _make_subdirs()

    def tearDown(self):
        shutil.rmtree(TEST_CAPTURE, ignore_errors=True)

    def test_empty_dir_returns_zero(self):
        self.assertEqual(_count_files(TEST_CAPTURE / "processed"), 0)

    def test_excludes_readme(self):
        (TEST_CAPTURE / "approved" / "README.md").write_text("readme", "utf-8")
        self.assertEqual(_count_files(TEST_CAPTURE / "approved"), 0)

    def test_counts_non_readme_files(self):
        (TEST_CAPTURE / "approved" / "capture1.md").write_text("a", "utf-8")
        (TEST_CAPTURE / "approved" / "capture2.md").write_text("b", "utf-8")
        self.assertEqual(_count_files(TEST_CAPTURE / "approved"), 2)

    def test_missing_dir_returns_neg_one(self):
        self.assertEqual(_count_files(TEST_CAPTURE / "nonexistent"), -1)


class TestParseEventLog(unittest.TestCase):
    def setUp(self):
        _clear_event_log()
        TEST_EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        _clear_event_log()

    def test_missing_file(self):
        valid, count, eid, etype, etime = _parse_event_log()
        self.assertFalse(valid)
        self.assertEqual(count, 0)

    def test_empty_file(self):
        _write_event_log([])
        valid, count, eid, etype, etime = _parse_event_log()
        self.assertTrue(valid)
        self.assertEqual(count, 0)

    def test_valid_jsonl(self):
        _write_event_log([
            '{"event_id":"evt_001","event_type":"test.a","occurred_at":"2026-01-01T00:00:00Z"}',
            '{"event_id":"evt_002","event_type":"test.b","occurred_at":"2026-01-02T00:00:00Z"}',
        ])
        valid, count, eid, etype, etime = _parse_event_log()
        self.assertTrue(valid)
        self.assertEqual(count, 2)
        self.assertEqual(eid, "evt_002")
        self.assertEqual(etype, "test.b")
        self.assertEqual(etime, "2026-01-02T00:00:00Z")

    def test_malformed_jsonl(self):
        _write_event_log([
            '{"event_id":"evt_001","event_type":"test.a","occurred_at":"2026-01-01T00:00:00Z"}',
            "not valid json",
        ])
        valid, count, eid, etype, etime = _parse_event_log()
        self.assertFalse(valid)
        self.assertEqual(count, 2)

    def test_single_event(self):
        _write_event_log([
            '{"event_id":"evt_001","event_type":"test.a","occurred_at":"2026-01-01T00:00:00Z"}',
        ])
        valid, count, eid, etype, etime = _parse_event_log()
        self.assertTrue(valid)
        self.assertEqual(count, 1)
        self.assertEqual(eid, "evt_001")

    def test_blank_lines_ignored(self):
        _write_event_log([
            '{"event_id":"evt_001","event_type":"test.a","occurred_at":"2026-01-01T00:00:00Z"}',
            "",
            '{"event_id":"evt_002","event_type":"test.b","occurred_at":"2026-01-02T00:00:00Z"}',
        ])
        valid, count, eid, etype, etime = _parse_event_log()
        self.assertTrue(valid)
        self.assertEqual(count, 3)
        self.assertEqual(eid, "evt_002")


class TestCheckPathReadable(unittest.TestCase):
    def test_existing_path(self):
        self.assertTrue(_check_path_readable(Path("/")))

    def test_nonexistent_path(self):
        self.assertFalse(_check_path_readable(Path("/nonexistent_path_xyz_123")))


class TestStatusResponseValues(unittest.TestCase):
    def setUp(self):
        _make_subdirs()
        _clear_event_log()

    def tearDown(self):
        shutil.rmtree(TEST_CAPTURE, ignore_errors=True)
        _clear_event_log()

    def test_pending_captures_included(self):
        (TEST_CAPTURE / "pending_review" / "test.md").write_text("x", "utf-8")
        pending = _count_files(TEST_CAPTURE / "pending_review")
        self.assertEqual(pending, 1)


if __name__ == "__main__":
    unittest.main()
