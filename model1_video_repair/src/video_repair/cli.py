from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from .mp4_probe import probe_mp4_atoms
from .batch import repair_dir_with_untrunc
from .strategies import repair_with_untrunc, remux_with_ffmpeg


def _print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_probe(args: argparse.Namespace) -> int:
    r = probe_mp4_atoms(args.input)
    _print_json(
        {
            "path": str(r.path),
            "size_bytes": r.size_bytes,
            "header_has_ftyp": r.header_has_ftyp,
            "header_has_mdat": r.header_has_mdat,
            "header_has_moov": r.header_has_moov,
            "file_has_moov": r.file_has_moov,
            "likely_issue": ("missing_moov" if not r.file_has_moov and r.header_has_ftyp and r.header_has_mdat else "unknown"),
        }
    )
    return 0


def cmd_remux(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    out = Path(args.output) if args.output else inp.with_name(inp.stem + "_remux.mp4")
    r = remux_with_ffmpeg(args.input, out, ffmpeg=args.ffmpeg)
    if not r.ok:
        sys.stderr.write(r.stderr + "\n")
        return r.returncode or 1
    print(str(out))
    return 0


def cmd_untrunc(args: argparse.Namespace) -> int:
    broken = Path(args.broken)
    out = Path(args.output) if args.output else broken.with_name(broken.stem + "_fixed.mp4")
    r = repair_with_untrunc(args.good, args.broken, out, untrunc=args.untrunc)
    if not r.ok:
        sys.stderr.write(r.stderr + "\n")
        return r.returncode or 1
    print(str(out))
    return 0


def cmd_batch_untrunc(args: argparse.Namespace) -> int:
    report = repair_dir_with_untrunc(
        input_dir=args.input_dir,
        template_dir=args.template_dir,
        output_dir=args.output_dir,
        tools_dir=args.tools_dir,
        untrunc=args.untrunc,
        ffprobe=args.ffprobe,
        reencode_video=bool(args.reencode_video),
        report_path=args.report,
        cleanup=not args.no_cleanup,
    )
    _print_json(asdict(report))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="video_repair")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe", help="检查 MP4 是否缺少 moov/基本 atom")
    p_probe.add_argument("input")
    p_probe.set_defaults(func=cmd_probe)

    p_remux = sub.add_parser("remux", help="用 ffmpeg 无损重封装（适用于 moov 在末尾等情况）")
    p_remux.add_argument("input")
    p_remux.add_argument("-o", "--output", default=None)
    p_remux.add_argument("--ffmpeg", default=None, help="ffmpeg.exe 路径（可选）")
    p_remux.set_defaults(func=cmd_remux)

    p_untrunc = sub.add_parser("untrunc", help="用 untrunc 修复缺少 moov 的 MP4")
    p_untrunc.add_argument("good", help="同设置的正常样本视频 good.mp4")
    p_untrunc.add_argument("broken", help="坏的视频（打不开的 mp4）")
    p_untrunc.add_argument("-o", "--output", default=None)
    p_untrunc.add_argument("--untrunc", default=None, help="untrunc.exe 路径（可选）")
    p_untrunc.set_defaults(func=cmd_untrunc)

    p_batch = sub.add_parser("batch-untrunc", help="按目录批量用 untrunc 修复（方案 B）")
    p_batch.add_argument("--input-dir", required=True, help="异常视频目录（批量）")
    p_batch.add_argument("--template-dir", required=True, help="正常视频目录（用于挑选样本视频）")
    p_batch.add_argument("--output-dir", required=True, help="输出目录（不覆盖原文件）")
    p_batch.add_argument("--report", default=None, help="写出 JSON 报告到指定路径（可选）")
    p_batch.add_argument("--tools-dir", default=None, help="工具下载/缓存目录（可选，默认 module1_video_repair/tools）")
    p_batch.add_argument("--untrunc", default=None, help="untrunc.exe 路径（可选，不传则自动下载/查找 PATH）")
    p_batch.add_argument("--ffprobe", default=None, help="ffprobe.exe 路径（可选，不传则自动下载/查找 PATH）")
    p_batch.add_argument("--reencode-video", action="store_true", help="强兜底：对输出进行视频+音频重编码（解决花屏/扭曲，耗时长）")
    p_batch.add_argument("--no-cleanup", action="store_true", help="保留中间文件（默认自动清理未使用的中间输出）")
    p_batch.set_defaults(func=cmd_batch_untrunc)

    return p


def main(argv: list[str] | None = None) -> int:
    # 配置日志：默认 INFO 级别输出到 stderr，不影响 JSON stdout 输出
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
