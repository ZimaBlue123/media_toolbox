from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.error
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolPaths:
    untrunc: Path | None
    ffmpeg: Path | None
    ffprobe: Path | None


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


def _tools_dir(base_dir: str | Path | None = None) -> Path:
    if base_dir:
        return Path(base_dir)
    return Path(__file__).resolve().parents[3] / "tools"


def _http_get_json(url: str, *, timeout_s: int = 60) -> object:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "av_media_repair/module1_video_repair"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        headers=headers,
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download(url: str, dest: Path, *, timeout_s: int = 300) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "av_media_repair/module1_video_repair"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp, dest.open("wb") as f:
        shutil.copyfileobj(resp, f)
    if not dest.exists() or dest.stat().st_size == 0:
        raise RuntimeError(f"下载失败或文件为空：{dest}")


def _extract_zip_member(zip_path: Path, member_suffix: str, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        members = [m for m in z.namelist() if m.lower().endswith(member_suffix.lower())]
        if not members:
            raise FileNotFoundError(f"ZIP 内未找到 {member_suffix}（{zip_path}）")
        # 选最短路径（通常是 /bin/ffmpeg.exe 这种）
        members.sort(key=lambda s: (len(s), s))
        m = members[0]
        with z.open(m) as src, dest_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)


def _extract_zip_folder_containing(zip_path: Path, member_suffix: str, dest_dir: Path) -> Path:
    """
    在 ZIP 内找到一个以 member_suffix 结尾的文件（如 untrunc.exe），
    然后把其所在“文件夹前缀”下的所有文件解压到 dest_dir。
    返回解压后的目标文件路径（dest_dir/member_name_basename）。
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        members = [m for m in z.namelist() if m.lower().endswith(member_suffix.lower())]
        if not members:
            raise FileNotFoundError(f"ZIP 内未找到 {member_suffix}（{zip_path}）")
        members.sort(key=lambda s: (len(s), s))
        target = members[0]
        prefix = target.rsplit("/", 1)[0] + "/" if "/" in target else ""

        for name in z.namelist():
            if not name or name.endswith("/"):
                continue
            if prefix and not name.startswith(prefix):
                continue
            # 只解压“同目录”下文件，避免携带多层路径
            base = name.split("/")[-1]
            if not base:
                continue
            out = dest_dir / base
            with z.open(name) as src, out.open("wb") as dst:
                shutil.copyfileobj(src, dst)

        return dest_dir / target.split("/")[-1]


def _pick_github_asset(assets: list[dict], *, prefer_zip: bool, keywords: list[str]) -> dict | None:
    def score(a: dict) -> int:
        name = str(a.get("name", "")).lower()
        s = 0
        if prefer_zip and name.endswith(".zip"):
            s += 50
        if name.endswith(".exe"):
            s += 40
        for k in keywords:
            if k.lower() in name:
                s += 10
        return s

    ranked = sorted(assets, key=score, reverse=True)
    best = ranked[0] if ranked else None
    if not best or score(best) <= 0:
        return None
    return best


def _exe_works(exe: Path, test_args: list[str] | None = None) -> bool:
    try:
        res = subprocess.run(
            [str(exe)] + (test_args or ["--version"]),
            capture_output=True,
            timeout=10
        )
        return res.returncode == 0
    except Exception:
        return False


def ensure_untrunc(*, tools_dir: str | Path | None = None, untrunc_path: str | None = None) -> Path:
    if untrunc_path:
        p = Path(untrunc_path)
        if not p.exists():
            raise FileNotFoundError(f"指定的 untrunc 不存在：{p}")
        return p

    in_path = shutil.which("untrunc") or shutil.which("untrunc.exe")
    if in_path:
        return Path(in_path)

    if not _is_windows():
        raise RuntimeError("未在 PATH 中找到 untrunc。非 Windows 环境请自行安装 untrunc 并加入 PATH，或用 --untrunc 指定。")

    td = _tools_dir(tools_dir) / "untrunc"
    exe = td / "untrunc.exe"
    if exe.exists() and _exe_works(exe, ["-h"]):
        return exe

    # 使用已知的 GitHub Releases 直链（避免 GitHub API rate limit）
    arch = platform.machine().lower()
    zip_name = "untrunc_x64.zip" if ("64" in arch or "amd64" in arch) else "untrunc_x32.zip"
    url = f"https://github.com/anthwlock/untrunc/releases/download/latest/{zip_name}"
    name = zip_name
    with tempfile.TemporaryDirectory() as tmp:
        tmp_zip = Path(tmp) / name
        _download(url, tmp_zip)
        if name.lower().endswith(".zip"):
            # Windows 预编译通常需要同目录 DLL，一并解压才能运行
            exe = _extract_zip_folder_containing(tmp_zip, "untrunc.exe", td)
        elif name.lower().endswith(".exe"):
            td.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(tmp_zip, exe)
        else:
            raise RuntimeError(f"未知的 untrunc 资产格式：{name}")

    return exe


def ensure_ffmpeg_suite(*, tools_dir: str | Path | None = None, ffmpeg_path: str | None = None, ffprobe_path: str | None = None) -> ToolPaths:
    ffmpeg = Path(ffmpeg_path) if ffmpeg_path else (Path(shutil.which("ffmpeg")) if shutil.which("ffmpeg") else None)
    ffprobe = Path(ffprobe_path) if ffprobe_path else (Path(shutil.which("ffprobe")) if shutil.which("ffprobe") else None)
    if ffmpeg and ffprobe and ffmpeg.exists() and ffprobe.exists():
        return ToolPaths(untrunc=None, ffmpeg=ffmpeg, ffprobe=ffprobe)

    if not _is_windows():
        # Linux/macOS：不做自动下载，避免破坏系统包管理
        return ToolPaths(untrunc=None, ffmpeg=ffmpeg, ffprobe=ffprobe)

    td = _tools_dir(tools_dir) / "ffmpeg"
    ffmpeg_exe = td / "ffmpeg.exe"
    ffprobe_exe = td / "ffprobe.exe"
    if ffmpeg_exe.exists() and ffprobe_exe.exists() and _exe_works(ffmpeg_exe) and _exe_works(ffprobe_exe):
        return ToolPaths(untrunc=None, ffmpeg=ffmpeg_exe, ffprobe=ffprobe_exe)

    # Use known BtbN release URL pattern (avoids GitHub API rate limits)
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip"
    name = "ffmpeg-master-latest-win64-gpl-shared.zip"
    
    with tempfile.TemporaryDirectory() as tmp:
        tmp_zip = Path(tmp) / name
        try:
            _download(url, tmp_zip)
        except Exception:
            # Fallback to GitHub API
            api = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
            data = _http_get_json(api)
            assets = list(data.get("assets") or [])
            asset = _pick_github_asset(
                assets,
                prefer_zip=True,
                keywords=["win64", "gpl", "shared", "lgpl", "zip"],
            )
            if not asset:
                return ToolPaths(untrunc=None, ffmpeg=ffmpeg, ffprobe=ffprobe)

            url = str(asset.get("browser_download_url"))
            name = str(asset.get("name") or "ffmpeg.zip")
            tmp_zip = Path(tmp) / name
            _download(url, tmp_zip)

        # Windows 发行版可能是 shared build，需要同目录 DLL；一并解压
        _extract_zip_folder_containing(tmp_zip, "ffprobe.exe", td)
        # 保险：若 ffmpeg.exe 没在同目录（极少数压缩包结构差异），再按需补齐
        if not ffmpeg_exe.exists():
            _extract_zip_member(tmp_zip, "ffmpeg.exe", ffmpeg_exe)

    return ToolPaths(untrunc=None, ffmpeg=ffmpeg_exe, ffprobe=ffprobe_exe)


def default_tools(*, tools_dir: str | Path | None = None) -> ToolPaths:
    untrunc = None
    try:
        untrunc = ensure_untrunc(tools_dir=tools_dir)
    except Exception:
        untrunc = None

    suite = ensure_ffmpeg_suite(tools_dir=tools_dir)
    return ToolPaths(untrunc=untrunc, ffmpeg=suite.ffmpeg, ffprobe=suite.ffprobe)
