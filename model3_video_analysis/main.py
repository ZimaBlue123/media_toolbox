import os
import sys
import logging
from typing import List, Optional
import ollama
from video_analyzer import LocalVideoAnalyzer

# 设定日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_environment() -> bool:
    """检查 Ollama 是否运行，以及必需的模型是否存在"""
    try:
        models_info = ollama.list()
    except Exception as e:
        logging.error(f"【系统错误】无法连接到 Ollama！({e})")
        print("请确保您已经安装了 Ollama，并且软件处于运行状态。")
        print("下载地址: https://ollama.com/")
        return False
        
    available_models: List[str] = []
    if hasattr(models_info, 'models'):
        available_models = [m.model for m in models_info.models]
    else:
        available_models = [m.get('model', m.get('name', '')) for m in models_info.get('models', [])] # type: ignore
        
    required_models: List[str] = ['moondream:latest', 'qwen2.5:1.5b']
    
    missing_models: List[str] = []
    for req in required_models:
        if req not in available_models and req.replace(':latest', '') not in available_models:
            missing_models.append(req)
            
    if missing_models:
        logging.warning("【模型缺失】检测到您还没下载所需的本地大模型。")
        print("请打开一个新的终端，运行以下命令进行下载（下载速度取决于您的网络）：")
        for m in missing_models:
            print(f"ollama pull {m}")
        print("\n请在下载完成后重新运行本程序。")
        return False
        
    return True

def main() -> None:
    print("=======================================")
    print("  免费开源本地版 - 视频内容分析 (Model_3) ")
    print("=======================================")

    print("正在检查本地 AI 环境...")
    if not check_environment():
        sys.exit(1)
    print("环境正常，所有本地模型已就绪！\n")

    analyzer = LocalVideoAnalyzer(vision_model='moondream', text_model='qwen2.5:1.5b')

    input_dir = "input"
    available_videos: List[str] = []
    
    if os.path.exists(input_dir):
        available_videos = [f for f in os.listdir(input_dir) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]
        
    if available_videos:
        print(f"\n在 '{input_dir}' 文件夹中发现以下视频：")
        for i, v_name in enumerate(available_videos):
            print(f"  [{i+1}] {v_name}")
        print("  [0] 手动输入其他路径")
        
        choice = input(f"\n请选择视频序号 (0-{len(available_videos)}) [直接回车默认选 1]: ").strip()
        if not choice:
            choice = "1"
            
        if choice.isdigit() and 1 <= int(choice) <= len(available_videos):
            video_path = os.path.join(input_dir, available_videos[int(choice)-1])
            print(f"已选择视频: {video_path}")
        else:
            video_path = input("请输入视频的具体路径: ").strip()
    else:
        video_path = input("请输入待分析视频的路径 (建议将视频放入 input 文件夹): ").strip()
    
    if video_path.startswith('"') and video_path.endswith('"'):
        video_path = video_path[1:-1]
    if video_path.startswith("'") and video_path.endswith("'"):
        video_path = video_path[1:-1]

    if not os.path.exists(video_path):
        logging.error("找不到该文件，请检查路径是否正确。")
        sys.exit(1)

    try:
        interval_input = input("请输入抽帧间隔(秒) [默认 5]: ").strip()
        interval = int(interval_input) if interval_input.isdigit() else 5
        
        analyzer.process_video(video_path, interval_seconds=interval)

        print("\n=======================================")
        print("           [核心功能一] 视频总结       ")
        print("=======================================")
        print("正在呼叫本地 Qwen 模型生成总结，请稍候...")
        summary = analyzer.summarize()
        print("\n【视频内容概述】：")
        print(summary)
        print("=======================================\n")

        print("=======================================")
        print("           [核心功能二] 视频问答       ")
        print("=======================================")
        print("您可以提出任何关于视频的具体问题。")
        print("(输入 'q', 'quit' 或 'exit' 退出程序)\n")

        while True:
            question = input("请输入您的问题: ").strip()
            if question.lower() in ['q', 'quit', 'exit']:
                print("准备退出...")
                break
            if not question:
                continue

            print("思考中...")
            answer = analyzer.answer_question(question)
            print("\n【回答】：")
            print(answer)
            print("-" * 39)

    except KeyboardInterrupt:
        logging.info("程序被用户手动中断。")
    except Exception as e:
        logging.exception(f"运行中发生未捕获错误: {e}")
    finally:
        print("感谢使用完全免费、注重隐私的本地分析工具！再见。")

if __name__ == "__main__":
    main()
