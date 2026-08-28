# av_media_repair

**视频修复与音视频处理工具集**（Windows 优先，跨平台兼容）

[English](README_en.md) | 简体中文

---

## 项目概述

本项目用于**修复损坏/不完整的视频文件**并提供**音视频格式处理能力**。核心场景：MP4/MOV/MKV 等格式因录制中断、传输损坏、编码错误等问题导致的播放异常。

### 主要功能

| 功能 | 说明 |
|------|------|
| **损坏视频修复** | 通过 untrunc 重建缺失的 moov atom（索引/元数据） |
| **批量处理** | 支持目录级批量修复，自动选取模板视频与清理中间文件 |
| **格式兼容增强** | 无损重封装/音频重编码/完整重编码三档处理 |
| **格式探测** | MP4 ISO BMFF box 结构探测，精准诊断缺失的 moov/mdat |
| **FFmpeg 工具链** | 自动下载/管理需要的 ffmpeg/ffprobe/untrunc |

### 支持的视频格式

`.mp4` `.mov` `.m4v` `.avi` `.mkv` `.webm` `.flv` `.wmv` `.ts` `.mts` `.m2ts` `.vob` `.3gp` `.3g2` `.mpg` `.mpeg` `.mxf` `.ogv` `.rm` `.rmvb` `.divx` `.asf` `.f4v`

---

## 快速开始

### 方式一：批量修复（推荐）

```bash
# 0 依赖，直接使用标准库或可编辑安装
pip install -r requirements.txt

# 批量修复（自动下载工具）
python -m video_repair batch-untrunc \
  --input-dir ./input \
  --template-dir ./template \
  --output-dir ./output
```

### 方式二：单文件处理

```bash
# 探测 MP4 结构
python -m video_repair probe input.mp4

# 重新封装（无损，提升兼容性）
python -m video_repair remux input.mp4 -o output.mp4

# 用 untrunc 修复
python -m video_repair untrunc good.mp4 broken.mp4 -o fixed.mp4
```

### 方式三：Python API

```python
from video_repair import repair_dir_with_untrunc

report = repair_dir_with_untrunc(
    input_dir="./input",
    template_dir="./template",
    output_dir="./output",
    reencode_video=True,  # 启用重编码（耗时更长但更彻底）
    report_path="./repair_report.json",
    cleanup=True,         # 自动清理中间产物
)
print(f"成功: {sum(1 for i in report.items if i.untrunc.get('ok'))}/{len(report.items)}")
```

---

## 运行测试

本项目内置完整的单元测试套件，零外部依赖即可直接运行：

```bash
cd model1_video_repair
python -m unittest discover -s tests -v
```

---

## 项目结构

```
11-av_media_repair/
├── model1_video_repair/          # 主模块
│   ├── src/video_repair/
│   │   ├── __init__.py            # API 导出
│   │   ├── __main__.py            # 模块入口 (python -m video_repair)
│   │   ├── cli.py                 # 命令行接口
│   │   ├── batch.py               # 批量修复逻辑
│   │   ├── strategies.py          # FFmpeg/untrunc 策略
│   │   ├── mp4_probe.py           # ISO BMFF box 探测
│   │   ├── ffprobe.py             # ffprobe 封装
│   │   └── tooling.py             # 工具自动下载/管理
│   ├── tests/                     # 单元测试套件 (unittest)
│   ├── input/                     # 输入目录（gitkeep）
│   ├── output/                    # 输出目录（gitkeep）
│   └── template/                  # 模板视频目录（gitkeep）
├── model2_image_location/         # 图片位置识别模块
│   ├── src/image_location/
│   ├── tests/
│   ├── requirements.txt
│   ├── README.md
│   └── README_en.md
├── tools/                         # 工具缓存目录（自动下载）
├── requirements.txt
└── README.md
```

---

## 修复流程说明

### 三档处理策略

1. **无损重封装** (`sanitize_container`)
   - 仅重新封装，不重编码
   - 添加 `genpts` 生成时间戳
   - `faststart` 前移 moov 原子
   - 速度最快，无质量损失

2. **音频重编码** (`sanitize_audio`)
   - 视频仍 copy，音频重编码为 AAC
   - 解决音频流损坏但视频正常的情况

3. **完整重编码** (`reencode_av`)
   - H.264(libopenh264) + AAC/Vorbis
   - 最终兜底方案，耗时最长
   - 适用于花屏、扭曲等码流级损坏

### 批量修复优先级

```
输入 → untrunc 重建 moov → sanitize(重封) → (可选)reencode → 输出
                               ↓ 失败时降级
                          sanitize_audio(重编码音频)
```

---

## 依赖工具

| 工具 | 用途 | 获取方式 |
|------|------|----------|
| `ffmpeg` | 音视频处理 | 自动下载或 PATH 中已有 |
| `ffprobe` | 媒体信息探测 | 自动下载或 PATH 中已有 |
| `untrunc` | 重建缺失的 moov | 自动下载或手动指定 |

> 工具自动下载使用了 [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) 和 [anthwlock/untrunc](https://github.com/anthwlock/untrunc) 的预编译版本。

---

## 命令行帮助

```
用法: video_repair <命令> [选项]

可用命令:
  probe          检查 MP4 是否缺少 moov/基本 atom
  remux          用 ffmpeg 无损重封装（适用于 moov 在末尾等情况）
  untrunc        用 untrunc 修复缺少 moov 的 MP4
  batch-untrunc  按目录批量用 untrunc 修复

输入 "video_repair <命令> -h" 查看特定命令的帮助
```

---

## License

MIT License
