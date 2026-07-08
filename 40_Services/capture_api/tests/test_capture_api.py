import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error

SRC = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.realpath(SRC))
import app


def _free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _read_url(url, data=None, method="GET", headers=None, code_expected=None):
    if headers is None:
        headers = {}
    if data is not None:
        data = json.dumps(data).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        if code_expected is not None and e.code == code_expected:
            return e.code, {}
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            return e.code, json.loads(body) if body else {}
        except json.JSONDecodeError:
            return e.code, {"_raw": body}


class TestCaptureAPIHealth(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.queue_dir = tempfile.mkdtemp()
        cls.queue_path = os.path.join(cls.queue_dir, "test_captures.jsonl")
        cls.port = _free_port()
        os.environ["LIFEOS_CAPTURE_PORT"] = str(cls.port)
        os.environ["LIFEOS_CAPTURE_QUEUE_PATH"] = cls.queue_path
        os.environ["LIFEOS_CAPTURE_REQUIRE_AUTH"] = "false"
        cls.server = app.CaptureServer(("127.0.0.1", cls.port), app.CaptureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import shutil
        shutil.rmtree(cls.queue_dir, ignore_errors=True)

    @property
    def base(self):
        return f"http://127.0.0.1:{self.port}"

    def test_health_returns_ok(self):
        status, body = _read_url(f"{self.base}/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "lifeos_capture_api")
        self.assertEqual(body["mode"], "queue_only")

    def test_health_json_content_type(self):
        req = urllib.request.Request(f"{self.base}/health")
        with urllib.request.urlopen(req) as resp:
            self.assertIn("application/json", resp.headers.get("Content-Type", ""))


class TestCaptureAPIPostCapture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.queue_dir = tempfile.mkdtemp()
        cls.queue_path = os.path.join(cls.queue_dir, "test_captures.jsonl")
        cls.port = _free_port()
        os.environ["LIFEOS_CAPTURE_PORT"] = str(cls.port)
        os.environ["LIFEOS_CAPTURE_QUEUE_PATH"] = cls.queue_path
        os.environ["LIFEOS_CAPTURE_REQUIRE_AUTH"] = "false"
        cls.server = app.CaptureServer(("127.0.0.1", cls.port), app.CaptureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import shutil
        shutil.rmtree(cls.queue_dir, ignore_errors=True)

    @property
    def base(self):
        return f"http://127.0.0.1:{self.port}"

    def test_valid_text_capture(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "Hello world test capture"})
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        self.assertIn("capture_id", body)
        self.assertEqual(body["status"], "queued")

    def test_valid_url_capture(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"url": "https://example.com/article"})
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])

    def test_text_alias_normalized_to_content(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"text": "alias capture"})
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])

    def test_missing_content_and_url_rejected(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"source": "telegram"})
        self.assertEqual(status, 400)
        self.assertFalse(body["success"])

    def test_empty_content_rejected(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "   "})
        self.assertEqual(status, 400)
        self.assertFalse(body["success"])

    def test_oversized_payload_rejected(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "x" * 100000})
        self.assertIn(status, [400, 413])
        self.assertFalse(body["success"])

    def test_invalid_json_rejected(self):
        req = urllib.request.Request(f"{self.base}/captures",
                                     data=b"not-json",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req):
                pass
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, [400, 415])

    def test_tags_string_becomes_list(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "tag test", "tags": "single-tag"})
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])

    def test_source_defaults_to_unknown(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "no source"})
        self.assertEqual(status, 200)
        self.assertEqual(body.get("source"), "unknown")

    def test_queue_appends_jsonl(self):
        before_count = 0
        if os.path.exists(self.queue_path):
            with open(self.queue_path, "r") as f:
                before_count = len([l for l in f if l.strip()])
        _read_url(f"{self.base}/captures", method="POST",
                  data={"content": "line one"})
        _read_url(f"{self.base}/captures", method="POST",
                  data={"content": "line two"})
        self.assertTrue(os.path.exists(self.queue_path))
        with open(self.queue_path, "r") as f:
            lines = [l for l in f if l.strip()]
        self.assertEqual(len(lines), before_count + 2)
        rec1 = json.loads(lines[-2])
        self.assertEqual(rec1["content"], "line one")
        self.assertEqual(rec1["status"], "queued")

    def test_priority_defaults_to_normal(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "priority test"})
        self.assertEqual(status, 200)
        with open(self.queue_path, "r") as f:
            lines = [l for l in f if l.strip()]
        rec = json.loads(lines[-1])
        self.assertEqual(rec["priority"], "normal")

    def test_url_inferred_capture_type(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"url": "https://example.com"})
        self.assertEqual(status, 200)
        with open(self.queue_path, "r") as f:
            lines = [l for l in f if l.strip()]
        rec = json.loads(lines[-1])
        self.assertEqual(rec["capture_type"], "url")

    def test_content_capture_type_defaults_to_text(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "just some text"})
        self.assertEqual(status, 200)
        with open(self.queue_path, "r") as f:
            lines = [l for l in f if l.strip()]
        rec = json.loads(lines[-1])
        self.assertEqual(rec["capture_type"], "text")

    def test_capture_record_has_required_fields(self):
        _read_url(f"{self.base}/captures", method="POST",
                  data={"content": "field check", "source": "desktop", "title": "Test"})
        with open(self.queue_path, "r") as f:
            lines = [l for l in f if l.strip()]
        rec = json.loads(lines[-1])
        for fld in ("capture_id", "received_at", "source", "capture_type",
                     "content", "url", "title", "tags", "priority",
                     "client", "metadata", "status", "raw_payload",
                     "auth_method", "schema_version"):
            self.assertIn(fld, rec, f"missing field: {fld}")

    def test_method_not_allowed(self):
        status, _ = _read_url(f"{self.base}/captures", method="GET")
        self.assertEqual(status, 405)


