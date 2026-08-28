from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .ffprobe import ffprobe_json
from .mp4_probe import probe_mp4_atoms
from .strategies import ExecResult, reencode_av_with_ffmpeg, repair_with_untrunc, sanitize_audio_with_ffmpeg, sanitize_container_with_ffmpeg, SUPPORTED_VIDEO_EXTENSIONS
from .tooling import ToolPaths, ensure_ffmpeg_suite, ensure_untrunc

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ItemReport:
    input_path: str
    output_path: str
    template_path: str
    before_probe: dict
    after_probe: dict | None
    untrunc: dict
    ffmpeg_sanitize: dict | None
    ffmpeg_reencode: dict | None
    ffprobe_ok: bool | None
    ffprobe_error: str | None
    elapsed_ms: int


@dataclass(frozen=True)
class BatchReport:
    started_at: float
    finished_at: float
    input_dir: str
    template_file: str
    output_dir: str
    tools: dict
    items: list[ItemReport]


def _probe_to_jsonable_dict(p: str | Path) -> dict:
    r = probe_mp4_atoms(p)
    d = asdict(r)
    d["path"] = str(d.get("path"))
    return d


def _pick_template_mp4(template_dir: Path) -> Path:
    cands = []
    for ext in SUPPORTED_VIDEO_EXTENSIONS:
        cands.extend(template_dir.glob(f"*{ext}"))
    cands = [p for p in cands if p.is_file()]
    if not cands:
        raise FileNotFoundError(f"template 目录未找到视频文件：{template_dir}")
    # 选最大的（通常更"完整"，且同设置几秒也会小，但至少确保不是空文件）
    cands.sort(key=lambda p: p.stat().st_size, reverse=True)
    return cands[0]


def _list_inputs(input_dir: Path) -> list[Path]:
    cands: list[Path] = []
    for ext in SUPPORTED_VIDEO_EXTENSIONS:
        cands.extend(input_dir.glob(f"*{ext}"))
    cands = [p for p in cands if p.is_file()]
    # 避免把 untrunc 生成的 *_fixed*.mp4 再次作为输入反复处理
    cands = [p for p in cands if "fixed" not in p.name.lower()]
    cands.sort(key=lambda p: p.name)
    return cands


def _try_remove(path: Path) -> None:
    """尝试删除文件，失败时仅记录警告。"""
    try:
        if path.exists():
            path.unlink()
            logger.debug("Cleaned up intermediate file: %s", path)
    except OSError as e:
        logger.warning("Failed to clean up %s: %s", path, e)


def repair_dir_with_untrunc(
    *,
    input_dir: str | Path,
    template_dir: str | Path,
    output_dir: str | Path,
    tools_dir: str | Path | None = None,
    untrunc: str | None = None,
    ffprobe: str | None = None,
    reencode_video: bool = False,
    report_path: str | Path | None = None,
    cleanup: bool = True,
) -> BatchReport:
    in_dir = Path(input_dir)
    tpl_dir = Path(template_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tpl = _pick_template_mp4(tpl_dir)
    inputs = _list_inputs(in_dir)
    total = len(inputs)

    logger.info("Template: %s", tpl)
    logger.info("Found %d input file(s) in %s", total, in_dir)

    untrunc_exe = ensure_untrunc(tools_dir=tools_dir, untrunc_path=untrunc)
    suite = ensure_ffmpeg_suite(tools_dir=tools_dir, ffprobe_path=ffprobe)
    tools = ToolPaths(untrunc=untrunc_exe, ffmpeg=suite.ffmpeg, ffprobe=suite.ffprobe)

    items: list[ItemReport] = []
    started = time.time()
    for idx, p in enumerate(inputs, 1):
        logger.info("[%d/%d] Processing: %s", idx, total, p.name)
        t0 = time.time()
        before = _probe_to_jsonable_dict(p)

        out_untrunc = out_dir / f"{p.stem}_untrunc{p.suffix}"
        r: ExecResult = repair_with_untrunc(tpl, p, out_untrunc, untrunc=str(untrunc_exe))

        if not r.ok:
            logger.warning("[%d/%d] untrunc FAILED for %s: %s", idx, total, p.name, r.stderr[:200])

        # 二次封装整理（提升播放器兼容性）
        ff_sanitize: ExecResult | None = None
        out_final = out_dir / f"{p.stem}_final{p.suffix}"
        if r.ok and out_untrunc.exists() and tools.ffmpeg:
            ff_sanitize = sanitize_container_with_ffmpeg(out_untrunc, out_final, ffmpeg=str(tools.ffmpeg))
            if not ff_sanitize.ok:
                # copy 失败时降级为"重编码音频"
                ff_sanitize = sanitize_audio_with_ffmpeg(out_untrunc, out_final, ffmpeg=str(tools.ffmpeg))

        # 可选：重编码（用于"花屏/扭曲"等码流级问题，耗时较长）
        ff_reencode: ExecResult | None = None
        out_reencode = out_dir / f"{p.stem}_reencode{p.suffix}"
        if reencode_video and r.ok and out_untrunc.exists() and tools.ffmpeg:
            ff_reencode = reencode_av_with_ffmpeg(out_untrunc, out_reencode, ffmpeg=str(tools.ffmpeg))

        # 主要输出选择顺序：reencode > final > untrunc
        if ff_reencode and ff_reencode.ok and out_reencode.exists():
            out_main = out_reencode
        elif ff_sanitize and ff_sanitize.ok and out_final.exists():
            out_main = out_final
        else:
            out_main = out_untrunc

        after = _probe_to_jsonable_dict(out_main) if r.ok and out_main.exists() else None

        fp_ok: bool | None = None
        fp_err: str | None = None
        if r.ok and tools.ffprobe and out_main.exists():
            fp = ffprobe_json(out_main, ffprobe=str(tools.ffprobe))
            fp_ok = fp.ok
            fp_err = None if fp.ok else fp.stderr

        elapsed = int((time.time() - t0) * 1000)

        # 清理未使用的中间文件
        if cleanup:
            intermediates = {out_untrunc, out_final, out_reencode}
            intermediates.discard(out_main)
            for tmp_file in intermediates:
                _try_remove(tmp_file)

        status = "OK" if r.ok else "FAILED"
        logger.info("[%d/%d] %s — %s (%.1fs)", idx, total, status, p.name, elapsed / 1000)

        items.append(
            ItemReport(
                input_path=str(p),
                output_path=str(out_main),
                template_path=str(tpl),
                before_probe=before,
                after_probe=after,
                untrunc=asdict(r),
                ffmpeg_sanitize=(asdict(ff_sanitize) if ff_sanitize else None),
                ffmpeg_reencode=(asdict(ff_reencode) if ff_reencode else None),
                ffprobe_ok=fp_ok,
                ffprobe_error=fp_err,
                elapsed_ms=elapsed,
            )
        )

    finished = time.time()
    ok_count = sum(1 for i in items if i.untrunc.get("ok"))
    logger.info("Batch complete: %d/%d succeeded in %.1fs", ok_count, total, finished - started)

    report = BatchReport(
        started_at=started,
        finished_at=finished,
        input_dir=str(in_dir),
        template_file=str(tpl),
        output_dir=str(out_dir),
        tools={"untrunc": str(tools.untrunc) if tools.untrunc else None, "ffprobe": str(tools.ffprobe) if tools.ffprobe else None},
        items=items,
    )

    if report_path:
        rp = Path(report_path)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")

    return report
