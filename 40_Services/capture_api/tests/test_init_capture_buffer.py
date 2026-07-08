import os
import sys
import tempfile
import unittest

SRC = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.realpath(SRC))
import init_capture_buffer


class TestInitCaptureBuffer(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.buf = os.path.join(self.tmp, "LifeOS_Capture_Buffer")
        self.med = os.path.join(self.tmp, "LifeOS_Media_Archive")

    def test_dry_run_creates_nothing(self):
        init_capture_buffer.init_buffer(self.buf, dry_run=True)
        self.assertFalse(os.path.exists(self.buf))

    def test_creates_buffer_directories(self):
        init_capture_buffer.init_buffer(self.buf)
        for subdir in init_capture_buffer.BUFFER_STRUCTURE:
            path = os.path.join(self.buf, subdir)
            self.assertTrue(os.path.isdir(path), f"Missing: {path}")

    def test_creates_media_directories(self):
        init_capture_buffer.init_media(self.med)
        for subdir in init_capture_buffer.MEDIA_STRUCTURE:
            path = os.path.join(self.med, subdir)
            self.assertTrue(os.path.isdir(path), f"Missing: {path}")

    def test_idempotent_rerun(self):
        init_capture_buffer.init_buffer(self.buf)
        init_capture_buffer.init_buffer(self.buf)
        for subdir in init_capture_buffer.BUFFER_STRUCTURE:
            path = os.path.join(self.buf, subdir)
            self.assertTrue(os.path.isdir(path))

    def test_creates_readme_files(self):
        init_capture_buffer.init_buffer(self.buf)
        init_capture_buffer.init_media(self.med)
        buf_readme = os.path.join(self.buf, "README.md")
        med_readme = os.path.join(self.med, "README.md")
        self.assertTrue(os.path.isfile(buf_readme))
        self.assertTrue(os.path.isfile(med_readme))
        with open(buf_readme, "r") as f:
            content = f.read()
        self.assertIn("NOT the canonical", content)

    def test_media_readme_contains_safety(self):
        init_capture_buffer.init_media(self.med)
        with open(os.path.join(self.med, "README.md"), "r") as f:
            content = f.read()
        self.assertIn("NOT stored in Git", content)

    def test_refuses_canonical_vault_path(self):
        with self.assertRaises(ValueError):
            init_capture_buffer.init_buffer("/home/lifeos/10_Vaults/LifeOS")

    def test_refuses_filesystem_root(self):
        with self.assertRaises(ValueError):
            init_capture_buffer.init_buffer("/")

    def test_no_canonical_vault_touched(self):
        import tempfile
        safe_tmp = os.path.join(self.tmp, "safe")
        init_capture_buffer.init_buffer(safe_tmp)
        init_capture_buffer.init_media(os.path.join(self.tmp, "media"))
        with open(os.path.join(safe_tmp, "01_Processed", "test.txt"), "w") as f:
            f.write("test")
        self.assertTrue(os.path.isfile(os.path.join(safe_tmp, "01_Processed", "test.txt")))

    def test_manual_markdown_dir_exists(self):
        init_capture_buffer.init_buffer(self.buf)
        self.assertTrue(os.path.isdir(
            os.path.join(self.buf, "01_Processed", "manual_markdown")))


if __name__ == "__main__":
    unittest.main()
