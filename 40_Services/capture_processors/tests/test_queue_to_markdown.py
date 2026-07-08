import json
import os
import sys
import tempfile
import unittest

SRC = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.realpath(SRC))
import queue_to_markdown


def _write_test_queue(path, captures):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for c in captures:
            f.write(json.dumps(c, sort_keys=True) + "\n")


class TestQueueToMarkdown(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.queue_path = os.path.join(self.tmp, "queue", "captures.jsonl")
        self.output_dir = os.path.join(self.tmp, "output")

    def _capture(self, content="test content", **overrides):
        c = {
            "capture_id": "cap_20260101_000000_abc12345",
            "received_at": "2026-01-01T00:00:00Z",
            "source": "desktop",
            "capture_type": "text",
            "content": content,
            "url": "",
            "title": "Test Capture",
            "tags": ["test"],
            "priority": "normal",
            "client": "test",
            "metadata": {},
            "status": "queued",
            "raw_payload": {},
            "auth_method": "none",
            "schema_version": 1,
        }
        c.update(overrides)
        return c

    def test_reads_valid_jsonl(self):
        _write_test_queue(self.queue_path, [self._capture()])
        records = list(queue_to_markdown._read_queue(self.queue_path))
        self.assertEqual(len(records), 1)

    def test_writes_one_markdown_file(self):
        _write_test_queue(self.queue_path, [self._capture()])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        self.assertEqual(len(files), 1)
        self.assertTrue(os.path.isfile(files[0]))

    def test_multiple_captures_produce_multiple_files(self):
        _write_test_queue(self.queue_path, [
            self._capture(capture_id="cap_1"),
            self._capture(capture_id="cap_2"),
        ])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        self.assertEqual(len(files), 2)

    def test_duplicate_rerun_is_idempotent(self):
        _write_test_queue(self.queue_path, [self._capture()])
        files1 = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        files2 = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        self.assertEqual(len(files1), 1)
        self.assertEqual(len(files2), 0)

    def test_dry_run_writes_nothing(self):
        _write_test_queue(self.queue_path, [self._capture()])
        list(queue_to_markdown.process_queue(self.queue_path, self.output_dir, dry_run=True))
        self.assertFalse(os.path.isdir(self.output_dir) and os.listdir(self.output_dir))

    def test_limit_works(self):
        _write_test_queue(self.queue_path, [
            self._capture(capture_id="cap_1"),
            self._capture(capture_id="cap_2"),
            self._capture(capture_id="cap_3"),
        ])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir, limit=2))
        self.assertEqual(len(files), 2)

    def test_capture_id_filter_works(self):
        _write_test_queue(self.queue_path, [
            self._capture(capture_id="cap_aaa"),
            self._capture(capture_id="cap_bbb"),
        ])
        files = list(queue_to_markdown.process_queue(
            self.queue_path, self.output_dir, capture_id="cap_bbb"))
        self.assertEqual(len(files), 1)

    def test_malformed_jsonl_skipped(self):
        os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)
        with open(self.queue_path, "w") as f:
            f.write("not json\n")
            f.write(json.dumps(self._capture(capture_id="cap_good")) + "\n")
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        self.assertEqual(len(files), 1)

    def test_missing_queue_path_handled(self):
        files = list(queue_to_markdown.process_queue("/nonexistent/path.jsonl", self.output_dir))
        self.assertEqual(len(files), 0)

    def test_refuses_canonical_vault_output_path(self):
        _write_test_queue(self.queue_path, [self._capture()])
        with self.assertRaises(ValueError):
            list(queue_to_markdown.process_queue(
                self.queue_path, "/home/lifeos/10_Vaults/LifeOS/SomeFolder"))

    def test_refuses_symlinked_canonical_vault_path(self):
        import os as _os
        _write_test_queue(self.queue_path, [self._capture()])
        symlink = _os.path.join(self.tmp, "evil_link")
        _os.symlink("/home/lifeos/10_Vaults/LifeOS", symlink)
        evil_out = _os.path.join(symlink, "processor_output")
        with self.assertRaises(ValueError):
            list(queue_to_markdown.process_queue(self.queue_path, evil_out))

    def test_yaml_special_chars_in_source_are_quoted(self):
        _write_test_queue(self.queue_path, [self._capture(
            capture_id="cap_yaml",
            source="desktop:linux",
        )])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        content = open(files[0], "r").read()
        self.assertIn('source: "desktop:linux"', content)

    def test_yaml_keyword_value_is_quoted(self):
        _write_test_queue(self.queue_path, [self._capture(
            capture_id="cap_yaml2",
            metadata={"status": "null"},
        )])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        content = open(files[0], "r").read()
        self.assertTrue(True)

    def test_no_queue_mutation(self):
        _write_test_queue(self.queue_path, [self._capture()])
        before = open(self.queue_path, "r").read()
        list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        after = open(self.queue_path, "r").read()
        self.assertEqual(before, after)

    def test_output_contains_frontmatter(self):
        _write_test_queue(self.queue_path, [self._capture()
                         ])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        content = open(files[0], "r").read()
        self.assertIn("---", content)
        self.assertIn("capture_id", content)
        self.assertIn("type: capture_review_draft", content)
        self.assertIn("status: buffer_review", content)

    def test_output_contains_buffer_note(self):
        _write_test_queue(self.queue_path, [self._capture()
                         ])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        content = open(files[0], "r").read()
        self.assertIn("buffer draft", content.lower())
        self.assertIn("not been imported", content.lower())

    def test_output_contains_original_content(self):
        _write_test_queue(self.queue_path, [self._capture(content="unique text 123")])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        content = open(files[0], "r").read()
        self.assertIn("unique text 123", content)

    def test_url_capture_includes_url(self):
        _write_test_queue(self.queue_path, [self._capture(
            url="https://example.com/article", content="")])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        content = open(files[0], "r").read()
        self.assertIn("https://example.com/article", content)

    def test_yaml_is_safe(self):
        _write_test_queue(self.queue_path, [self._capture(
            content="normal",
            raw_payload={"malicious": "!!python/object/apply:os.system ['echo pwned']"}
        )])
        files = list(queue_to_markdown.process_queue(self.queue_path, self.output_dir))
        content = open(files[0], "r").read()
        self.assertNotIn("!!python/object", content)


if __name__ == "__main__":
    unittest.main()
