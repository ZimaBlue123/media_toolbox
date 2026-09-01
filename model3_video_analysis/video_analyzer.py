import cv2
import ollama
import os
import warnings
import concurrent.futures
import logging
import shutil
from typing import List, Optional

warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

class LocalVideoAnalyzer:
    def __init__(self, vision_model: str = 'moondream', text_model: str = 'qwen2.5:1.5b') -> None:
        """
        初始化本地视频分析器
        """
        self.vision_model: str = vision_model
        self.text_model: str = text_model
        self.frame_descriptions: List[str] = []
        self.audio_transcript: str = ""
        self.video_context: str = ""
        self.whisper_model = None

    def load_whisper(self) -> None:
        """延迟加载 Whisper 模型，并配置内置 FFmpeg 路径"""
        if self.whisper_model is not None:
            return
            
        logger.info("[音频模块] 正在准备 Whisper 语音模型...")
        project_root = os.path.dirname(os.path.abspath(__file__))
        local_bin_dir = os.path.join(project_root, "bin")
        local_models_dir = os.path.join(project_root, "models")
        
        try:
            os.makedirs(local_bin_dir, exist_ok=True)
            os.makedirs(local_models_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"[音频模块] 无法创建本地依赖文件夹: {e}")
            
        try:
            import imageio_ffmpeg
            original_ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            
            local_ffmpeg_exe = os.path.join(local_bin_dir, "ffmpeg.exe")
            if not os.path.exists(local_ffmpeg_exe):
                shutil.copy(original_ffmpeg_exe, local_ffmpeg_exe)

            if local_bin_dir not in os.environ["PATH"]:
                os.environ["PATH"] = local_bin_dir + os.pathsep + os.environ["PATH"]
        except ImportError:
            logger.warning("[音频模块] 找不到 imageio_ffmpeg 库，可能无法自动配置 ffmpeg。")
        except Exception as e:
            logger.error(f"[音频模块] 本地配置 FFmpeg 失败: {e}")
        
        try:
            import whisper
            self.whisper_model = whisper.load_model("base", download_root=local_models_dir)
            logger.info("[音频模块] 语音模型加载完毕，开始识别！")
        except Exception as e:
            logger.error(f"[音频模块] Whisper 加载失败: {e}")

    def extract_audio_transcript(self, video_path: str) -> None:
        """提取并转写视频中的语音"""
        if not os.path.exists(video_path):
            logger.error(f"[音频模块] 视频文件不存在: {video_path}")
            return
            
        self.load_whisper()
        if not self.whisper_model:
            return

        try:
            result = self.whisper_model.transcribe(video_path)
            self.audio_transcript = result.get("text", "").strip()
            
            if self.audio_transcript:
                logger.info(f"[音频模块] 语音分析完成！提取到文本: {self.audio_transcript[:60]}...")
            else:
                logger.info("[音频模块] 分析完成，未检测到语音或视频静音。")
        except Exception as e:
            logger.error(f"[音频模块] 语音提取失败: {e}")
            self.audio_transcript = ""

    def extract_and_analyze_frames(self, video_path: str, interval_seconds: int = 5) -> None:
        """抽帧并使用视觉模型分析"""
        if not os.path.exists(video_path):
            logger.error(f"[画面模块] 视频文件不存在: {video_path}")
            return
            
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"[画面模块] 无法打开视频文件: {video_path}")
            return
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            cap.release()
            raise ValueError("无法读取视频内容，请检查路径或格式是否受支持。")
        
        frame_interval = int(fps * interval_seconds)
        frame_count = 0
        success, image = cap.read()
        self.frame_descriptions = []
        
        while success:
            if frame_count % frame_interval == 0:
                success_encode, buffer = cv2.imencode('.jpg', image)
                if success_encode:
                    image_bytes = buffer.tobytes()
                    time_stamp = frame_count // int(fps)
                    
                    try:
                        response = ollama.generate(
                            model=self.vision_model,
                            prompt='Describe what is happening in this image in detail.',
                            images=[image_bytes]
                        )
                        desc = response.get('response', '').strip()
                        self.frame_descriptions.append(f"[Time: {time_stamp}s]: {desc}")
                        logger.info(f"[画面模块] {time_stamp}秒 关键帧分析完成")
                    except Exception as e:
                        logger.error(f"[画面模块] {time_stamp}秒 分析失败 ({e})")
            
            success, image = cap.read()
            frame_count += 1
            
        cap.release()
        logger.info("[画面模块] 所有关键帧分析完毕！")

    def process_video(self, video_path: str, interval_seconds: int = 5) -> None:
        """完整的视频分析工作流：多线程并发处理画面与语音"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"找不到视频文件: {video_path}")
            
        cache_file = video_path + ".context.txt"
        if os.path.exists(cache_file):
            logger.info(f"📂 检测到历史分析记录，直接从缓存加载：{os.path.basename(cache_file)}")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.video_context = f.read()
                if "=== 视频语音对白（自动识别） ===" in self.video_context:
                    self.audio_transcript = self.video_context.split("=== 视频语音对白（自动识别） ===")[-1].strip()
                return
            except Exception as e:
                logger.warning(f"无法读取缓存文件 {cache_file}, 将重新进行分析 ({e})")
            
        logger.info("🚀 开始多线程加速分析 (画面抽帧与语音识别同步进行)...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_audio = executor.submit(self.extract_audio_transcript, video_path)
            future_frames = executor.submit(self.extract_and_analyze_frames, video_path, interval_seconds)
            concurrent.futures.wait([future_audio, future_frames])
        
        logger.info("🔄 音视频双轨数据处理完毕，正在拼装上下文...")
        
        frames_text = "\n".join(self.frame_descriptions)
        audio_text = self.audio_transcript if self.audio_transcript else "（无）"
        
        self.video_context = f"=== 视频画面描述（英文） ===\n{frames_text}\n\n=== 视频语音对白（自动识别） ===\n{audio_text}"
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(self.video_context)
            logger.info(f"💾 分析上下文已自动保存至：{os.path.basename(cache_file)}，下次分析该视频将秒开！")
        except Exception as e:
            logger.error(f"⚠️ 缓存保存失败：{e}")

    def summarize(self) -> str:
        """结合画面与语音进行总结"""
        if not self.video_context:
            raise ValueError("请先运行 process_video 流程。")
            
        prompt = f"以下是系统从一段视频中自动提取的信息，包含【画面描述】和【语音对白】两部分：\n{self.video_context}\n\n请作为专业的视频内容分析员，综合“画面里发生的事情”和“人物的对白语音”，用【中文】详细总结这段视频的主要内容、场景变化以及具体发生了什么事件。"
        try:
            response = ollama.generate(model=self.text_model, prompt=prompt)
            return response.get('response', '')
        except Exception as e:
            logger.error(f"生成总结失败: {e}")
            return "分析失败，请检查模型运行状态。"

    def answer_question(self, question: str) -> str:
        """结合画面与语音进行问答"""
        if not self.video_context:
            raise ValueError("请先运行 process_video 流程。")
            
        prompt = f"以下是系统从视频提取的内容，包含【画面描述】和【语音对白】：\n{self.video_context}\n\n用户问题：{question}\n\n请结合画面和语音双方面的信息，用【中文】准确回答用户的问题。如果提供的信息中无法推断出答案，请如实告知。"
        try:
            response = ollama.generate(model=self.text_model, prompt=prompt)
            return response.get('response', '')
        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            return "回答失败，请检查模型运行状态。"
