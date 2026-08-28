from __future__ import annotations

import os
import struct
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Mp4AtomProbeResult:
    path: Path
    size_bytes: int
    header_has_ftyp: bool
    header_has_moov: bool
    header_has_mdat: bool
    file_has_moov: bool


def _scan_boxes_in_buffer(data: bytes) -> set[bytes]:
    boxes = set()
    pos = 0
    while pos < len(data):
        if pos + 8 > len(data):
            break
        try:
            box_size, box_type = struct.unpack_from(">I4s", data, pos)
            
            header_size = 8
            if box_size == 1:
                if pos + 16 > len(data):
                    break
                box_size = struct.unpack_from(">Q", data, pos + 8)[0]
                header_size = 16
            elif box_size == 0:
                box_size = len(data) - pos
                
            if box_size < header_size:
                break
                
            boxes.add(box_type)
            pos += box_size
        except struct.error as e:
            logger.debug(f"Struct parsing error during buffer scan: {e}")
            break
            
    return boxes


def _file_contains_box_type(path: Path, box_type: bytes) -> bool:
    try:
        with path.open("rb") as f:
            while True:
                header = f.read(8)
                if len(header) < 8:
                    break
                try:
                    size, btype = struct.unpack(">I4s", header)
                except struct.error:
                    break
                
                if btype == box_type:
                    return True
                
                if size == 0:
                    return False
                    
                if size == 1:
                    ext_header = f.read(8)
                    if len(ext_header) < 8:
                        break
                    try:
                        size = struct.unpack(">Q", ext_header)[0]
                    except struct.error:
                        break
                    if size < 16:
                        return False
                    try:
                        f.seek(size - 16, os.SEEK_CUR)
                    except OSError:
                        break
                else:
                    if size < 8:
                        return False
                    try:
                        f.seek(size - 8, os.SEEK_CUR)
                    except OSError:
                        break
    except OSError as e:
        logger.warning(f"OS error reading file {path}: {e}")
        return False
                    
    return False


def probe_mp4_atoms(path: str | Path, *, header_bytes: int = 64 * 1024) -> Mp4AtomProbeResult:
    p = Path(path)
    try:
        size = p.stat().st_size
    except OSError as e:
        logger.error(f"Cannot stat file {path}: {e}")
        return Mp4AtomProbeResult(
            path=p, size_bytes=0, header_has_ftyp=False, 
            header_has_moov=False, header_has_mdat=False, file_has_moov=False
        )
    
    head = b""
    try:
        with p.open("rb") as f:
            head = f.read(header_bytes)
    except OSError as e:
        logger.warning(f"Error reading header of {path}: {e}")

    boxes = _scan_boxes_in_buffer(head)

    header_has_ftyp = b"ftyp" in boxes
    header_has_moov = b"moov" in boxes
    header_has_mdat = b"mdat" in boxes

    file_has_moov = _file_contains_box_type(p, b"moov")

    return Mp4AtomProbeResult(
        path=p,
        size_bytes=size,
        header_has_ftyp=header_has_ftyp,
        header_has_moov=header_has_moov,
        header_has_mdat=header_has_mdat,
        file_has_moov=file_has_moov,
    )
