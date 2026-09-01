# AV Media Toolbox 

**A comprehensive toolkit for Audio/Video Processing, Image Geolocation, and Multimodal AI Video Analysis** (Windows-first, cross-platform compatible)

[English](README_en.md) | [简体中文](README.md)

---

## Overview

This project is a comprehensive multimedia toolkit that currently includes three core modules, covering everything from low-level **corrupted video repair**, to **image EXIF metadata parsing**, and all the way to **multimodal AI-powered video analysis**.

### Core Modules

| Module | Core Functionality | Primary Tech Stack |
|--------|--------------------|--------------------|
| **Model 1: Video Repair** (`model1_video_repair`) | Repairs MP4/MOV videos corrupted by recording interruptions or missing moov atoms. Supports batch lossless remuxing, audio re-encoding, and full re-encoding. | `ffmpeg`, `ffprobe`, `untrunc` |
| **Model 2: Image Geolocation** (`model2_image_location`) | Extracts EXIF metadata from photos to retrieve precise GPS coordinates and perform map/geolocation mapping. | `exifread`, `geopy` |
| **Model 3: Video AI Analysis** (`model3_video_analysis`) | **(New!)** Local, fully offline, and free multimodal AI video analysis. Comprehends scenes via frame extraction, transcribes speech via audio extraction, and merges them for intelligent content summarization and Q&A. | `ollama` (moondream, qwen2.5:1.5b), `openai-whisper` |

---

## Quick Start by Module

### ➡️ Model 1: Video Repair
Used for repairing unplayable or corrupted videos. Supports directory-level batch processing.
```bash
# Navigate to module
cd model1_video_repair
pip install -r requirements.txt

# Batch repair (auto-downloads required tools)
python -m video_repair batch-untrunc \
  --input-dir ./input \
  --template-dir ./template \
  --output-dir ./output
```
*For more details, see [model1_video_repair/README.md](model1_video_repair/README.md)*

### ➡️ Model 2: Image Geolocation
Used to read hidden GPS information from photos.
```bash
# Navigate to module
cd model2_image_location
pip install -r requirements.txt

# Run main program
python main.py
```
*For more details, see [model2_image_location/README.md](model2_image_location/README.md)*

### ➡️ Model 3: Multimodal Video Analysis (Local AI)
Fully offline, zero-privacy-leak video understanding based on the local Ollama framework.
```bash
# Navigate to module
cd model3_video_analysis
pip install -r requirements.txt

# Download required local LLMs
ollama pull moondream:latest
ollama pull qwen2.5:1.5b

# Run the interactive analysis tool
python main.py
```
*This module supports automatic context caching, enabling instant answers for repeated questions on the same video. For more details, see [model3_video_analysis/README.md](model3_video_analysis/README.md)*

---

## Overall Project Structure

```text
media_toolbox/
├── model1_video_repair/          # [Module 1] Low-level video repair
│   ├── src/video_repair/         
│   ├── tests/                    
│   ├── requirements.txt
│   └── README.md
├── model2_image_location/        # [Module 2] Photo GPS EXIF analysis
│   ├── src/image_location/
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
├── model3_video_analysis/        # [Module 3] Multimodal AI video analysis
│   ├── bin/                      # Auto-cloned local ffmpeg binary 
│   ├── models/                   # Auto-downloaded local Whisper models
│   ├── main.py                   # Interactive CLI entry point
│   ├── video_analyzer.py         # Core logic for frame/audio extraction & AI
│   ├── requirements.txt
│   └── README.md
├── tools/                        # (Auto-downloaded tool cache for Model 1)
├── README.md                     # Main documentation (Chinese)
└── README_en.md                  # Main documentation (English)
```

---

## Dependencies & Environment Recommendations

*   **OS**: Windows-first (automatic handling of environment paths implemented), with cross-platform support for macOS / Linux.
*   **Python**: Recommended `Python 3.10+`.
*   **Special Requirements**: Model 3 requires users to install [Ollama](https://ollama.com/) locally and ensure it is running in the background. All Whisper dependencies (like specific ffmpeg versions) are handled automatically behind the scenes.

---

## License

MIT License