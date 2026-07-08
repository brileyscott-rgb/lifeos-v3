import json
import os
import sys
import tempfile
import unittest

SRC = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.realpath(SRC))
import review_packet_builder


def _write_draft(path, capture_id="cap_test001", **extra_frontmatter):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("---\n")
        f.write(f"type: capture_review_draft\n")
        f.write(f"capture_id: {capture_id}\n")
        f.write(f"source: desktop\n")
        f.write(f"capture_type: text\n")
        f.write(f"status: buffer_review\n")
        f.write(f"schema_version: 1\n")
        for k, v in extra_frontmatter.items():
            f.write(f"{k}: {v}\n")
        f.write("---\n")
        f.write("# Capture Review Draft\n")
        f.write("Test content.\n")


class TestReviewPacketBuilder(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.tmp, "input")
        self.output_dir = os.path.join(self.tmp, "output")
        os.makedirs(self.input_dir, exist_ok=True)

    def test_creates_packet_from_draft(self):
        _write_draft(os.path.join(self.input_dir, "cap_test001_draft.md"))
        packets = list(review_packet_builder.build_packets(self.input_dir, self.output_dir))
        self.assertEqual(len(packets), 1)
        self.assertTrue(os.path.isfile(packets[0]))

    def test_dry_run_creates_nothing(self):
        _write_draft(os.path.join(self.input_dir, "draft.md"))
        list(review_packet_builder.build_packets(self.input_dir, self.output_dir, dry_run=True))
        self.assertFalse(os.path.isdir(self.output_dir) and os.listdir(self.output_dir))

    def test_idempotent_rerun(self):
        _write_draft(os.path.join(self.input_dir, "draft.md"))
        list(review_packet_builder.build_packets(self.input_dir, self.output_dir))
        list(review_packet_builder.build_packets(self.input_dir, self.output_dir))
        count = len(os.listdir(self.output_dir))
        self.assertEqual(count, 1)

    def test_limit_works(self):
        for i in range(3):
            _write_draft(os.path.join(self.input_dir, f"draft_{i}.md"), capture_id=f"cap_{i}")
        packets = list(review_packet_builder.build_packets(self.input_dir, self.output_dir, limit=2))
        self.assertEqual(len(packets), 2)

    def test_refuses_canonical_vault_output(self):
        _write_draft(os.path.join(self.input_dir, "draft.md"))
        with self.assertRaises(ValueError):
            list(review_packet_builder.build_packets(
                self.input_dir, "/home/lifeos/10_Vaults/LifeOS/packets"))

    def test_no_source_mutation(self):
        draft_path = os.path.join(self.input_dir, "draft.md")
        _write_draft(draft_path)
        before = open(draft_path, "r").read()
        list(review_packet_builder.build_packets(self.input_dir, self.output_dir))
        after = open(draft_path, "r").read()
        self.assertEqual(before, after)

    def test_packet_contains_safety_warning(self):
        _write_draft(os.path.join(self.input_dir, "draft.md"))
        packets = list(review_packet_builder.build_packets(self.input_dir, self.output_dir))
        content = open(packets[0], "r").read()
        self.assertIn("not been imported", content.lower())

    def test_skips_non_markdown_files(self):
        _write_draft(os.path.join(self.input_dir, "draft.md"))
        with open(os.path.join(self.input_dir, "notes.txt"), "w") as f:
            f.write("not a draft")
        packets = list(review_packet_builder.build_packets(self.input_dir, self.output_dir))
        self.assertEqual(len(packets), 1)

    def test_empty_input_dir_returns_zero(self):
        packets = list(review_packet_builder.build_packets(self.input_dir, self.output_dir))
        self.assertEqual(len(packets), 0)


if __name__ == "__main__":
    unittest.main()
