
# 视频内容分析 (Model_3)

这是本地完全免费开源的多模态视频内容分析工具。结合了 \qwen2.5:1.5b\，\moondream\ 和 \openai-whisper\ 模型。

## 功能
- 自动提取视频画面，交由 \moondream\ 视觉大模型理解环境变化。
- 自动提取并转写视频语音，交由 \whisper\ 语音大模型获取文本。
- 双轨拼接多模态上下文，交由 \qwen2.5:1.5b\ 提供深度总结和针对性问答。
- 多线程并行加速处理，并具备结果缓存功能。

## 安装
1. 安装依赖:
   \\\ash
   pip install -r requirements.txt
   \\\
2. 安装并启动 Ollama，并拉取模型:
   \\\ash
   ollama pull moondream:latest
   ollama pull qwen2.5:1.5b
   \\\
3. 运行程序:
   \\\ash
   python main.py
   \\\

