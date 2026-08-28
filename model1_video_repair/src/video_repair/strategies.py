from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExecResult:
    ok: bool
    command: list[str]
    stdout: str
    stderr: str
    returncode: int


def _run(command: list[str], cwd: str | None = None) -> ExecResult:
    # 某些第三方可执行文件在 Windows 下会输出非 UTF-8 文本；
    # 这里用 errors='replace' 避免解码异常导致子进程输出读取线程崩溃。
    p = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    return ExecResult(
        ok=(p.returncode == 0),
        command=command,
        stdout=p.stdout or "",
        stderr=p.stderr or "",
        returncode=p.returncode,
    )


# 常见视频格式扩展名（元数据/封装格式）
SUPPORTED_VIDEO_EXTENSIONS = frozenset([
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".flv", ".wmv",
    ".ts", ".mts", ".m2ts", ".vob", ".3gp", ".3g2", ".mpg", ".mpeg",
    ".mxf", ".ogv", ".rm", ".rmvb", ".divx", ".asf", ".f4v",
])

_FORMAT_MAP = {
    ".mp4": "mp4",
    ".mov": "mov",
    ".m4v": "m4v",
    ".avi": "avi",
    ".mkv": "mkv",
    ".webm": "webm",
    ".flv": "flv",
    ".wmv": "wmv",
    ".ts": "mpegts",
    ".mts": "mpegts",
    ".m2ts": "mpegts",
    ".vob": "mpeg",
    ".3gp": "3gp",
    ".3g2": "3gp",
    ".mpg": "mpeg",
    ".mpeg": "mpeg",
    ".mxf": "mxf",
    ".ogv": "ogg",
    ".rm": "rm",
    ".rmvb": "rm",
    ".divx": "avi",
    ".asf": "asf",
    ".f4v": "flv",
}


def _resolve_ffmpeg(ffmpeg: str | None) -> str | None:
    return ffmpeg or shutil.which("ffmpeg")


def sanitize_container_with_ffmpeg(
    input_path: str | Path,
    output_path: str | Path,
    *,
    ffmpeg: str | None = None,
) -> ExecResult:
    """
    用 ffmpeg 重新写封装（尽量无损 copy），提升播放器兼容性：
    - 生成时间戳（genpts）
    - moov 前移（faststart）
    - 根据文件扩展名自适应容器格式
    支持：MP4/MOV/M4V/AVI/MKV/WebM/FLV/WMV/TS/MTS/M2TS/VOB/3GP/3G2/MPG/MPEG/MXF/OGV/RM/RMVB/DIVX/ASF/F4V
    """
    in_p = str(Path(input_path))
    out_p = str(Path(output_path))
    ext = Path(in_p).suffix.lower()

    exe = _resolve_ffmpeg(ffmpeg)
    if not exe:
        return ExecResult(
            ok=False,
            command=["ffmpeg"],
            stdout="",
            stderr="未找到 ffmpeg。请先安装 ffmpeg，并确保 ffmpeg.exe 在 PATH 中，或传入 --ffmpeg 参数。",
            returncode=127,
        )

    out_format = _FORMAT_MAP.get(ext, "mp4")

    cmd = [
        exe,
        "-y",
        "-fflags",
        "+genpts",
        "-i",
        in_p,
        "-map",
        "0",
        "-c",
        "copy",
    ]

    # 按容器类型添加特定标志
    if out_format in ("mp4", "mov", "m4v"):
        cmd.extend(["-movflags", "+faststart"])
    elif out_format == "mkv":
        cmd.extend(["-default_mode", "infer_no_subs"])
    elif out_format == "mpegts":
        cmd.extend(["-mpegts_flags", "initial_non_negative"])
    elif out_format == "webm":
        # WebM 仅支持 VP8/VP9/Vorbis，强制复制可能失败，不加 faststart
        pass
    elif out_format == "flv":
        cmd.extend(["-flvflags", "no_metadata_none"])
    elif out_format in ("asf", "wmv"):
        cmd.extend(["-ws_warnflags", "ignore"])

    cmd.extend(["-f", out_format, out_p])
    return _run(cmd)


def sanitize_audio_with_ffmpeg(
    input_path: str | Path,
    output_path: str | Path,
    *,
    ffmpeg: str | None = None,
) -> ExecResult:
    """
    若 copy 封装后仍无声，可尝试重编码音频（视频仍 copy）。
    支持所有常见视频格式的音频重编码。
    """
    in_p = str(Path(input_path))
    out_p = str(Path(output_path))
    ext = Path(in_p).suffix.lower()

    exe = _resolve_ffmpeg(ffmpeg)
    if not exe:
        return ExecResult(
            ok=False,
            command=["ffmpeg"],
            stdout="",
            stderr="未找到 ffmpeg。请先安装 ffmpeg，并确保 ffmpeg.exe 在 PATH 中，或传入 --ffmpeg 参数。",
            returncode=127,
        )

    out_format = _FORMAT_MAP.get(ext, "mp4")

    cmd = [
        exe, "-y", "-fflags", "+genpts", "-i", in_p,
        "-map", "0", "-c:v", "copy",
    ]

    # WebM/Ogv 使用 Vorbis 音频，其他使用 AAC
    if out_format in ("webm", "ogv"):
        cmd.extend(["-c:a", "libvorbis", "-b:a", "128k"])
    else:
        cmd.extend(["-c:a", "aac", "-b:a", "160k"])

    if out_format in ("mp4", "mov", "m4v"):
        cmd.extend(["-movflags", "+faststart"])

    cmd.extend(["-f", out_format, out_p])
    return _run(cmd)


