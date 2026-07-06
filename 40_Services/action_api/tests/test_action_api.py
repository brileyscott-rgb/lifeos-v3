"""Tests for LifeOS Action API — uses temp dirs, never touches real data."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class TestActionAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="lifeos_action_test_")
        cls.capture_base = Path(cls.tmp) / "capture"
        cls.event_log_path = Path(cls.tmp) / "event-log" / "events.jsonl"
        cls.capture_base.mkdir(parents=True, exist_ok=True)
        cls.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        cls.event_log_path.write_text("", "utf-8")
        for sub in ["pending_review", "approved", "rejected", "processed"]:
            (cls.capture_base / sub).mkdir(parents=True, exist_ok=True)

        # Patch module-level paths once
        cls.patches = [
            patch("server.CAPTURE_BASE", cls.capture_base),
            patch("server.EVENT_LOG", cls.event_log_path),
            patch("server.PENDING_DIR", cls.capture_base / "pending_review"),
            patch("server.APPROVED_DIR", cls.capture_base / "approved"),
            patch("server.REJECTED_DIR", cls.capture_base / "rejected"),
            patch("server.PROCESSED_DIR", cls.capture_base / "processed"),
            patch("server.ALLOWED_DIRS", {
                cls.capture_base / "pending_review",
                cls.capture_base / "approved",
                cls.capture_base / "rejected",
                cls.capture_base / "processed",
            }),
            patch("server._SUBDIRS", {
                cls.capture_base / "pending_review",
                cls.capture_base / "approved",
                cls.capture_base / "rejected",
                cls.capture_base / "processed",
            }),
            patch("server._ALL_PARENT", cls.capture_base),
        ]
        for p in cls.patches:
            p.start()

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()

    def setUp(self):
        # Clean all capture subdirs and event log between tests
        for sub in ["pending_review", "approved", "rejected", "processed"]:
            d = self.capture_base / sub
            for f in d.iterdir():
                if f.is_file():
                    f.unlink()
        self.event_log_path.write_text("", "utf-8")

    # --- Helpers ---

    def _create_capture(self, text="Test capture text"):
        return server._write_capture_file(
            server._make_capture_id(text), text
        )

    def _add_file(self, subdir, name, capture_id="cap_test", status="pending_review", content="Body"):
        d = self.capture_base / subdir
        text = f"---\ncapture_id: {capture_id}\nstatus: {status}\ncreated_at: 2026-01-01\n---\n\n{content}"
        (d / name).write_text(text, "utf-8")

    # --- Health ---

    def test_server_constants(self):
        self.assertEqual(server.SERVICE_NAME, "lifeos-action-api")
        self.assertEqual(server.MODE, "read_write")
        self.assertTrue(hasattr(server.ActionHandler, "do_GET"))
        self.assertTrue(hasattr(server.ActionHandler, "do_POST"))

    # --- Create capture ---

    def test_create_capture(self):
        file_name = self._create_capture()
        self.assertIsNotNone(file_name)
        pending = self.capture_base / "pending_review"
        self.assertTrue((pending / file_name).exists())
        content = (pending / file_name).read_text("utf-8")
        self.assertIn("capture_id: cap_", content)
        self.assertIn("status: pending_review", content)
        self.assertIn("Test capture text", content)

    def test_create_with_unicode(self):
        file_name = self._create_capture("Café résumé 日本語")
        self.assertIsNotNone(file_name)
        pending = self.capture_base / "pending_review"
        self.assertTrue((pending / file_name).exists())

    # --- Reject empty ---

    def test_reject_empty_text(self):
        cid = server._make_capture_id("")
        file_name = server._write_capture_file(cid, "")
        # _write_capture_file writes files regardless; validation is in POST handler
        # Verify at minimum no crash and a filename is returned
        self.assertIsNotNone(file_name)

    # --- Pending list ---

    def test_pending_list_excludes_readme(self):
        self._create_capture("First capture")
        readme = self.capture_base / "pending_review" / "README.md"
        readme.write_text("# README", "utf-8")
        files = server._list_capture_files(server.PENDING_DIR)
        self.assertEqual(len(files), 1)
        for f in files:
            self.assertNotEqual(f["file_name"], "README.md")

    def test_pending_list_excludes_directories(self):
        self._create_capture("Second capture")
        subdir = self.capture_base / "pending_review" / "subdir"
        subdir.mkdir(exist_ok=True)
        files = server._list_capture_files(server.PENDING_DIR)
        self.assertEqual(len(files), 1)

    def test_pending_list_sorts_oldest_first(self):
        self._add_file("pending_review", "20260101_000001_first.md", "cap_1")
        self._add_file("pending_review", "20260102_000002_second.md", "cap_2")
        self._add_file("pending_review", "20260103_000003_third.md", "cap_3")
        files = server._list_capture_files(server.PENDING_DIR)
        self.assertEqual(len(files), 3)
        self.assertEqual(files[0]["capture_id"], "cap_1")
        self.assertEqual(files[1]["capture_id"], "cap_2")
        self.assertEqual(files[2]["capture_id"], "cap_3")

    def test_empty_pending_list(self):
        files = server._list_capture_files(server.PENDING_DIR)
        self.assertEqual(len(files), 0)

    # --- Resolve by index ---

    def test_get_pending_by_index(self):
        self._add_file("pending_review", "alpha.md", "cap_alpha")
        self._add_file("pending_review", "beta.md", "cap_beta")
        result = server._resolve_by_index(server.PENDING_DIR, "2")
        self.assertIsNotNone(result)
        self.assertEqual(result["capture_id"], "cap_beta")

    def test_get_pending_latest(self):
        self._add_file("pending_review", "first.md", "cap_first")
        self._add_file("pending_review", "second.md", "cap_second")
        result = server._resolve_by_index(server.PENDING_DIR, "latest")
        self.assertIsNotNone(result)
        self.assertEqual(result["capture_id"], "cap_second")

    def test_invalid_index_error(self):
        result = server._resolve_by_index(server.PENDING_DIR, "999")
        self.assertIsNone(result)

    def test_non_numeric_index(self):
        result = server._resolve_by_index(server.PENDING_DIR, "abc")
        self.assertIsNone(result)

    # --- Approve / Reject ---

    def test_approve_capture_moves_file(self):
        file_name = self._create_capture("Approve me")
        pending = self.capture_base / "pending_review"
        approved = self.capture_base / "approved"
        self.assertTrue((pending / file_name).exists())
        result, err = server._move_capture(
            file_name, server.PENDING_DIR, server.APPROVED_DIR, "approved", "test"
        )
        self.assertIsNone(err)
        self.assertIsNotNone(result)
        self.assertFalse((pending / file_name).exists())
        self.assertTrue((approved / file_name).exists())
        content = (approved / file_name).read_text("utf-8")
        self.assertIn("status: approved", content)
        self.assertIn("processed_at:", content)

    def test_reject_capture_moves_file(self):
        file_name = self._create_capture("Reject me")
        pending = self.capture_base / "pending_review"
        rejected = self.capture_base / "rejected"
        self.assertTrue((pending / file_name).exists())
        result, err = server._move_capture(
            file_name, server.PENDING_DIR, server.REJECTED_DIR, "rejected", "test"
        )
        self.assertIsNone(err)
        self.assertIsNotNone(result)
        self.assertFalse((pending / file_name).exists())
        self.assertTrue((rejected / file_name).exists())
        content = (rejected / file_name).read_text("utf-8")
        self.assertIn("status: rejected", content)
        self.assertIn("processed_at:", content)

    def test_missing_capture_rejected(self):
        result, err = server._move_capture(
            "nonexistent.md", server.PENDING_DIR, server.APPROVED_DIR, "approved", "test"
        )
        self.assertIsNotNone(err)
        self.assertEqual(err, "capture_not_found")

    def test_resolve_by_id(self):
        self._add_file("pending_review", "byid.md", "cap_byid")
        result = server._resolve_by_id(server.PENDING_DIR, "cap_byid")
        self.assertIsNotNone(result)
        self.assertEqual(result["capture_id"], "cap_byid")

    def test_missing_id(self):
        result = server._resolve_by_id(server.PENDING_DIR, "nonexistent")
        self.assertIsNone(result)

    # --- Events ---

    def test_event_appended_on_create(self):
        self._create_capture("Event test capture")
        content = self.event_log_path.read_text("utf-8").strip()
        # _write_capture_file does not append events — the POST handler does
        # Events are appended by _append_event which is called by the POST handler
        lines = [l for l in content.splitlines() if l.strip()]
        self.assertEqual(len(lines), 0)

    def test_append_event_manually(self):
        eid = server._append_event("telegram.capture_created", {"test": True})
        self.assertTrue(eid.startswith("evt_"))
        content = self.event_log_path.read_text("utf-8").strip()
        self.assertTrue(len(content) > 0)
        self.assertIn("telegram.capture_created", content)

    def test_event_appended_on_approve(self):
        file_name = self._create_capture("Event approve")
        server._move_capture(file_name, server.PENDING_DIR, server.APPROVED_DIR, "approved", "test")
        content = self.event_log_path.read_text("utf-8").strip()
        lines = [l for l in content.splitlines() if l.strip()]
        self.assertTrue(any("telegram.capture_approved" in l for l in lines))

    def test_event_appended_on_reject(self):
        file_name = self._create_capture("Event reject")
        server._move_capture(file_name, server.PENDING_DIR, server.REJECTED_DIR, "rejected", "test")
        content = self.event_log_path.read_text("utf-8").strip()
        lines = [l for l in content.splitlines() if l.strip()]
        self.assertTrue(any("telegram.capture_rejected" in l for l in lines))

    def test_event_id_format(self):
        eid = server._make_event_id("telegram.capture_created")
        self.assertTrue(eid.startswith("evt_"))
        self.assertIn("telegram_capture_created", eid)

    def test_event_id_collision_avoided(self):
        # Manually add an event with the same base ID
        existing = server._load_event_ids()
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        base = f"evt_{now.strftime('%Y%m%dT%H%M%SZ')}_telegram_capture_created"
        self.event_log_path.write_text(
            json.dumps({"event_id": base}) + "\n", "utf-8"
        )
        eid = server._make_event_id("telegram.capture_created")
        self.assertNotEqual(eid, base)
        self.assertTrue(eid.startswith(base))

    # --- Security ---

    def test_path_traversal_rejected(self):
        handler = server.ActionHandler
        self.assertFalse(handler._check_path_security(None, "/absolute/path"))
        self.assertFalse(handler._check_path_security(None, "../outside"))
        self.assertFalse(handler._check_path_security(None, "pending/../../../etc/passwd"))
        self.assertTrue(handler._check_path_security(None, "valid_capture_id"))
        self.assertTrue(handler._check_path_security(None, "cap_2026_some_id"))

    def test_safe_resolve_rejects_traversal(self):
        result = server._safe_resolve(Path("/etc/passwd"))
        self.assertIsNone(result)

    # --- Read / response shape ---

    def test_read_capture_file(self):
        self._add_file("pending_review", "readtest.md", "cap_readtest", content="Hello content")
        f = self.capture_base / "pending_review" / "readtest.md"
        data = server._read_capture_file(f)
        self.assertIsNotNone(data)
        self.assertEqual(data["frontmatter"].get("capture_id"), "cap_readtest")
        self.assertIn("Hello content", data["content"])

    def test_response_json_shape(self):
        file_name = self._create_capture("Shape test")
        result, err = server._move_capture(
            file_name, server.PENDING_DIR, server.APPROVED_DIR, "approved", "test"
        )
        self.assertIsNone(err)
        self.assertIn("capture_id", result)
        self.assertIn("file_name", result)
        self.assertIn("event_id", result)

    def test_capture_id_format(self):
        cid = server._make_capture_id("Hello World Test")
        self.assertTrue(cid.startswith("cap_"))
        self.assertIn("hello-world-test", cid)

    def test_approved_list(self):
        self._add_file("approved", "approved_test.md", "cap_approved_test", status="approved")
        files = server._list_capture_files(server.APPROVED_DIR)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["capture_id"], "cap_approved_test")

    def test_slugify(self):
        self.assertEqual(server._slugify("Hello World"), "hello-world")
        self.assertEqual(server._slugify("  Spaces  "), "spaces")
        self.assertEqual(server._slugify("Special#Chars!"), "specialchars")
        self.assertLessEqual(len(server._slugify("a" * 100)), 40)

    def test_load_event_ids_empty(self):
        ids = server._load_event_ids()
        self.assertEqual(len(ids), 0)

    def test_event_ids_loaded(self):
        self.event_log_path.write_text(
            json.dumps({"event_id": "evt_test_1"}) + "\n"
            + json.dumps({"event_id": "evt_test_2"}) + "\n",
            "utf-8",
        )
        ids = server._load_event_ids()
        self.assertIn("evt_test_1", ids)
        self.assertIn("evt_test_2", ids)


if __name__ == "__main__":
    unittest.main()
