"""Tests for video_repair.mp4_probe — ISO BMFF box-level parsing and probe."""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from video_repair.mp4_probe import (
    _file_contains_box_type,
    _scan_boxes_in_buffer,
    probe_mp4_atoms,
)


def _make_box(box_type: bytes, payload: bytes = b"") -> bytes:
    """Helper to create a standard 32-bit sized box."""
    size = 8 + len(payload)
    return struct.pack(">I4s", size, box_type) + payload


def _make_box_64(box_type: bytes, payload: bytes = b"") -> bytes:
    """Helper to create a 64-bit extended size box."""
    size = 16 + len(payload)
    return struct.pack(">I4sQ", 1, box_type, size) + payload


class TestScanBoxesInBuffer(unittest.TestCase):
    def test_scan_standard_boxes(self):
        buf = _make_box(b"ftyp", b"isom") + _make_box(b"moov", b"...\x00\x00") + _make_box(b"mdat", b"video_data")
        boxes = _scan_boxes_in_buffer(buf)
        self.assertIn(b"ftyp", boxes)
        self.assertIn(b"moov", boxes)
        self.assertIn(b"mdat", boxes)

    def test_scan_extended_64bit_box(self):
        buf = _make_box(b"ftyp", b"isom") + _make_box_64(b"mdat", b"huge_data_chunk")
        boxes = _scan_boxes_in_buffer(buf)
        self.assertIn(b"ftyp", boxes)
        self.assertIn(b"mdat", boxes)

    def test_no_false_positive_from_payload(self):
        # Even if mdat payload contains the ASCII bytes b"moov", it should NOT be detected as a moov box!
        fake_payload = b"prefix" + b"moov" + b"suffix"
        buf = _make_box(b"ftyp", b"isom") + _make_box(b"mdat", fake_payload)
        boxes = _scan_boxes_in_buffer(buf)
        self.assertIn(b"ftyp", boxes)
        self.assertIn(b"mdat", boxes)
        self.assertNotIn(b"moov", boxes)

    def test_truncated_buffer_graceful(self):
        # Truncated header (fewer than 8 bytes)
        self.assertEqual(_scan_boxes_in_buffer(b"\x00\x00\x00"), set())


class TestFileContainsBoxType(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_finds_moov_in_file(self):
        f = self.tmp_path / "valid.mp4"
        data = _make_box(b"ftyp", b"isom") + _make_box(b"moov", b"meta") + _make_box(b"mdat", b"frames")
        f.write_bytes(data)

        self.assertTrue(_file_contains_box_type(f, b"moov"))
        self.assertTrue(_file_contains_box_type(f, b"ftyp"))
        self.assertTrue(_file_contains_box_type(f, b"mdat"))
        self.assertFalse(_file_contains_box_type(f, b"free"))

    def test_no_false_positive_in_file_mdat(self):
        f = self.tmp_path / "broken_missing_moov.mp4"
        # mdat payload contains the 4-byte sequence b"moov", but there's no actual moov box
        payload_with_embedded_moov = b"AAA" + b"moov" + b"BBB" * 100
        data = _make_box(b"ftyp", b"isom") + _make_box(b"mdat", payload_with_embedded_moov)
        f.write_bytes(data)

        self.assertFalse(_file_contains_box_type(f, b"moov"))
        self.assertTrue(_file_contains_box_type(f, b"mdat"))

    def test_finds_moov_with_64bit_box(self):
        f = self.tmp_path / "large_box.mp4"
        data = _make_box_64(b"mdat", b"large_media_content") + _make_box(b"moov", b"metadata")
        f.write_bytes(data)

        self.assertTrue(_file_contains_box_type(f, b"moov"))


class TestProbeMp4Atoms(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_probe_broken_mp4(self):
        f = self.tmp_path / "interrupted.mp4"
        # ftyp + mdat without moov
        f.write_bytes(_make_box(b"ftyp", b"isom") + _make_box(b"mdat", b"stream..."))

        res = probe_mp4_atoms(f)
        self.assertEqual(res.path, f)
        self.assertEqual(res.size_bytes, f.stat().st_size)
        self.assertTrue(res.header_has_ftyp)
        self.assertTrue(res.header_has_mdat)
        self.assertFalse(res.header_has_moov)
        self.assertFalse(res.file_has_moov)

    def test_probe_valid_mp4(self):
        f = self.tmp_path / "healthy.mp4"
        f.write_bytes(_make_box(b"ftyp", b"isom") + _make_box(b"moov", b"idx") + _make_box(b"mdat", b"frames"))

        res = probe_mp4_atoms(f)
        self.assertTrue(res.header_has_ftyp)
        self.assertTrue(res.header_has_moov)
        self.assertTrue(res.file_has_moov)


if __name__ == "__main__":
    unittest.main()
