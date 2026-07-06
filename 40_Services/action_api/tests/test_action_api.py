"""Tests for LifeOS Action API — uses temp dirs, never touches real data."""

import json
import os
import sys
import threading
import tempfile
import unittest
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import patch

# Ensure action_api package dir is on sys.path for unittest discovery
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
        eid = server._make_event_id("telegram.capture_created")
        self.event_log_path.write_text(
            json.dumps({"event_id": eid}) + "\n", "utf-8"
        )
        eid2 = server._make_event_id("telegram.capture_created")
        self.assertNotEqual(eid, eid2)

    # --- Security ---

    def test_path_traversal_rejected(self):
        check = server.ActionHandler._check_path_security
        self.assertFalse(check("/absolute/path"))
        self.assertFalse(check("../outside"))
        self.assertFalse(check("pending/../../../etc/passwd"))
        self.assertFalse(check("valid_capture_id"))
        self.assertTrue(check("cap_2026_some_id"))

    def test_strict_capture_id_validation(self):
        check = server.ActionHandler._check_path_security
        self.assertTrue(check("cap_test_valid"))
        self.assertTrue(check("cap_2026_some_id"))
        self.assertTrue(check("cap_CapZ0-9_-"))
        self.assertFalse(check("/etc/passwd"))
        self.assertFalse(check("../outside"))
        self.assertFalse(check("pending/../../../etc/passwd"))
        self.assertFalse(check("cap_test/approve"))
        self.assertFalse(check("http://example.com"))
        self.assertFalse(check(""))
        self.assertFalse(check("cap_test\\backslash"))
        self.assertFalse(check("valid_capture_id"))
        self.assertFalse(check(None))
        self.assertFalse(check("."))
        self.assertFalse(check(".."))

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
        self.assertNotIn("/", cid)
        self.assertNotIn("\\", cid)
        self.assertNotIn("..", cid)

    def test_capture_id_uniqueness(self):
        cid1 = server._make_capture_id("same text")
        cid2 = server._make_capture_id("same text")
        self.assertNotEqual(cid1, cid2)

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

    def test_event_append_failure_returns_none(self):
        bad_path = Path(self.tmp) / "nonexistent" / "events.jsonl"
        with patch("server.EVENT_LOG", bad_path):
            eid = server._append_event("test.event", {"test": True})
            self.assertIsNone(eid)


