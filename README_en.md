# av_media_repair

**Video Repair & Audio/Video Processing Toolkit** (Windows-first, cross-platform compatible)

[English](README_en.md) | [简体中文](README.md)

---

## Overview

This project is designed to **repair corrupted/incomplete video files** and provide **audio/video format processing capabilities**. Primary use case: playback issues in MP4/MOV/MKV formats caused by recording interruption, transmission corruption, or encoding errors.

### Key Features

| Feature | Description |
|---------|-------------|
| **Corrupted Video Repair** | Rebuild missing moov atoms (index/metadata) via untrunc |
| **Batch Processing** | Directory-level batch repair with automatic template selection & intermediate cleanup |
| **Format Compatibility** | Lossless remux / Audio re-encode / Full re-encode (3 tiers) |
| **Format Probe** | ISO BMFF box structure probing to accurately diagnose missing moov/mdat |
| **FFmpeg Toolchain** | Auto-download/manage ffmpeg/ffprobe/untrunc |

### Supported Video Formats

`.mp4` `.mov` `.m4v` `.avi` `.mkv` `.webm` `.flv` `.wmv` `.ts` `.mts` `.m2ts` `.vob` `.3gp` `.3g2` `.mpg` `.mpeg` `.mxf` `.ogv` `.rm` `.rmvb` `.divx` `.asf` `.f4v`

---

## Quick Start

### Method 1: Batch Repair (Recommended)

```bash
# Zero third-party dependencies, standard library ready
pip install -r requirements.txt

# Batch repair (auto-downloads tools)
python -m video_repair batch-untrunc \
  --input-dir ./input \
  --template-dir ./template \
  --output-dir ./output
```

### Method 2: Single File Processing

```bash
# Probe MP4 structure
python -m video_repair probe input.mp4

# Remux (lossless, improve compatibility)
python -m video_repair remux input.mp4 -o output.mp4

# Repair with untrunc
python -m video_repair untrunc good.mp4 broken.mp4 -o fixed.mp4
```

### Method 3: Python API

```python
from video_repair import repair_dir_with_untrunc

report = repair_dir_with_untrunc(
    input_dir="./input",
    template_dir="./template",
    output_dir="./output",
    reencode_video=True,  # Enable re-encode (slower but more thorough)
    report_path="./repair_report.json",
    cleanup=True,         # Auto-clean intermediate files
)
print(f"Success: {sum(1 for i in report.items if i.untrunc.get('ok'))}/{len(report.items)}")
```

---

## Running Tests

This project includes a comprehensive test suite using Python's standard `unittest` library (zero external dependencies):

```bash
cd model1_video_repair
python -m unittest discover -s tests -v
```

---

## Project Structure

```
11-av_media_repair/
├── model1_video_repair/          # Main module
│   ├── src/video_repair/
│   │   ├── __init__.py            # API exports
│   │   ├── __main__.py            # Module entry point (python -m video_repair)
│   │   ├── cli.py                 # CLI interface
│   │   ├── batch.py               # Batch repair logic
│   │   ├── strategies.py          # FFmpeg/untrunc strategies
│   │   ├── mp4_probe.py           # ISO BMFF box probing
│   │   ├── ffprobe.py             # ffprobe wrapper
│   │   └── tooling.py             # Tool auto-download/management
│   ├── tests/                     # Test suite (unittest)
│   ├── input/                     # Input directory (gitkeep)
│   ├── output/                    # Output directory (gitkeep)
│   └── template/                  # Template video directory (gitkeep)
├── model2_image_location/         # Image Location Identification module
│   ├── src/image_location/
│   ├── tests/
│   ├── requirements.txt
│   ├── README.md
│   └── README_en.md
├── tools/                         # Tool cache directory (auto-downloaded)
├── requirements.txt
└── README.md
```

---

## Repair Flow

### Three-Tier Processing Strategy

1. **Lossless Remux** (`sanitize_container`)
   - Re-mux only, no re-encode
   - Add `genpts` to generate timestamps
   - `faststart` to move moov atom forward
   - Fastest, no quality loss

2. **Audio Re-encode** (`sanitize_audio`)
   - Video remains copy, audio re-encoded to AAC
   - Solves audio stream corruption while video is intact

3. **Full Re-encode** (`reencode_av`)
   - H.264(libopenh264) + AAC/Vorbis
   - Final fallback, longest processing time
   - For corruption at bitstream level (blocking, distortion, etc.)

### Batch Repair Priority

```
Input → untrunc rebuild moov → sanitize(remux) → (optional) reencode → Output
                               ↓ fallback on failure
                          sanitize_audio(re-encode audio)
```

---

## Dependencies

| Tool | Purpose | How to Get |
|------|---------|------------|
| `ffmpeg` | Audio/Video processing | Auto-download or in PATH |
| `ffprobe` | Media info probing | Auto-download or in PATH |
| `untrunc` | Rebuild missing moov | Auto-download or manual specification |

> Tool auto-download uses pre-built binaries from [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) and [anthwlock/untrunc](https://github.com/anthwlock/untrunc).

---

## CLI Help

```
Usage: video_repair <command> [options]

Available commands:
  probe          Check if MP4 is missing moov/basic atoms
  remux          Lossless remux with ffmpeg (for moov at end etc.)
  untrunc        Repair MP4 missing moov using untrunc
  batch-untrunc  Batch repair by directory using untrunc

Run "video_repair <command> -h" for help on specific commands
```

---

## License

MIT License