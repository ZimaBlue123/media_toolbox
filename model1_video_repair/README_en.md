# Module 1: Video Repair (module1_video_repair)

[简体中文](README.md) | English

Goal: Repair "unplayable" video files into playable ones without overwriting original files.

## Common Unplayable Causes

- **Video missing `moov`** (index/metadata not written, common with recording interruption). Usually requires `untrunc` to rebuild using a "same-settings normal video".
- **`moov` at end of file** (faststart issue), can use `ffmpeg` remux to move `moov` forward.
- **Container/codec not supported by player**, try transcoding or different player (e.g., VLC).

## Supported Video Formats

`.mp4` `.mov` `.m4v` `.avi` `.mkv` `.webm` `.flv` `.wmv` `.ts` `.mts` `.m2ts` `.vob` `.3gp` `.3g2` `.mpg` `.mpeg` `.mxf` `.ogv` `.rm` `.rmvb` `.divx` `.asf` `.f4v`

## Usage (Recommended)

In PowerShell, navigate to this module directory:

```bash
cd "E:\Cursor Project\11-av_media_repair\module1_video_repair"
```

### 0) Install (Optional)

This module has **zero third-party Python dependencies**. Recommended to run with Python 3.9+.

```bash
python -m pip install -e .
```

### 1) Diagnose File (Check for Missing moov)

```bash
python -m video_repair probe "E:\Cursor Project\recording1-20260401.mp4"
```

### 2) Try FFmpeg Lossless Remux (For moov at end)

> Requires `ffmpeg` installed and `ffmpeg.exe` in PATH.

```bash
python -m video_repair remux "E:\Cursor Project\input.mp4" -o "E:\Cursor Project\output_remux.mp4"
```

### 3) Repair with untrunc (For Missing moov)

> Requires:
> - A "same recording settings" normal sample video `good.mp4` (a few seconds is enough)
> - `untrunc.exe` (on Windows, this project can auto-download and cache to `tools/untrunc/`)

```bash
python -m video_repair untrunc "E:\Cursor Project\good.mp4" "E:\Cursor Project\recording1-20260401.mp4" -o "E:\Cursor Project\output_fixed.mp4" --untrunc "C:\path\to\untrunc.exe"
```

### 4) Batch Rebuild moov using "Normal Same-Settings Video"

Directory convention:

- Corrupted videos: `module1_video_repair/input/`
- Normal videos: `module1_video_repair/template/`
- Output directory: `module1_video_repair/output/`

One-click batch repair + self-check (writes JSON report and auto-cleans intermediate files):

```bash
python -m video_repair batch-untrunc `
  --input-dir "E:\Cursor Project\11-av_media_repair\module1_video_repair\input" `
  --template-dir "E:\Cursor Project\11-av_media_repair\module1_video_repair\template" `
  --output-dir "E:\Cursor Project\11-av_media_repair\module1_video_repair\output" `
  --report "E:\Cursor Project\11-av_media_repair\module1_video_repair\output\report.json"
```

If after repair "file opens but video is distorted/blocky/some players have no audio", enable **strong fallback re-encoding** (slower but best compatibility):

```bash
python -m video_repair batch-untrunc `
  --input-dir "E:\Cursor Project\11-av_media_repair\module1_video_repair\input" `
  --template-dir "E:\Cursor Project\11-av_media_repair\module1_video_repair\template" `
  --output-dir "E:\Cursor Project\11-av_media_repair\module1_video_repair\output" `
  --report "E:\Cursor Project\11-av_media_repair\module1_video_repair\output\report.json" `
  --reencode-video
```

### 5) Run Unit Tests

```bash
python -m unittest discover -s tests -v
```

## Safety Tips

- Always backup original files and set to read-only
- Use new filenames for output (this tool does this by default)