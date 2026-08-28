"""Tests for video_repair.tooling — download validation, exe health checks, and path discovery."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from video_repair.tooling import (
    _download,
    _exe_works,
    _extract_zip_folder_containing,
    _extract_zip_member,
    _http_get_json,
    ensure_ffmpeg_suite,
    ensure_untrunc,
)


class TestExeWorks(unittest.TestCase):
    @patch("subprocess.run")
    def test_exe_works_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(args=["exe", "--version"], returncode=0)
        self.assertTrue(_exe_works(Path("test_exe.exe")))

    @patch("subprocess.run")
    def test_exe_works_failure_code(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(args=["exe", "--version"], returncode=1)
        self.assertFalse(_exe_works(Path("test_exe.exe")))

    @patch("subprocess.run", side_effect=OSError("Exec failed"))
    def test_exe_works_exception(self, _mock_run):
        self.assertFalse(_exe_works(Path("test_exe.exe")))


class TestDownloadValidation(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_download_raises_on_empty_file(self):
        dest = self.tmp_path / "download.zip"
        # Mock urllib to create an empty file
        mock_resp = MagicMock()
        mock_resp.read.return_value = b""

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            with self.assertRaises(RuntimeError):
                _download("http://example.com/file.zip", dest)


class TestZipExtraction(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_extract_zip_member(self):
        zip_path = self.tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("bin/ffmpeg.exe", b"dummy_ffmpeg_bytes")

        out_exe = self.tmp_path / "extracted" / "ffmpeg.exe"
        _extract_zip_member(zip_path, "ffmpeg.exe", out_exe)

        self.assertTrue(out_exe.exists())
        self.assertEqual(out_exe.read_bytes(), b"dummy_ffmpeg_bytes")

    def test_extract_zip_folder_containing(self):
        zip_path = self.tmp_path / "tools.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("tools/untrunc.exe", b"untrunc_binary")
            z.writestr("tools/avcodec.dll", b"dll_binary")
            z.writestr("other/readme.txt", b"ignore_me")

        dest_dir = self.tmp_path / "tools_dir"
        target = _extract_zip_folder_containing(zip_path, "untrunc.exe", dest_dir)

        self.assertEqual(target, dest_dir / "untrunc.exe")
        self.assertTrue((dest_dir / "untrunc.exe").exists())
        self.assertTrue((dest_dir / "avcodec.dll").exists())
        self.assertFalse((dest_dir / "readme.txt").exists())


class TestEnsureUntrunc(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_custom_path_not_exist_raises(self):
        with self.assertRaises(FileNotFoundError):
            ensure_untrunc(untrunc_path=str(self.tmp_path / "nonexistent.exe"))

    def test_custom_path_exists_returned(self):
        custom = self.tmp_path / "my_untrunc.exe"
        custom.write_text("binary")
        res = ensure_untrunc(untrunc_path=str(custom))
        self.assertEqual(res, custom)

    @patch("video_repair.tooling._exe_works", return_value=True)
    def test_cached_exe_works_returns_cached(self, _mock_works):
        tools_dir = self.tmp_path / "tools"
        cached_exe = tools_dir / "untrunc" / "untrunc.exe"
        cached_exe.parent.mkdir(parents=True, exist_ok=True)
        cached_exe.write_text("cached binary")

        with patch("video_repair.tooling._is_windows", return_value=True), \
             patch("shutil.which", return_value=None):
            res = ensure_untrunc(tools_dir=tools_dir)
            self.assertEqual(res, cached_exe)


class TestEnsureFfmpegSuite(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("video_repair.tooling._exe_works", return_value=True)
    def test_cached_ffmpeg_works_returns_cached(self, _mock_works):
        tools_dir = self.tmp_path / "tools"
        ff_exe = tools_dir / "ffmpeg" / "ffmpeg.exe"
        probe_exe = tools_dir / "ffmpeg" / "ffprobe.exe"
        ff_exe.parent.mkdir(parents=True, exist_ok=True)
        ff_exe.write_text("binary")
        probe_exe.write_text("binary")

        with patch("video_repair.tooling._is_windows", return_value=True), \
             patch("shutil.which", return_value=None):
            suite = ensure_ffmpeg_suite(tools_dir=tools_dir)
            self.assertEqual(suite.ffmpeg, ff_exe)
            self.assertEqual(suite.ffprobe, probe_exe)


class TestHttpGetJsonAuth(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_http_get_json_uses_github_token_if_set(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_123"}):
            res = _http_get_json("https://api.github.com/test")
            self.assertEqual(res, {"status": "ok"})
            req_arg = mock_urlopen.call_args[0][0]
            self.assertEqual(req_arg.headers.get("Authorization"), "Bearer ghp_test_token_123")


if __name__ == "__main__":
    unittest.main()
