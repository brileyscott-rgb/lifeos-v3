#!/usr/bin/env python3
"""
Tests for ai_worker.py dry-run scaffold.

Run: python3 -m pytest tests/test_ai_worker_dry_run.py -v
Or:  python3 tests/test_ai_worker_dry_run.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent dir to path so we can import ai_worker
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai_worker


class TestAiWorkerDryRun(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_base = ai_worker.BASE_DIR
        ai_worker.BASE_DIR = Path(self.tmpdir)
        ai_worker.JOBS_DIR = ai_worker.BASE_DIR / "jobs"
        ai_worker.PENDING_DIR = ai_worker.JOBS_DIR / "pending"
        ai_worker.LOG_DIR = ai_worker.BASE_DIR / "logs"

    def tearDown(self):
        ai_worker.BASE_DIR = self.original_base
        ai_worker.JOBS_DIR = self.original_base / "jobs"
        ai_worker.PENDING_DIR = self.original_base / "jobs" / "pending"
        ai_worker.LOG_DIR = self.original_base / "logs"
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_ensure_dirs_creates_folders(self):
        ai_worker.ensure_dirs()
        self.assertTrue(ai_worker.PENDING_DIR.exists())
        self.assertTrue((ai_worker.JOBS_DIR / "approved").exists())
        self.assertTrue((ai_worker.JOBS_DIR / "running").exists())
        self.assertTrue((ai_worker.JOBS_DIR / "completed").exists())
        self.assertTrue((ai_worker.JOBS_DIR / "rejected").exists())
        self.assertTrue(ai_worker.LOG_DIR.exists())

    def test_create_job_creates_file(self):
        ai_worker.ensure_dirs()
        job_id = ai_worker.create_job("test goal")
        self.assertIsNotNone(job_id)
        matching = list(ai_worker.PENDING_DIR.glob(f"{job_id}.md"))
        self.assertEqual(len(matching), 1)
        content = matching[0].read_text(encoding="utf-8")
        self.assertIn("test goal", content)
        self.assertIn(job_id, content)

    def test_create_job_frontmatter(self):
        ai_worker.ensure_dirs()
        job_id = ai_worker.create_job("frontmatter test")
        filepath = ai_worker.PENDING_DIR / f"{job_id}.md"
        content = filepath.read_text(encoding="utf-8")
        self.assertIn("status: pending", content)
        self.assertIn("approval_state: not_requested", content)
        self.assertIn("risk_level: unclassified", content)
        self.assertIn("source: cli", content)

    def test_list_jobs_empty(self):
        ai_worker.ensure_dirs()
        jobs = ai_worker.list_jobs()
        self.assertEqual(len(jobs), 0)

    def test_list_jobs_after_create(self):
        ai_worker.ensure_dirs()
        ai_worker.create_job("list test 1")
        ai_worker.create_job("list test 2")
        jobs = ai_worker.list_jobs()
        self.assertEqual(len(jobs), 2)

    def test_show_status_output(self):
        ai_worker.ensure_dirs()
        ai_worker.create_job("status test")
        from io import StringIO
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            ai_worker.show_status()
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertIn("dry-run", output)
        self.assertIn("Pending:", output)
        self.assertIn("1", output)


if __name__ == "__main__":
    unittest.main()
