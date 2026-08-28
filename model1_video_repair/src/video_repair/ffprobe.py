from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FfprobeResult:
    ok: bool
    returncode: int
    stderr: str
    data: dict | None


def ffprobe_json(path: str | Path, *, ffprobe: str | None = None, timeout_s: int = 60) -> FfprobeResult:
    exe = ffprobe or shutil.which("ffprobe")
    if not exe:
        return FfprobeResult(ok=False, returncode=127, stderr="未找到 ffprobe。", data=None)

    p = Path(path)
    cmd = [
        exe,
        "-hide_banner",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(p),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return FfprobeResult(ok=False, returncode=124, stderr="ffprobe 超时。", data=None)

    if r.returncode != 0:
        return FfprobeResult(ok=False, returncode=r.returncode, stderr=r.stderr or "", data=None)

    try:
        data = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return FfprobeResult(ok=False, returncode=2, stderr="ffprobe 输出非 JSON。", data=None)

    return FfprobeResult(ok=True, returncode=0, stderr=r.stderr or "", data=data)