def reencode_av_with_ffmpeg(
    input_path: str | Path,
    output_path: str | Path,
    *,
    ffmpeg: str | None = None,
) -> ExecResult:
    """
    通过重新编码视频+音频来“重建码流”（最强兜底，耗时长）。
    - 视频：libopenh264（本项目内置 ffmpeg build 通常可用）
    - 音频：AAC（其他格式转 Vorbis）
    支持所有常见视频格式的重编码处理。
    """
    in_p = str(Path(input_path))
    out_p = str(Path(output_path))
    ext = Path(in_p).suffix.lower()
    
    exe = _resolve_ffmpeg(ffmpeg)
    if not exe:
        return ExecResult(
            ok=False,
            command=["ffmpeg"],
            stdout="",
            stderr="未找到 ffmpeg。请先安装 ffmpeg，并确保 ffmpeg.exe 在 PATH 中，或传入 --ffmpeg 参数。",
            returncode=127,
        )

    out_format = _FORMAT_MAP.get(ext, "mp4")
    use_vorbis = out_format in ("webm", "ogv")

    cmd = [
        exe, "-y", "-hide_banner", "-v", "error",
        "-fflags", "+genpts+discardcorrupt", "-err_detect", "ignore_err",
        "-i", in_p, "-map", "0:v:0", "-map", "0:a?",
        "-c:v", "libopenh264", "-pix_fmt", "yuv420p",
        "-g", "60", "-keyint_min", "60",
    ]
    if use_vorbis:
        cmd.extend(["-c:a", "libvorbis", "-b:a", "128k"])
    else:
        cmd.extend(["-c:a", "aac", "-b:a", "160k"])
    cmd.extend(["-af", "aresample=async=1:first_pts=0"])
    if out_format in ("mp4", "mov", "m4v"):
        cmd.extend(["-movflags", "+faststart"])
    cmd.extend(["-f", out_format, out_p])
    return _run(cmd)


def remux_with_ffmpeg(input_path: str | Path, output_path: str | Path, *, ffmpeg: str | None = None) -> ExecResult:
    in_p = str(Path(input_path))
    out_p = str(Path(output_path))
    
    exe = _resolve_ffmpeg(ffmpeg)
    if not exe:
        return ExecResult(
            ok=False,
            command=["ffmpeg"],
            stdout="",
            stderr="未找到 ffmpeg。请先安装 ffmpeg，并确保 ffmpeg.exe 在 PATH 中，或传入 --ffmpeg 参数。",
            returncode=127,
        )

    # -movflags +faststart: 把 moov 前移（如果存在的话）
    # -c copy: 尽量无损重封装
    cmd = [exe, "-y", "-i", in_p, "-c", "copy", "-movflags", "+faststart", out_p]
    return _run(cmd)


def repair_with_untrunc(
    good_path: str | Path,
    broken_path: str | Path,
    output_path: str | Path,
    *,
    untrunc: str | None = None,
) -> ExecResult:
    good_p = str(Path(good_path).absolute())
    broken_p = str(Path(broken_path).absolute())
    out_p = str(Path(output_path).absolute())
    
    exe = untrunc or shutil.which("untrunc") or shutil.which("untrunc.exe")
    if not exe:
        return ExecResult(
            ok=False,
            command=["untrunc"],
            stdout="",
            stderr="未找到 untrunc。请下载 untrunc.exe 并通过 --untrunc 指定路径，或把它加入 PATH。",
            returncode=127,
        )

    out_dir = Path(out_p).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use a temporary directory for execution
    tmpdir = tempfile.mkdtemp()
    try:
        tmp_broken = Path(tmpdir) / Path(broken_p).name
        shutil.copy2(broken_p, tmp_broken)

        cmd = [exe, good_p, str(tmp_broken)]
        r = _run(cmd, cwd=tmpdir)
        if not r.ok:
            return r

        # Search for output files only in the temp dir
        candidates = []
        broken_name = tmp_broken.name
        for pat in (
            f"{tmp_broken.stem}_fixed{tmp_broken.suffix}",
            f"fixed_{broken_name}",
            f"repaired_{broken_name}",
            f"{broken_name}_fixed.mp4",
        ):
            candidates.append(Path(tmpdir) / pat)

        produced = next((c for c in candidates if c.exists() and c.stat().st_size > 0), None)
        if not produced:
            fixed = sorted(
                [p for p in Path(tmpdir).glob("*fixed*.mp4") if p.is_file() and p.stat().st_size > 0],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            produced = fixed[0] if fixed else None
            
        if not produced:
            return ExecResult(
                ok=False,
                command=cmd,
                stdout=r.stdout,
                stderr=(r.stderr + "\n" if r.stderr else "")
                + "untrunc 执行成功但未找到输出文件（不同版本输出命名可能不同）。",
                returncode=2,
            )

        try:
            shutil.copy2(str(produced), out_p)
        except Exception as e:  # noqa: BLE001
            return ExecResult(
                ok=False,
                command=cmd,
                stdout=r.stdout,
                stderr=(r.stderr + "\n" if r.stderr else "") + f"复制输出到目标路径失败：{e}",
                returncode=3,
            )

        return ExecResult(ok=True, command=cmd, stdout=r.stdout, stderr=r.stderr, returncode=0)
    finally:
        # Clean up temp directory
        shutil.rmtree(tmpdir, ignore_errors=True)