class TestCaptureAPIAuth(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.queue_dir = tempfile.mkdtemp()
        cls.queue_path = os.path.join(cls.queue_dir, "test_captures.jsonl")
        cls.port = _free_port()
        os.environ["LIFEOS_CAPTURE_PORT"] = str(cls.port)
        os.environ["LIFEOS_CAPTURE_QUEUE_PATH"] = cls.queue_path
        os.environ["LIFEOS_CAPTURE_BEARER_TOKEN"] = "test-secret-token"
        os.environ["LIFEOS_CAPTURE_REQUIRE_AUTH"] = "true"
        cls.server = app.CaptureServer(("127.0.0.1", cls.port), app.CaptureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import shutil
        shutil.rmtree(cls.queue_dir, ignore_errors=True)

    @property
    def base(self):
        return f"http://127.0.0.1:{self.port}"

    def test_unauthorized_when_auth_required(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "no auth"})
        self.assertEqual(status, 401)
        self.assertFalse(body["success"])

    def test_bearer_valid_accepted(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "bearer ok"},
                                 headers={"Authorization": "Bearer test-secret-token"})
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])

    def test_bearer_invalid_rejected(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "bad bearer"},
                                 headers={"Authorization": "Bearer wrong-token"})
        self.assertEqual(status, 401)
        self.assertFalse(body["success"])

    def test_bearer_auth_method_recorded(self):
        _read_url(f"{self.base}/captures", method="POST",
                  data={"content": "auth method test"},
                  headers={"Authorization": "Bearer test-secret-token"})
        with open(self.queue_path, "r") as f:
            lines = [l for l in f if l.strip()]
        rec = json.loads(lines[-1])
        self.assertEqual(rec["auth_method"], "bearer")

    def test_health_unauthenticated_still_works(self):
        status, body = _read_url(f"{self.base}/health")
        self.assertEqual(status, 200)


class TestCaptureAPIDisabledAuth(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.queue_dir = tempfile.mkdtemp()
        cls.queue_path = os.path.join(cls.queue_dir, "test_captures.jsonl")
        cls.port = _free_port()
        os.environ["LIFEOS_CAPTURE_PORT"] = str(cls.port)
        os.environ["LIFEOS_CAPTURE_QUEUE_PATH"] = cls.queue_path
        os.environ["LIFEOS_CAPTURE_REQUIRE_AUTH"] = "false"
        cls.server = app.CaptureServer(("127.0.0.1", cls.port), app.CaptureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import shutil
        shutil.rmtree(cls.queue_dir, ignore_errors=True)

    @property
    def base(self):
        return f"http://127.0.0.1:{self.port}"

    def test_unauthenticated_accepted_when_require_auth_false(self):
        status, body = _read_url(f"{self.base}/captures", method="POST",
                                 data={"content": "no auth needed"})
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])


if __name__ == "__main__":
    unittest.main()
