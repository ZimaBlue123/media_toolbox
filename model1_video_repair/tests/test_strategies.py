"""Tests for video_repair.strategies — command construction and helpers."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from video_repair.strategies import (
    ExecResult,
    SUPPORTED_VIDEO_EXTENSIONS,
    _FORMAT_MAP,
    _resolve_ffmpeg,
    reencode_av_with_ffmpeg,
    remux_with_ffmpeg,
    repair_with_untrunc,
    sanitize_audio_with_ffmpeg,
    sanitize_container_with_ffmpeg,
)


class TestFormatMap(unittest.TestCase):
    """Verify _FORMAT_MAP covers all extensions and is consistent."""

    def test_format_map_covers_mp4_family(self):
        for ext in (".mp4", ".mov", ".m4v"):
            self.assertIn(ext, _FORMAT_MAP)
            self.assertIn(_FORMAT_MAP[ext], ("mp4", "mov", "m4v"))

    def test_format_map_keys_are_all_lowercase(self):
        for k in _FORMAT_MAP:
            self.assertEqual(k, k.lower(), f"Key {k!r} should be lowercase")
            self.assertTrue(k.startswith("."), f"Key {k!r} should start with a dot")

    def test_all_supported_extensions_have_format(self):
        for ext in SUPPORTED_VIDEO_EXTENSIONS:
            self.assertIn(ext, _FORMAT_MAP, f"{ext} is in SUPPORTED_VIDEO_EXTENSIONS but missing from _FORMAT_MAP")


class TestResolveFfmpeg(unittest.TestCase):
    """Verify _resolve_ffmpeg returns the passed value or shutil.which result."""

    def test_returns_explicit_path(self):
        self.assertEqual(_resolve_ffmpeg("/usr/bin/ffmpeg"), "/usr/bin/ffmpeg")

    @patch("shutil.which", return_value=None)
    def test_returns_none_when_not_found(self, _mock):
        self.assertIsNone(_resolve_ffmpeg(None))

    @patch("shutil.which", return_value="C:\\ffmpeg\\ffmpeg.exe")
    def test_returns_which_result(self, _mock):
        self.assertEqual(_resolve_ffmpeg(None), "C:\\ffmpeg\\ffmpeg.exe")


class TestFfmpegNotFoundReturnsError(unittest.TestCase):
    """All ffmpeg wrappers should return ExecResult(ok=False) when ffmpeg is missing."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("shutil.which", return_value=None)
    def test_sanitize_container(self, _mock):
        r = sanitize_container_with_ffmpeg(self.tmp_path / "in.mp4", self.tmp_path / "out.mp4")
        self.assertFalse(r.ok)
        self.assertEqual(r.returncode, 127)
        self.assertIn("ffmpeg", r.stderr)

    @patch("shutil.which", return_value=None)
    def test_sanitize_audio(self, _mock):
        r = sanitize_audio_with_ffmpeg(self.tmp_path / "in.mp4", self.tmp_path / "out.mp4")
        self.assertFalse(r.ok)
        self.assertEqual(r.returncode, 127)

    @patch("shutil.which", return_value=None)
    def test_reencode_av(self, _mock):
        r = reencode_av_with_ffmpeg(self.tmp_path / "in.mp4", self.tmp_path / "out.mp4")
        self.assertFalse(r.ok)
        self.assertEqual(r.returncode, 127)

    @patch("shutil.which", return_value=None)
    def test_remux(self, _mock):
        r = remux_with_ffmpeg(self.tmp_path / "in.mp4", self.tmp_path / "out.mp4")
        self.assertFalse(r.ok)
        self.assertEqual(r.returncode, 127)


class TestCommandConstruction(unittest.TestCase):
    """Verify ffmpeg commands contain expected flags."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("video_repair.strategies._run")
    @patch("shutil.which", return_value="ffmpeg")
    def test_sanitize_container_mp4_has_faststart(self, _w, mock_run):
        mock_run.return_value = ExecResult(ok=True, command=[], stdout="", stderr="", returncode=0)
        sanitize_container_with_ffmpeg(self.tmp_path / "in.mp4", self.tmp_path / "out.mp4")
        cmd = mock_run.call_args[0][0]
        self.assertIn("-movflags", cmd)
        self.assertIn("+faststart", cmd)

    @patch("video_repair.strategies._run")
    @patch("shutil.which", return_value="ffmpeg")
    def test_sanitize_container_mkv_has_default_mode(self, _w, mock_run):
        mock_run.return_value = ExecResult(ok=True, command=[], stdout="", stderr="", returncode=0)
        sanitize_container_with_ffmpeg(self.tmp_path / "in.mkv", self.tmp_path / "out.mkv")
        cmd = mock_run.call_args[0][0]
        self.assertIn("-default_mode", cmd)

    @patch("video_repair.strategies._run")
    @patch("shutil.which", return_value="ffmpeg")
    def test_reencode_uses_libopenh264(self, _w, mock_run):
        mock_run.return_value = ExecResult(ok=True, command=[], stdout="", stderr="", returncode=0)
        reencode_av_with_ffmpeg(self.tmp_path / "in.mp4", self.tmp_path / "out.mp4")
        cmd = mock_run.call_args[0][0]
        self.assertIn("libopenh264", cmd)

    @patch("video_repair.strategies._run")
    @patch("shutil.which", return_value="ffmpeg")
    def test_reencode_webm_uses_vorbis(self, _w, mock_run):
        mock_run.return_value = ExecResult(ok=True, command=[], stdout="", stderr="", returncode=0)
        reencode_av_with_ffmpeg(self.tmp_path / "in.webm", self.tmp_path / "out.webm")
        cmd = mock_run.call_args[0][0]
        self.assertIn("libvorbis", cmd)


class TestUntruncNotFound(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("shutil.which", return_value=None)
    def test_returns_error(self, _mock):
        r = repair_with_untrunc(self.tmp_path / "good.mp4", self.tmp_path / "broken.mp4", self.tmp_path / "out.mp4")
        self.assertFalse(r.ok)
        self.assertEqual(r.returncode, 127)
        self.assertIn("untrunc", r.stderr)


if __name__ == "__main__":
    unittest.main()