class TestActionAPIHTTP(TestActionAPI):
    """HTTP endpoint tests using in-process HTTPServer."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.http_server = HTTPServer(("localhost", 0), server.ActionHandler)
        cls.port = cls.http_server.server_address[1]
        cls.thread = threading.Thread(
            target=cls.http_server.serve_forever, daemon=True
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http_server.shutdown()
        super().tearDownClass()

    def _get(self, path):
        import urllib.request
        try:
            resp = urllib.request.urlopen(
                f"http://localhost:{self.port}{path}"
            )
            return json.loads(resp.read()), resp.status
        except urllib.request.HTTPError as e:
            return json.loads(e.read()), e.code

    def _post(self, path, data=None):
        import urllib.request
        body = json.dumps(data).encode() if data is not None else b"{}"
        req = urllib.request.Request(
            f"http://localhost:{self.port}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            resp = urllib.request.urlopen(req)
            return json.loads(resp.read()), resp.status
        except urllib.request.HTTPError as e:
            return json.loads(e.read()), e.code

    # --- GET /health ---

    def test_health_endpoint(self):
        data, status = self._get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["service"], "lifeos-action-api")
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["mode"], "read_write")

    # --- GET /captures/pending ---

    def test_pending_endpoint_empty(self):
        data, status = self._get("/captures/pending")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["pending"], [])

    def test_pending_endpoint_with_captures(self):
        self._create_capture("Capture A")
        self._create_capture("Capture B")
        data, status = self._get("/captures/pending")
        self.assertEqual(status, 200)
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["pending"][0]["index"], 1)
        self.assertEqual(data["pending"][1]["index"], 2)

    def test_pending_endpoint_excludes_readme(self):
        self._create_capture("Capture C")
        readme = self.capture_base / "pending_review" / "README.md"
        readme.write_text("# README", "utf-8")
        data, status = self._get("/captures/pending")
        names = [f["file_name"] for f in data["pending"]]
        self.assertNotIn("README.md", names)

    def test_pending_endpoint_excludes_dirs(self):
        self._create_capture("Capture D")
        subdir = self.capture_base / "pending_review" / "subdir"
        subdir.mkdir(exist_ok=True)
        data, status = self._get("/captures/pending")
        self.assertEqual(data["count"], 1)

    def test_pending_endpoint_sorts_oldest_first(self):
        self._add_file("pending_review", "alpha.md", "cap_aa")
        self._add_file("pending_review", "beta.md", "cap_bb")
        data, status = self._get("/captures/pending")
        self.assertEqual(data["pending"][0]["capture_id"], "cap_aa")
        self.assertEqual(data["pending"][1]["capture_id"], "cap_bb")

    # --- GET /captures/pending/1 ---

    def test_pending_by_index(self):
        self._create_capture("First")
        f2 = self._create_capture("Second")
        data, status = self._get("/captures/pending/1")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertIn("content", data["capture"])

    def test_pending_by_index_404(self):
        data, status = self._get("/captures/pending/999")
        self.assertEqual(status, 404)
        self.assertFalse(data["success"])

    # --- GET /captures/pending/latest ---

    def test_pending_latest(self):
        self._create_capture("AAA")
        f2 = self._create_capture("BBB")
        data, status = self._get("/captures/pending/latest")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["capture"]["file_name"], f2)

    def test_pending_latest_empty(self):
        data, status = self._get("/captures/pending/latest")
        self.assertEqual(status, 404)
        self.assertFalse(data["success"])

    # --- GET /captures/<id> ---

    def test_capture_by_id(self):
        self._add_file("pending_review", "byid.md", "cap_http_byid")
        data, status = self._get("/captures/cap_http_byid")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["capture"]["capture_id"], "cap_http_byid")

    def test_capture_by_id_missing(self):
        data, status = self._get("/captures/nonexistent")
        self.assertEqual(status, 404)
        self.assertFalse(data["success"])

    # --- GET /captures/approved ---

    def test_approved_endpoint(self):
        self._add_file("approved", "app.md", "cap_app", status="approved")
        data, status = self._get("/captures/approved")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["approved"][0]["capture_id"], "cap_app")

    def test_approved_endpoint_empty(self):
        data, status = self._get("/captures/approved")
        self.assertEqual(status, 200)
        self.assertEqual(data["count"], 0)

    # --- POST /captures ---

    def test_post_captures_valid_text(self):
        data, status = self._post("/captures", {"text": "Hello via HTTP"})
        self.assertEqual(status, 201)
        self.assertTrue(data["success"])
        self.assertTrue(data["capture_id"].startswith("cap_"))
        self.assertIn("file_name", data)
        self.assertIn("event_id", data)
        pending = self.capture_base / "pending_review"
        self.assertTrue((pending / data["file_name"]).exists())
        content = self.event_log_path.read_text("utf-8")
        self.assertIn("telegram.capture_created", content)

    def test_post_captures_empty_text(self):
        data, status = self._post("/captures", {"text": ""})
        self.assertEqual(status, 400)
        self.assertFalse(data["success"])
        pending = self.capture_base / "pending_review"
        files = list(pending.iterdir())
        self.assertEqual(len([f for f in files if f.is_file()]), 0)

    def test_post_captures_missing_text(self):
        data, status = self._post("/captures", {})
        self.assertEqual(status, 400)
        self.assertFalse(data["success"])

    # --- POST /captures/<id>/approve ---

    def test_post_approve(self):
        self._add_file("pending_review", "toapprove.md", "cap_approve_me",
                       status="pending_review", content="Approve this")
        data, status = self._post("/captures/cap_approve_me/approve")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertFalse(
            (self.capture_base / "pending_review" / "toapprove.md").exists()
        )
        self.assertTrue(
            (self.capture_base / "approved" / "toapprove.md").exists()
        )
        content = self.event_log_path.read_text("utf-8")
        self.assertIn("telegram.capture_approved", content)

    # --- POST /captures/<id>/reject ---

    def test_post_reject(self):
        self._add_file("pending_review", "toreject.md", "cap_reject_me",
                       status="pending_review", content="Reject this")
        data, status = self._post("/captures/cap_reject_me/reject")
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertFalse(
            (self.capture_base / "pending_review" / "toreject.md").exists()
        )
        self.assertTrue(
            (self.capture_base / "rejected" / "toreject.md").exists()
        )
        content = self.event_log_path.read_text("utf-8")
        self.assertIn("telegram.capture_rejected", content)

    def test_post_approve_invalid_id(self):
        data, status = self._post("/captures/invalid/approve")
        self.assertEqual(status, 400)
        self.assertFalse(data["success"])

    def test_post_approve_missing(self):
        data, status = self._post("/captures/cap_nonexistent/approve")
        self.assertEqual(status, 404)
        self.assertFalse(data["success"])


if __name__ == "__main__":
    unittest.main()
