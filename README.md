# AV Media Toolbox (多媒体处理与分析工具箱)

**音视频处理、图像定位及多模态 AI 分析的综合工具箱**（Windows 优先，跨平台兼容）

[English](README_en.md) | 简体中文
---

## 项目概述

本项目是一个综合性的多媒体工具箱，目前包含三大核心模块，覆盖了从底层的**损坏视频修复**，到**图片元数据解析**，再到**多模态 AI 视频智能分析**的全方位场景。

### 核心模块一览

| 模块名称 | 核心功能 | 主要技术栈/依赖 |
|---------|---------|----------------|
| **Model 1: 视频修复** (`model1_video_repair`) | 修复因录制中断、损坏缺失 moov atom 的 MP4/MOV 等视频。支持批量无损重封装、音频重编码和彻底重编码。 | `ffmpeg`, `ffprobe`, `untrunc` |
| **Model 2: 图片定位** (`model2_image_location`) | 提取照片中的 EXIF 元数据，获取拍摄时的精确 GPS 经纬度位置信息并实现地图映射。 | `exifread`, `geopy` |
| **Model 3: 视频内容分析** (`model3_video_analysis`) | **(New!)** 本地离线的纯免费 AI 多模态视频分析。通过抽帧进行画面理解，通过提取音频进行语音识别，最后双轨融合进行内容总结和智能问答。 | `ollama` (moondream, qwen2.5:1.5b), `openai-whisper` |

---

## 模块快速入门

### ➡️ Model 1: 视频修复模块
用于修复无法播放的受损视频，支持目录级批量修复。
```bash
# 进入模块
cd model1_video_repair
pip install -r requirements.txt

# 批量修复（自动下载所需工具）
python -m video_repair batch-untrunc \
  --input-dir ./input \
  --template-dir ./template \
  --output-dir ./output
```
*更多详情请查阅 [model1_video_repair/README.md](model1_video_repair/README.md)*

### ➡️ Model 2: 图片定位模块
用于读取照片隐藏的 GPS 信息。
```bash
# 进入模块
cd model2_image_location
pip install -r requirements.txt
# 运行主程序
python main.py
```
*更多详情请查阅 [model2_image_location/README.md](model2_image_location/README.md)*

### ➡️ Model 3: 视频内容分析模块 (AI 本地化)
基于本地 Ollama 框架，完全免费、零隐私泄露的视频内容理解。
```bash
# 进入模块
cd model3_video_analysis
pip install -r requirements.txt

# 下载所需的本地大模型
ollama pull moondream:latest
ollama pull qwen2.5:1.5b

# 运行交互式智能分析工具
python main.py
```
*此模块支持自动缓存上下文，对同一视频多次提问可实现秒答。更多详情请查阅 [model3_video_analysis/README.md](model3_video_analysis/README.md)*

---

## 整体项目结构

```text
media_toolbox/
├── model1_video_repair/          # [模块 1] 视频底层修复工具
│   ├── src/video_repair/         # 修复算法逻辑
│   ├── tests/                    # 单元测试
│   ├── requirements.txt
│   └── README.md
├── model2_image_location/        # [模块 2] 照片 GPS EXIF 分析工具
│   ├── src/image_location/
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
├── model3_video_analysis/        # [模块 3] AI 视频内容多模态分析工具
│   ├── bin/                      # (自动克隆) 专用的 ffmpeg 二进制环境
│   ├── models/                   # (自动下载) 本地存储的 Whisper 语音模型
│   ├── main.py                   # 交互式 CLI 入口
│   ├── video_analyzer.py         # 音视频分离、并发抽帧与 AI 总结核心逻辑
│   ├── requirements.txt
│   └── README.md
├── tools/                        # (Model 1 自动下载的缓存工具目录)
├── README.md                     # 本工具箱主说明文档
└── README_en.md                  # 英文说明文档
```

---

## 依赖声明与环境建议

*   **操作系统**：优先支持 Windows (已自动处理各类环境路径兼容)，跨平台支持 macOS / Linux。
*   **Python 版本**：推荐 `Python 3.10+`。
*   **特殊依赖**：Model 3 需要用户在本地提前安装好 [Ollama](https://ollama.com/)，并保证其处于后台运行状态。所有 Whisper 的相关环境（如特定的 ffmpeg）已在代码中实现了静默自动适配，开箱即用。

---

## License

MIT License
