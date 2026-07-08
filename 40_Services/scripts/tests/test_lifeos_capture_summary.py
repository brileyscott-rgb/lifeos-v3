import json
import os
import sys
import tempfile
import unittest

SRC = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.realpath(SRC))
import lifeos_capture_summary


class TestCaptureSummary(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.queue_path = os.path.join(self.tmp, "captures.jsonl")
        self.processed_dir = os.path.join(self.tmp, "processed")
        os.makedirs(self.processed_dir, exist_ok=True)

    def _write_queue(self, lines):
        os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)
        with open(self.queue_path, "w") as f:
            for line in lines:
                if isinstance(line, str):
                    f.write(line + "\n")
                else:
                    f.write(json.dumps(line, sort_keys=True) + "\n")

    def _capture(self, source="desktop", capture_type="text", **overrides):
        c = {
            "capture_id": "cap_test",
            "received_at": "2026-01-01T00:00:00Z",
            "source": source,
            "capture_type": capture_type,
            "content": "test content",
            "url": "",
            "title": "",
            "tags": [],
            "priority": "normal",
            "client": "",
            "metadata": {},
            "status": "queued",
            "raw_payload": {},
            "auth_method": "none",
            "schema_version": 1,
        }
        c.update(overrides)
        return c

    def test_missing_queue_returns_zero_summary(self):
        s = lifeos_capture_summary.get_summary("/nonexistent.jsonl")
        self.assertFalse(s.queue_exists)
        self.assertEqual(s.queue_count, 0)

    def test_valid_queue_counts_sources(self):
        self._write_queue([
            self._capture(source="desktop"),
            self._capture(source="manual"),
            self._capture(source="desktop"),
        ])
        s = lifeos_capture_summary.get_summary(self.queue_path)
        self.assertTrue(s.queue_exists)
        self.assertEqual(s.queue_count, 3)
        self.assertEqual(s.sources_breakdown.get("desktop"), 2)
        self.assertEqual(s.sources_breakdown.get("manual"), 1)

    def test_valid_queue_counts_types(self):
        self._write_queue([
            self._capture(capture_type="text"),
            self._capture(capture_type="url"),
        ])
        s = lifeos_capture_summary.get_summary(self.queue_path)
        self.assertEqual(s.types_breakdown.get("text"), 1)
        self.assertEqual(s.types_breakdown.get("url"), 1)

    def test_malformed_line_counted(self):
        self._write_queue([
            json.dumps(self._capture(), sort_keys=True),
            "not valid json",
        ])
        s = lifeos_capture_summary.get_summary(self.queue_path)
        self.assertEqual(s.malformed_count, 1)

    def test_text_output_no_capture_body(self):
        self._write_queue([self._capture(content="secret capture text")])
        s = lifeos_capture_summary.get_summary(self.queue_path)
        text = lifeos_capture_summary.format_text(s)
        self.assertNotIn("secret capture text", text)

    def test_json_output_valid(self):
        self._write_queue([self._capture()])
        s = lifeos_capture_summary.get_summary(self.queue_path)
        j = json.dumps(lifeos_capture_summary.to_dict(s))
        data = json.loads(j)
        self.assertEqual(data["queue_count"], 1)
        self.assertTrue(data["queue_exists"])

    def test_processed_markdown_count(self):
        self._write_queue([self._capture()])
        os.makedirs(self.processed_dir, exist_ok=True)
        with open(os.path.join(self.processed_dir, "test.md"), "w") as f:
            f.write("---\n---\n")
        s = lifeos_capture_summary.get_summary(self.queue_path, self.processed_dir)
        self.assertEqual(s.processed_markdown_count, 1)

    def test_newest_capture_id_reported(self):
        self._write_queue([
            self._capture(capture_id="cap_old", received_at="2025-01-01T00:00:00Z"),
            self._capture(capture_id="cap_new", received_at="2026-01-01T00:00:00Z"),
        ])
        s = lifeos_capture_summary.get_summary(self.queue_path)
        self.assertEqual(s.newest_capture_id, "cap_new")


if __name__ == "__main__":
    unittest.main()
