"""Tests for video_repair.batch and video_repair.cli."""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from video_repair.batch import (
    _list_inputs,
    _pick_template_mp4,
    repair_dir_with_untrunc,
)
from video_repair.cli import build_parser, main
from video_repair.strategies import ExecResult


class TestBatchHelpers(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_pick_template_mp4_picks_largest(self):
        tpl_dir = self.tmp_path / "template"
        tpl_dir.mkdir()
        small = tpl_dir / "small.mp4"
        large = tpl_dir / "large.mp4"
        small.write_bytes(b"x" * 100)
        large.write_bytes(b"x" * 1000)

        picked = _pick_template_mp4(tpl_dir)
        self.assertEqual(picked, large)

    def test_pick_template_mp4_raises_on_empty(self):
        tpl_dir = self.tmp_path / "empty_template"
        tpl_dir.mkdir()
        with self.assertRaises(FileNotFoundError):
            _pick_template_mp4(tpl_dir)

    def test_list_inputs_ignores_fixed_files(self):
        in_dir = self.tmp_path / "input"
        in_dir.mkdir()
        normal = in_dir / "video1.mp4"
        fixed1 = in_dir / "video1_fixed.mp4"
        fixed2 = in_dir / "fixed_video2.mp4"
        normal.write_bytes(b"data")
        fixed1.write_bytes(b"data")
        fixed2.write_bytes(b"data")

        inputs = _list_inputs(in_dir)
        self.assertEqual(inputs, [normal])


class TestBatchRepairCleanup(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("video_repair.batch.ensure_untrunc")
    @patch("video_repair.batch.ensure_ffmpeg_suite")
    @patch("video_repair.batch.repair_with_untrunc")
    @patch("video_repair.batch.sanitize_container_with_ffmpeg")
    @patch("video_repair.batch.probe_mp4_atoms")
    def test_batch_cleans_up_intermediates_by_default(
        self,
        mock_probe,
        mock_sanitize,
        mock_untrunc,
        mock_ffmpeg_suite,
        mock_ensure_untrunc,
    ):
        tpl_dir = self.tmp_path / "tpl"
        tpl_dir.mkdir()
        tpl_file = tpl_dir / "good.mp4"
        tpl_file.write_bytes(b"good")

        in_dir = self.tmp_path / "in"
        in_dir.mkdir()
        in_file = in_dir / "broken.mp4"
        in_file.write_bytes(b"broken")

        out_dir = self.tmp_path / "out"

        mock_ensure_untrunc.return_value = Path("untrunc.exe")
        mock_suite = MagicMock()
        mock_suite.ffmpeg = Path("ffmpeg.exe")
        mock_suite.ffprobe = None
        mock_ffmpeg_suite.return_value = mock_suite

        # Untrunc creates intermediate file
        def fake_untrunc(good, broken, out, untrunc=None):
            out.write_bytes(b"untrunc_data")
            return ExecResult(ok=True, command=[], stdout="", stderr="", returncode=0)

        # Sanitize creates final file
        def fake_sanitize(inp, out, ffmpeg=None):
            out.write_bytes(b"final_data")
            return ExecResult(ok=True, command=[], stdout="", stderr="", returncode=0)

        mock_untrunc.side_effect = fake_untrunc
        mock_sanitize.side_effect = fake_sanitize

        from video_repair.mp4_probe import Mp4AtomProbeResult
        mock_probe.return_value = Mp4AtomProbeResult(
            path=in_file,
            size_bytes=10,
            header_has_ftyp=True,
            header_has_moov=False,
            header_has_mdat=True,
            file_has_moov=False,
        )

        report = repair_dir_with_untrunc(
            input_dir=in_dir,
            template_dir=tpl_dir,
            output_dir=out_dir,
            cleanup=True,
        )

        self.assertEqual(len(report.items), 1)
        # The main output should be the _final file
        final_file = out_dir / "broken_final.mp4"
        untrunc_file = out_dir / "broken_untrunc.mp4"
        self.assertTrue(final_file.exists())
        # The intermediate _untrunc file should have been cleaned up!
        self.assertFalse(untrunc_file.exists())


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_cli_parser_builds(self):
        p = build_parser()
        self.assertEqual(p.prog, "video_repair")

    def test_cli_probe_command(self):
        test_file = self.tmp_path / "sample.mp4"
        test_file.write_bytes(b"\x00\x00\x00\x14ftypisom\x00\x00\x02\x00isomiso2mp41")
        
        captured_stdout = io.StringIO()
        with patch("sys.stdout", captured_stdout):
            exit_code = main(["probe", str(test_file)])
        
        self.assertEqual(exit_code, 0)
        self.assertIn('"header_has_ftyp": true', captured_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
