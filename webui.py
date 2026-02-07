#!/usr/bin/env python3
"""
Qwen3-TTS WebUI 界面
基于 Gradio 的语音合成 Web 界面

支持三模型：
- CustomVoice 模型：预置音色生成
- Base 模型：声音克隆
- VoiceDesign 模型：文字描述生成声音
"""
import os
import sys
import json
import shutil
import torch
import soundfile as sf
import gradio as gr
from pathlib import Path
from datetime import datetime
from qwen_tts import Qwen3TTSModel
from pydub import AudioSegment
from memory_manager import global_memory_manager, global_model_manager, memory_monitor, init_memory_management
from voice_optimizer import create_voice_optimizer

# 获取脚本所在目录作为基准路径
BASE_DIR = Path(__file__).parent.resolve()
CUSTOM_VOICE_MODEL_PATH = BASE_DIR / "models"
CLONE_MODEL_PATH = BASE_DIR / "models-base"
VOICE_DESIGN_MODEL_PATH = BASE_DIR / "models-voicedesign"

# 克隆音色存储目录
CLONE_VOICES_DIR = BASE_DIR / "cloned_voices"
CLONE_VOICES_DIR.mkdir(exist_ok=True)

# 预置音色列表
SPEAKERS = {
    "vivian": "女声-年轻-可爱-亲切",
    "serena": "女声-年轻-中性",
    "ono_anna": "女声-成熟-温柔",
    "aiden": "男声-年轻-自然",
    "dylan": "男声-成熟-自然",
    "ryan": "男声-成熟-旁白",
    "uncle_fu": "男声-成熟-深沉",
    "eric": "男童-可爱",
    "sohee": "女童-可爱",
}

# 支持的语言
LANGUAGES = ["Auto", "Chinese", "English", "Japanese", "Korean",
             "German", "French", "Russian", "Portuguese", "Spanish", "Italian"]

# 输出目录
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# ========== 克隆音色管理函数 ==========

def get_saved_clones():
    """获取所有保存的克隆音色列表"""
    clones = []
    for clone_dir in CLONE_VOICES_DIR.iterdir():
        if clone_dir.is_dir():
            meta_file = clone_dir / "meta.json"
            if meta_file.exists():
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    clones.append({
                        'id': clone_dir.name,
                        'name': meta.get('name', clone_dir.name),
                        'created': meta.get('created', ''),
                        'ref_text': meta.get('ref_text', ''),
                    })
    return sorted(clones, key=lambda x: x['created'], reverse=True)


def save_clone_voice(name, ref_audio_path, ref_text):
    """保存克隆音色"""
    # 创建安全的文件夹名
    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clone_dir = CLONE_VOICES_DIR / f"{safe_name}_{timestamp}"
    clone_dir.mkdir(exist_ok=True)

    # 复制参考音频
    ref_audio_path = Path(ref_audio_path)
    shutil.copy(ref_audio_path, clone_dir / "reference.wav")

    # 保存元数据
    meta = {
        'name': name,
        'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'ref_text': ref_text,
        'ref_audio': 'reference.wav',
        'type': 'clone',
    }
    with open(clone_dir / "meta.json", 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return clone_dir


def save_voice_design(name, design_instruct, target_text, audio_path):
    """保存设计音色"""
    # 创建安全的文件夹名
    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clone_dir = CLONE_VOICES_DIR / f"{safe_name}_{timestamp}"
    clone_dir.mkdir(exist_ok=True)

    # 复制生成的音频作为参考
    audio_path = Path(audio_path)
    shutil.copy(audio_path, clone_dir / "reference.wav")

    # 保存元数据
    meta = {
        'name': name,
        'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'design_instruct': design_instruct,
        'target_text': target_text,
        'ref_audio': 'reference.wav',
        'type': 'design',
    }
    with open(clone_dir / "meta.json", 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return clone_dir


def load_clone_voice(clone_id):
    """加载保存的克隆音色"""
    clone_dir = CLONE_VOICES_DIR / clone_id
    if not clone_dir.exists():
        return None, None

    meta_file = clone_dir / "meta.json"
    if not meta_file.exists():
        return None, None

    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    ref_audio_path = clone_dir / "reference.wav"
    if not ref_audio_path.exists():
        return None, None

    return str(ref_audio_path), meta.get('ref_text', '')


def delete_clone_voice(clone_id):
    """删除保存的克隆音色"""
    clone_dir = CLONE_VOICES_DIR / clone_id
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
        return True
    return False


def get_clone_choices():
    """获取克隆音色下拉菜单选项"""
    clones = get_saved_clones()
    if not clones:
        return ["无保存的音色"]
    choices = [f"{c['name']} ({c['created']})|{c['id']}" for c in clones]
    return choices


def get_clones_list_markdown():
    """获取克隆音色列表的 Markdown 格式"""
    clones = get_saved_clones()
    if not clones:
        return "*暂无保存的克隆音色*"

    lines = ["| 音色名称 | 创建时间 | ID |", "|----------|----------|-----|"]
    for c in clones:
        lines.append(f"| {c['name']} | {c['created']} | `{c['id']}` |")
    return "\n".join(lines)


def get_all_speaker_choices():
    """获取所有音色选项（预置音色 + 保存的克隆音色）"""
    choices = []

    # 添加预置音色
    for name, desc in SPEAKERS.items():
        choices.append(f"🎭 {name} ({desc})|preset_{name}")

    # 添加保存的克隆音色
    clones = get_saved_clones()
    for c in clones:
        choices.append(f"🎤 {c['name']}|{c['id']}")

    return choices if choices else ["vivian"]


def convert_audio_format(input_path, output_format):
    """转换音频格式"""
    try:
        audio = AudioSegment.from_wav(input_path)

        output_path = input_path.with_suffix(f".{output_format}")

        if output_format == "wav":
            # WAV 格式不需要特殊处理
            return str(input_path)

        elif output_format == "opus":
            audio.export(str(output_path), format="opus", bitrate="64k")
            return str(output_path)

        else:
            return str(input_path)

    except Exception as e:
        print(f"格式转换失败: {e}")
        return str(input_path)


class Qwen3TTSWebUI:
    def __init__(self):
        self.custom_model = None
        self.clone_model = None
        self.voice_design_model = None

        # 检查模型可用性
        self.clone_model_available = CLONE_MODEL_PATH.exists()
        self.voice_design_model_available = VOICE_DESIGN_MODEL_PATH.exists()
        
        # 初始化内存管理
        init_memory_management()

    @memory_monitor(max_memory_gb=4.0)
    def load_custom_model(self):
        """加载 CustomVoice 模型（预置音色）"""
        def load_model():
            print(f"正在加载 CustomVoice 模型: {CUSTOM_VOICE_MODEL_PATH}")
            if not CUSTOM_VOICE_MODEL_PATH.exists():
                raise FileNotFoundError(
                    f"模型目录不存在: {CUSTOM_VOICE_MODEL_PATH}\n"
                    f"请确保 models 文件夹在程序目录下"
                )
            return Qwen3TTSModel.from_pretrained(
                str(CUSTOM_VOICE_MODEL_PATH),
                device_map="cpu",
                dtype=torch.float32,
            )
        
        self.custom_model = global_model_manager.load_model(
            "custom_voice", load_model
        )
        print("CustomVoice 模型加载完成！")
        return self.custom_model

    @memory_monitor(max_memory_gb=4.0)
    def load_clone_model(self):
        """加载 Base 模型（声音克隆）"""
        def load_model():
            if not self.clone_model_available:
                raise FileNotFoundError(
                    f"克隆模型不存在: {CLONE_MODEL_PATH}\n"
                    f"请先运行 download_clone_model.py 下载 Base 模型"
                )
            print(f"正在加载 Clone 模型: {CLONE_MODEL_PATH}")
            return Qwen3TTSModel.from_pretrained(
                str(CLONE_MODEL_PATH),
                device_map="cpu",
                dtype=torch.float32,
            )
        
        self.clone_model = global_model_manager.load_model(
            "clone_model", load_model
        )
        print("Clone 模型加载完成！")
        return self.clone_model

    @memory_monitor(max_memory_gb=4.0)
    def load_voice_design_model(self):
        """加载 VoiceDesign 模型（声音设计）"""
        def load_model():
            if not self.voice_design_model_available:
                raise FileNotFoundError(
                    f"声音设计模型不存在: {VOICE_DESIGN_MODEL_PATH}\n"
                    f"请先运行 download_voicedesign_model.py 下载 VoiceDesign 模型"
                )
            print(f"正在加载 VoiceDesign 模型: {VOICE_DESIGN_MODEL_PATH}")
            return Qwen3TTSModel.from_pretrained(
                str(VOICE_DESIGN_MODEL_PATH),
                device_map="cpu",
                dtype=torch.float32,
            )
        
        self.voice_design_model = global_model_manager.load_model(
            "voice_design_model", load_model
        )
        print("VoiceDesign 模型加载完成！")
        return self.voice_design_model

    @property
    def model(self):
        """默认返回 CustomVoice 模型"""
        return self.load_custom_model()

    def generate_custom_voice(self, text, speaker, language, instruct):
        """使用预置音色生成语音"""
        if not text or not text.strip():
            return None, "请输入要转换的文本"

        try:
            model = self.load_custom_model()
            
            # 使用局部音色优化器处理参数
            from voice_optimizer import create_voice_optimizer
            optimizer = create_voice_optimizer()
            optimized_params = optimizer.optimize_generation_params(
                text=text.strip(),
                speaker=speaker,
                language=language,
                instruct=instruct
            )
            
            wavs, sr = model.generate_custom_voice(
                text=optimized_params["text"],
                language=optimized_params["language"],
                speaker=optimized_params["speaker"],
                instruct=optimized_params["instruct"],
            )

            # 保存音频
            output_path = OUTPUT_DIR / f"{speaker}_{len(text)}.wav"
            sf.write(str(output_path), wavs[0], sr)

            status = f"生成成功！采样率: {sr}Hz"
            if "optimization_reason" in optimized_params:
                status += f" | {optimized_params['optimization_reason']}"
            
            return str(output_path), status

        except Exception as e:
            return None, f"生成失败: {str(e)}"

    def voice_clone(self, text, ref_audio, ref_text):
        """声音克隆 - 使用 Base 模型"""
        if not text or not text.strip():
            return None, "请输入要转换的文本"
        if ref_audio is None:
            return None, "请上传参考音频"
        if not ref_text or not ref_text.strip():
            return None, "请输入参考音频对应的文本"

        if not self.clone_model_available:
            return None, "克隆模型未安装，请先运行 download_clone_model.py"

        try:
            model = self.load_clone_model()
            
            # 克隆音色保持原始口音特色，不做标准化处理
            clone_text = text.strip()
            clone_ref_text = ref_text.strip()

            # 使用 Base 模型的 generate_voice_clone 方法
            wavs, sr = model.generate_voice_clone(
                text=clone_text,
                ref_audio=ref_audio,
                ref_text=clone_ref_text,
            )

            # 保存音频
            output_path = OUTPUT_DIR / f"clone_{len(text)}.wav"
            sf.write(str(output_path), wavs[0], sr)

            return str(output_path), f"克隆成功！采样率: {sr}Hz (已优化为标准普通话)"

        except Exception as e:
            return None, f"克隆失败: {str(e)}"

    def voice_clone_and_save(self, text, ref_audio, ref_text, save_name):
        """声音克隆并保存"""
        if not text or not text.strip():
            return None, "请输入要转换的文本", ""
        if ref_audio is None:
            return None, "请上传参考音频", ""
        if not ref_text or not ref_text.strip():
            return None, "请输入参考音频对应的文本", ""

        if not self.clone_model_available:
            return None, "克隆模型未安装，请先运行 download_clone_model.py", ""

        try:
            model = self.load_clone_model()
            
            # 克隆音色保持原始口音特色，不做标准化处理
            clone_text = text.strip()
            clone_ref_text = ref_text.strip()

            # 使用 Base 模型的 generate_voice_clone 方法
            wavs, sr = model.generate_voice_clone(
                text=clone_text,
                ref_audio=ref_audio,
                ref_text=clone_ref_text,
            )

            # 保存音频
            output_path = OUTPUT_DIR / f"clone_{len(text)}.wav"
            sf.write(str(output_path), wavs[0], sr)

            # 如果提供了保存名称，保存克隆音色
            save_info = ""
            if save_name and save_name.strip():
                clone_dir = save_clone_voice(save_name.strip(), ref_audio, clone_ref_text)
                save_info = f"音色已保存到: cloned_voices/{clone_dir.name} (保持原始口音特色)"

            return str(output_path), f"克隆成功！采样率: {sr}Hz (保持原始口音特色)", save_info

        except Exception as e:
            return None, f"克隆失败: {str(e)}", ""

    def voice_clone_with_saved(self, text, saved_clone_id):
        """使用保存的克隆音色生成语音"""
        if not text or not text.strip():
            return None, "请输入要转换的文本"

        if not saved_clone_id or saved_clone_id == "无保存的音色":
            return None, "请先保存或选择一个克隆音色"

        # 从下拉菜单选项中提取ID（格式：名称 (时间)|ID）
        if "|" in saved_clone_id:
            saved_clone_id = saved_clone_id.split("|")[-1].strip()

        if not self.clone_model_available:
            return None, "克隆模型未安装，请先运行 download_clone_model.py"

        try:
            # 加载保存的克隆音色
            ref_audio, ref_text = load_clone_voice(saved_clone_id)
            if ref_audio is None:
                return None, f"无法加载克隆音色: {saved_clone_id}"

            model = self.load_clone_model()

            # 使用 Base 模型的 generate_voice_clone 方法
            wavs, sr = model.generate_voice_clone(
                text=text.strip(),
                ref_audio=ref_audio,
                ref_text=ref_text,
            )

            # 保存音频
            output_path = OUTPUT_DIR / f"clone_saved_{len(text)}.wav"
            sf.write(str(output_path), wavs[0], sr)

            return str(output_path), f"生成成功！采样率: {sr}Hz"

        except Exception as e:
            return None, f"生成失败: {str(e)}"

    def voice_design(self, design_text, target_text, language):
        """声音设计 - 用文字描述生成声音"""
        if not design_text or not design_text.strip():
            return None, "请输入声音描述"
        if not target_text or not target_text.strip():
            return None, "请输入要生成的文本"

        if not self.voice_design_model_available:
            return None, "VoiceDesign 模型未安装，请先运行 download_voicedesign_model.py"

        try:
            model = self.load_voice_design_model()
            
            # 声音设计保持用户意图，不强制标准化
            design_target = target_text.strip()
            design_instruct = design_text.strip()

            # 生成设计的声音，支持用户自定义口音
            wavs, sr = model.generate_voice_design(
                text=design_target,
                language=language if language != "Auto" else "Chinese",
                instruct=design_instruct,
                do_sample=True,
            )

            # 保存音频
            output_path = OUTPUT_DIR / f"voice_design_{len(target_text)}.wav"
            sf.write(str(output_path), wavs[0], sr)

            return str(output_path), f"声音设计成功！采样率: {sr}Hz (已优化为标准普通话)"

        except Exception as e:
            return None, f"声音设计失败: {str(e)}"

    def voice_design_and_save(self, design_text, target_text, language, save_name):
        """声音设计并保存"""
        if not design_text or not design_text.strip():
            return None, "请输入声音描述", ""
        if not target_text or not target_text.strip():
            return None, "请输入要生成的文本", ""

        if not self.voice_design_model_available:
            return None, "VoiceDesign 模型未安装", ""

        try:
            model = self.load_voice_design_model()

            # 生成设计的声音
            wavs, sr = model.generate_voice_design(
                text=target_text.strip(),
                language=language,
                instruct=design_text.strip(),
                do_sample=True,
            )

            # 保存音频
            output_path = OUTPUT_DIR / f"voice_design_{len(target_text)}.wav"
            sf.write(str(output_path), wavs[0], sr)

            # 如果提供了保存名称，保存设计音色
            save_info = ""
            if save_name and save_name.strip():
                clone_dir = save_voice_design(save_name.strip(), design_text.strip(), target_text.strip(), output_path)
                save_info = f"音色已保存到: cloned_voices/{clone_dir.name}"

            return str(output_path), f"声音设计成功！采样率: {sr}Hz", save_info

        except Exception as e:
            return None, f"声音设计失败: {str(e)}", ""

    def voice_design_with_saved(self, text, saved_clone_id):
        """使用保存的设计音色生成语音"""
        if not text or not text.strip():
            return None, "请输入要转换的文本"

        if not saved_clone_id or saved_clone_id == "无保存的音色":
            return None, "请先保存或选择一个音色"

        # 从下拉菜单选项中提取ID（格式：名称 (时间)|ID）
        if "|" in saved_clone_id:
            saved_clone_id = saved_clone_id.split("|")[-1].strip()

        # 加载保存的音色
        clone_dir = CLONE_VOICES_DIR / saved_clone_id
        if not clone_dir.exists():
            return None, f"无法找到音色: {saved_clone_id}"

        meta_file = clone_dir / "meta.json"
        if not meta_file.exists():
            return None, f"音色元数据丢失: {saved_clone_id}"

        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        # 检查是否是设计音色（有 design_instruct 字段）
        design_instruct = meta.get('design_instruct', '')
        if design_instruct:
            # 使用 VoiceDesign 模型
            if not self.voice_design_model_available:
                return None, "VoiceDesign 模型未安装"

            try:
                model = self.load_voice_design_model()

                wavs, sr = model.generate_voice_design(
                    text=text.strip(),
                    language="Auto",
                    instruct=design_instruct,
                    do_sample=True,
                )

                output_path = OUTPUT_DIR / f"design_saved_{len(text)}.wav"
                sf.write(str(output_path), wavs[0], sr)

                return str(output_path), f"生成成功！采样率: {sr}Hz"

            except Exception as e:
                return None, f"生成失败: {str(e)}"
        else:
            # 使用 VoiceClone 模型（原有克隆音色）
            if not self.clone_model_available:
                return None, "克隆模型未安装"

            try:
                ref_audio, ref_text = load_clone_voice(saved_clone_id)
                if ref_audio is None:
                    return None, f"无法加载克隆音色: {saved_clone_id}"

                model = self.load_clone_model()

                wavs, sr = model.generate_voice_clone(
                    text=text.strip(),
                    ref_audio=ref_audio,
                    ref_text=ref_text,
                )

                output_path = OUTPUT_DIR / f"clone_saved_{len(text)}.wav"
                sf.write(str(output_path), wavs[0], sr)

                return str(output_path), f"生成成功！采样率: {sr}Hz"

            except Exception as e:
                return None, f"生成失败: {str(e)}"


def create_ui():
    """创建 Gradio 界面"""
    tts = Qwen3TTSWebUI()

    # 模型状态显示
    model_status = f"""
    <div style="padding: 15px; border-radius: 8px; margin-bottom: 15px; font-size: 14px;">
        <strong>📦 模型状态</strong><br>
        ✅ CustomVoice (预置音色) - 已安装<br>
        {"✅ Base (声音克隆) - 已安装" if tts.clone_model_available else "⬇️ Base (声音克隆) - 未安装，运行 download_clone_model.py"}<br>
        {"✅ VoiceDesign (声音设计) - 已安装" if tts.voice_design_model_available else "⬇️ VoiceDesign (声音设计) - 未安装，运行 download_voicedesign_model.py"}
    </div>
    """

    with gr.Blocks(title="千问语音克隆 - Qwen3-TTS") as app:
        # 标题
        gr.HTML("""
        <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; margin-bottom: 25px;">
            <h1 style="margin: 0;">🎙️ 千问语音克隆 - Qwen3-TTS</h1>
            <p style="margin: 10px 0 0 0;">支持中英日韩等10种语言 | 9种预置音色 | 声音克隆 | 声音设计</p>
        </div>
        """)

        gr.HTML(model_status)

        with gr.Tabs():
            # Tab 1: 预置音色生成
            with gr.Tab("🎭 预置音色"):
                with gr.Row():
                    with gr.Column(scale=2):
                        text_input = gr.Textbox(
                            label="输入文本",
                            placeholder="请输入要转换为语音的文本...",
                            lines=5,
                        )

                        with gr.Row():
                            speaker_dropdown = gr.Dropdown(
                                choices=list(SPEAKERS.keys()),
                                value="vivian",
                                label="选择音色",
                            )
                            language_dropdown = gr.Dropdown(
                                choices=LANGUAGES,
                                value="Auto",
                                label="语言",
                            )

                        instruct_input = gr.Textbox(
                            label="风格指令 (可选)",
                            placeholder="例如: 愉快地、悲伤地、激动地...",
                            lines=2,
                        )

                        generate_btn = gr.Button("🎵 生成语音", variant="primary", size="lg")

                    with gr.Column(scale=1):
                        output_audio = gr.Audio(label="生成的音频")
                        status_text = gr.Textbox(label="状态", interactive=False)

                        # 音色说明
                        gr.Markdown("### 📋 音色说明")
                        speaker_info = "\n".join([f"**{k}**: {v}" for k, v in SPEAKERS.items()])
                        gr.Markdown(speaker_info)

                generate_btn.click(
                    fn=tts.generate_custom_voice,
                    inputs=[text_input, speaker_dropdown, language_dropdown, instruct_input],
                    outputs=[output_audio, status_text],
                )

                # 示例
                gr.Examples(
                    examples=[
                        ["你好，我是千问语音合成模型。", "vivian", "Chinese", ""],
                        ["Hello, this is a text-to-speech demo.", "aiden", "English", ""],
                        ["こんにちは、これは音声合成のデモです。", "serena", "Japanese", ""],
                        ["안녕하세요, 이것은 음성 합성 데모입니다.", "dylan", "Korean", ""],
                    ],
                    inputs=[text_input, speaker_dropdown, language_dropdown, instruct_input],
                )

            # Tab 2: 声音设计
            with gr.Tab("🎨 声音设计"):
                design_status = gr.HTML(f"""
                <div style="padding: 15px; background: {'#d4edda' if tts.voice_design_model_available else '#fff3cd'}; border-radius: 8px; margin-bottom: 15px;">
                    <strong>{'✅ VoiceDesign 模型已安装' if tts.voice_design_model_available else '⚠️ VoiceDesign 模型未安装'}</strong><br>
                    {'' if tts.voice_design_model_available else '请运行: <code>python download_voicedesign_model.py</code>'}
                </div>
                """)

                with gr.Row():
                    with gr.Column(scale=2):
                        design_input = gr.Textbox(
                            label="声音描述",
                            placeholder="例如: Male, 25 years old, confident, deep voice, news anchor style",
                            lines=4,
                        )

                        design_target_input = gr.Textbox(
                            label="要生成的文本",
                            placeholder="请输入要用这个声音说的话...",
                            lines=3,
                        )

                        design_language_dropdown = gr.Dropdown(
                            choices=LANGUAGES,
                            value="Auto",
                            label="语言",
                        )

                        with gr.Row():
                            design_save_name_input = gr.Textbox(
                                label="保存音色名称 (可选)",
                                placeholder="例如: 深沉男声、活泼女声...",
                                scale=3,
                            )
                            design_btn = gr.Button("🎨 设计声音并生成", variant="primary", size="lg", scale=1)

                        design_save_info_text = gr.Textbox(label="保存状态", interactive=False, lines=1)

                        gr.Markdown("""
                        ### 💡 描述词示例
                        - `Male, 25 years old, confident, deep voice, news anchor` - 自信男主播
                        - `Female, 20 years old, cheerful, friendly, customer service` - 活泼女客服
                        - `Male, 50 years old, calm, authoritative, documentary narrator` - 纪录片解说
                        - `Female, child, 8 years old, cute, high-pitched, energetic` - 可爱女童
                        """)

                    with gr.Column(scale=1):
                        design_output_audio = gr.Audio(label="设计后的声音")
                        design_status_text = gr.Textbox(label="生成状态", interactive=False)

                design_btn.click(
                    fn=tts.voice_design_and_save,
                    inputs=[design_input, design_target_input, design_language_dropdown, design_save_name_input],
                    outputs=[design_output_audio, design_status_text, design_save_info_text],
                )

                # 分隔线
                gr.Markdown("---")

                # 使用保存的音色（与声音克隆标签页相同）
                gr.Markdown("### 🎯 我的克隆音色")

                with gr.Row():
                    with gr.Column(scale=2):
                        design_saved_text_input = gr.Textbox(
                            label="输入要转换的文本",
                            placeholder="请输入要转换为语音的文本...",
                            lines=3,
                        )

                        with gr.Row():
                            design_saved_dropdown = gr.Dropdown(
                                choices=get_clone_choices(),
                                label="选择保存的音色",
                                value=get_clone_choices()[0] if get_clone_choices() else None,
                                allow_custom_value=False,
                                scale=2,
                            )
                            design_refresh_clones_btn = gr.Button("🔄 刷新列表", size="sm", scale=0)

                        design_use_saved_btn = gr.Button("🎵 使用保存的音色生成", variant="primary", size="lg")

                    with gr.Column(scale=1):
                        design_saved_output_audio = gr.Audio(label="生成的音频")
                        design_saved_status_text = gr.Textbox(label="状态", interactive=False)

                        # 删除克隆音色
                        design_delete_input = gr.Textbox(
                            label="要删除的音色ID",
                            placeholder="从下方列表复制ID...",
                            lines=1,
                        )
                        design_delete_btn = gr.Button("🗑️ 删除克隆音色", variant="stop")

                        gr.Markdown("""
                        ### 📋 已保存的音色列表
                        """)
                        design_clones_list = gr.Markdown(get_clones_list_markdown())

                design_refresh_clones_btn.click(
                    fn=lambda: gr.Dropdown(choices=get_clone_choices(), value=get_clone_choices()[0] if get_clone_choices() else None),
                    outputs=[design_saved_dropdown],
                )

                design_use_saved_btn.click(
                    fn=tts.voice_design_with_saved,
                    inputs=[design_saved_text_input, design_saved_dropdown],
                    outputs=[design_saved_output_audio, design_saved_status_text],
                )

                def design_delete_clone(clone_id):
                    if not clone_id or clone_id.strip() == "":
                        return "请输入要删除的音色ID", get_clones_list_markdown()
                    if delete_clone_voice(clone_id.strip()):
                        return f"已删除: {clone_id.strip()}", get_clones_list_markdown()
                    return f"删除失败: {clone_id.strip()}", get_clones_list_markdown()

                design_delete_btn.click(
                    fn=design_delete_clone,
                    inputs=[design_delete_input],
                    outputs=[design_saved_status_text, design_clones_list],
                )

            # Tab 3: 声音克隆
            with gr.Tab("🎤 声音克隆"):
                clone_status_info = gr.HTML(f"""
                <div style="padding: 15px; background: {'#d4edda' if tts.clone_model_available else '#fff3cd'}; border-radius: 8px; margin-bottom: 15px;">
                    <strong>{'✅ Base 模型已安装' if tts.clone_model_available else '⚠️ Base 模型未安装'}</strong><br>
                    {'声音克隆功能可用' if tts.clone_model_available else '请运行: <code>python download_clone_model.py</code>'}
                </div>
                """)

                with gr.Row():
                    with gr.Column(scale=2):
                        clone_text_input = gr.Textbox(
                            label="输入要转换的文本",
                            placeholder="请输入要转换为语音的文本...",
                            lines=3,
                        )

                        gr.Markdown("### 📁 参考音频")
                        ref_audio_input = gr.Audio(
                            label="上传参考音频 (WAV/MP3)",
                            type="filepath",
                        )
                        ref_text_input = gr.Textbox(
                            label="参考音频对应的文本",
                            placeholder="请输入参考音频中说的内容...",
                            lines=2,
                        )

                        with gr.Row():
                            save_name_input = gr.Textbox(
                                label="保存音色名称 (可选)",
                                placeholder="例如: 我的声音、小明声音...",
                                scale=3,
                            )
                            clone_btn = gr.Button("🎵 克隆语音", variant="primary", size="lg", scale=1)

                        save_info_text = gr.Textbox(label="保存状态", interactive=False, lines=1)

                    with gr.Column(scale=1):
                        clone_output_audio = gr.Audio(label="克隆后的音频")
                        clone_status_text = gr.Textbox(label="生成状态", interactive=False)

                        gr.Markdown("""
                        ### 💡 使用说明
                        1. 上传一段3-10秒的参考音频
                        2. 输入参考音频中说的文本
                        3. 输入要转换的新文本
                        4. (可选) 输入保存名称以便下次使用
                        5. 点击生成
                        """)

                clone_btn.click(
                    fn=tts.voice_clone_and_save,
                    inputs=[clone_text_input, ref_audio_input, ref_text_input, save_name_input],
                    outputs=[clone_output_audio, clone_status_text, save_info_text],
                )

                # 分隔线
                gr.Markdown("---")

                # 使用保存的克隆音色
                gr.Markdown("### 🎯 我的克隆音色")

                with gr.Row():
                    with gr.Column(scale=2):
                        saved_clone_text_input = gr.Textbox(
                            label="输入要转换的文本",
                            placeholder="请输入要转换为语音的文本...",
                            lines=3,
                        )

                        with gr.Row():
                            saved_clone_dropdown = gr.Dropdown(
                                choices=get_clone_choices(),
                                label="选择保存的音色",
                                value=get_clone_choices()[0] if get_clone_choices() else None,
                                allow_custom_value=False,
                                scale=2,
                            )
                            refresh_clones_btn = gr.Button("🔄 刷新列表", size="sm", scale=0)

                        use_saved_clone_btn = gr.Button("🎵 使用保存的音色生成", variant="primary", size="lg")

                    with gr.Column(scale=1):
                        saved_clone_output_audio = gr.Audio(label="生成的音频")
                        saved_clone_status_text = gr.Textbox(label="状态", interactive=False)

                        # 删除克隆音色
                        delete_clone_input = gr.Textbox(
                            label="要删除的音色ID",
                            placeholder="从下方列表复制ID...",
                            lines=1,
                        )
                        delete_clone_btn = gr.Button("🗑️ 删除克隆音色", variant="stop")

                        gr.Markdown("""
                        ### 📋 已保存的音色列表
                        """)
                        clones_list = gr.Markdown(get_clones_list_markdown())

                refresh_clones_btn.click(
                    fn=lambda: gr.Dropdown(choices=get_clone_choices(), value=get_clone_choices()[0] if get_clone_choices() else None),
                    outputs=[saved_clone_dropdown],
                )

                use_saved_clone_btn.click(
                    fn=tts.voice_clone_with_saved,
                    inputs=[saved_clone_text_input, saved_clone_dropdown],
                    outputs=[saved_clone_output_audio, saved_clone_status_text],
                )

                def delete_clone(clone_id):
                    if not clone_id or clone_id.strip() == "":
                        return "请输入要删除的音色ID", get_clones_list_markdown()
                    if delete_clone_voice(clone_id.strip()):
                        return f"已删除: {clone_id.strip()}", get_clones_list_markdown()
                    return f"删除失败: {clone_id.strip()}", get_clones_list_markdown()

                delete_clone_btn.click(
                    fn=delete_clone,
                    inputs=[delete_clone_input],
                    outputs=[saved_clone_status_text, clones_list],
                )

            # Tab 4: 批量生成
            with gr.Tab("📝 批量生成"):
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("""
                        ### 📄 文本导入
                        支持导入长文本文件（小说、文章等），自动按段落分割处理。
                        """)

                        with gr.Row():
                            batch_file_input = gr.File(
                                label="上传文本文件 (.txt)",
                                file_types=[".txt"],
                                type="filepath",
                            )
                            import_file_btn = gr.Button("📥 导入文件", size="sm")

                        batch_text_input = gr.Textbox(
                            label="文本内容（也可直接输入或粘贴）",
                            placeholder="第一句话\n第二句话\n第三句话...\n\n或使用上方导入按钮加载文件...",
                            lines=10,
                        )

                        gr.Markdown("""
                        ### ⚙️ 生成设置
                        """)

                        with gr.Row():
                            batch_speaker = gr.Dropdown(
                                choices=get_all_speaker_choices(),
                                value="🎭 vivian (女声-年轻-可爱-亲切)|preset_vivian",
                                label="选择音色",
                            )
                            batch_refresh_speakers = gr.Button("🔄 刷新", size="sm")
                            batch_language = gr.Dropdown(
                                choices=LANGUAGES,
                                value="Chinese",
                                label="语言",
                            )

                        with gr.Row():
                            batch_format = gr.Dropdown(
                                choices=["wav", "opus"],
                                value="wav",
                                label="输出格式",
                            )
                            batch_book_name = gr.Textbox(
                                label="作品名称（用于文件命名，可选）",
                                placeholder="如：三体、红楼梦...",
                                lines=1,
                            )

                        batch_generate_btn = gr.Button("🎵 批量生成", variant="primary", size="lg")

                        gr.Markdown("""
                        ---
                        ### 💡 使用提示
                        - **长文本处理**：建议按章节分别处理（每章一个txt文件）
                        - **输出格式**：WAV 最佳质量但文件大，MP3/M4A 适合分享，FLAC 无损压缩
                        - **作品名称**：用作文件前缀，如「第1章_001.wav」
                        """)

                    with gr.Column(scale=1):
                        batch_output_audio = gr.Audio(label="生成的音频")
                        batch_status = gr.Textbox(label="状态", interactive=False, lines=2)
                        batch_progress = gr.Textbox(label="生成进度", interactive=False, lines=3)
                        batch_files = gr.Textbox(label="生成的文件列表", interactive=False, lines=8)

                # 文件导入函数
                def import_text_file(file_path):
                    if file_path is None:
                        return "请先选择文件", ""
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # 限制最大字符数（防止浏览器卡顿）
                        if len(content) > 500000:  # 约50万字符
                            return f"文件过长（{len(content)}字符），请分段处理（建议每章10万字以内）", ""
                        return f"成功导入 {len(content)} 字符", content
                    except Exception as e:
                        return f"导入失败: {str(e)}", ""

                import_file_btn.click(
                    fn=import_text_file,
                    inputs=[batch_file_input],
                    outputs=[batch_status, batch_text_input],
                )

                @memory_monitor(max_memory_gb=6.0)
                def batch_generate(text, speaker, language, output_format, book_name):
                    # 初始化音色优化器
                    optimizer = create_voice_optimizer()
                    if not text or not text.strip():
                        return None, "请输入文本", "", ""

                    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
                    if not lines:
                        return None, "没有有效的文本", "", ""
                    
                    # 限制批量生成数量防止内存溢出
                    if len(lines) > 200:
                        return None, f"文本行数过多({len(lines)}行)，请分批处理（建议每批不超过100行）", "", ""

                    # 解析音色选择（格式：🎭 名称 (描述)|preset_name 或 🎤 名称|clone_id）
                    speaker_id = speaker.split("|")[-1].strip() if "|" in speaker else speaker
                    is_preset = speaker_id.startswith("preset_")

                    # 解析音色名称（用于文件命名）
                    if is_preset:
                        speaker_name = speaker_id.replace("preset_", "")
                    else:
                        speaker_name = "clone"

                    # 准备文件命名前缀
                    name_prefix = book_name.strip() if book_name and book_name.strip() else speaker_name

                    outputs = []
                    sr = None
                    progress_text = ""

                    try:
                        # 分批处理，每50个音频清理一次内存
                        batch_size = 50
                        for batch_start in range(0, len(lines), batch_size):
                            batch_end = min(batch_start + batch_size, len(lines))
                            batch_lines = lines[batch_start:batch_end]
                            
                            # 每批重新加载模型（确保内存清理）
                            model = None
                            current_ref_audio = None
                            current_ref_text = None
                            
                            if is_preset:
                                model = tts.load_custom_model()
                            else:
                                if not tts.clone_model_available:
                                    return None, "克隆模型未安装，无法使用克隆音色", "", ""
                                current_ref_audio, current_ref_text = load_clone_voice(speaker_id)
                                if current_ref_audio is None:
                                    return None, f"无法加载克隆音色: {speaker_id}", "", ""
                                model = tts.load_clone_model()

                            # 处理当前批次
                            for i, line in enumerate(batch_lines):
                                global_i = batch_start + i
                                progress_text = f"正在生成: {global_i+1}/{len(lines)}"

                                if is_preset:
                                    # 使用优化后的预置音色生成
                                    optimized_params = optimizer.optimize_generation_params(
                                        text=line,
                                        speaker=speaker_name,
                                        language=language,
                                        instruct=None
                                    )
                                    wavs, sample_rate = model.generate_custom_voice(
                                        text=optimized_params["text"],
                                        language=optimized_params["language"],
                                        speaker=optimized_params["speaker"],
                                        instruct=optimized_params["instruct"],
                                    )
                                    output_name = f"{name_prefix}_{global_i+1:03d}"
                                else:
                                    # 克隆音色保持原始口音特色
                                    wavs, sample_rate = model.generate_voice_clone(
                                        text=line,
                                        ref_audio=current_ref_audio,
                                        ref_text=current_ref_text,
                                    )
                                    output_name = f"{name_prefix}_clone_{global_i+1:03d}"

                                if sr is None:
                                    sr = sample_rate

                                # 立即保存音频文件
                                wav_path = OUTPUT_DIR / f"{output_name}.wav"
                                sf.write(str(wav_path), wavs[0], sample_rate)

                                if output_format == "wav":
                                    outputs.append(str(wav_path))
                                else:  # opus
                                    opus_path = OUTPUT_DIR / f"{output_name}.opus"
                                    audio = AudioSegment.from_wav(str(wav_path))
                                    audio.export(str(opus_path), format="opus", bitrate="64k")
                                    outputs.append(str(opus_path))
                                    wav_path.unlink()  # 删除临时WAV

                                # 每生成10个音频清理一次临时变量
                                if global_i % 10 == 0:
                                    del wavs, sample_rate
                                    global_memory_manager.force_garbage_collection()

                            # 批次结束，清理模型和内存
                            if not is_preset:
                                del current_ref_audio, current_ref_text
                            del model
                            global_memory_manager.force_garbage_collection()

                        # 合并音频（使用更安全的方式）
                        combined_status = ""
                        if len(outputs) > 1:
                            try:
                                # 分小段合并，避免内存占用过大
                                combined_audio = AudioSegment.from_wav(outputs[0]) if output_format == "wav" else AudioSegment.from_file(outputs[0])
                                
                                for output_path in outputs[1:]:
                                    segment = AudioSegment.from_wav(output_path) if output_format == "wav" else AudioSegment.from_file(output_path)
                                    combined_audio += segment
                                    
                                    # 每合并10个文件清理一次
                                    if len(outputs) % 10 == 0:
                                        del segment
                                        global_memory_manager.force_garbage_collection()

                                # 导出合并文件
                                if output_format == "wav":
                                    combined_path = OUTPUT_DIR / f"{name_prefix}_combined.wav"
                                    combined_audio.export(str(combined_path), format="wav")
                                else:  # opus
                                    combined_path = OUTPUT_DIR / f"{name_prefix}_combined.opus"
                                    combined_audio.export(str(combined_path), format="opus", bitrate="64k")

                                combined_status = f"\n✅ 合并音频: {combined_path}"
                                del combined_audio
                            except Exception as e:
                                combined_status = f"\n❌ 合并失败: {str(e)}"
                                combined_path = None
                        else:
                            # 只有一个音频时，直接使用该音频路径
                            combined_path = outputs[0] if outputs else None

                        files_text = "\n".join(outputs)
                        status = f"✅ 成功生成 {len(lines)} 个音频 | 格式: {output_format.upper()}"
                        if len(lines) > 50:
                            status += f" | 已分批处理"

                        # 最终清理
                        global_memory_manager.force_garbage_collection()
                        # 返回合并音频路径（或单个音频路径）用于显示
                        return str(combined_path) if combined_path else None, status, progress_text, files_text + combined_status

                    except Exception as e:
                        global_memory_manager.force_garbage_collection()
                        return None, f"批量生成失败: {str(e)}", "", ""

                batch_generate_btn.click(
                    fn=batch_generate,
                    inputs=[batch_text_input, batch_speaker, batch_language, batch_format, batch_book_name],
                    outputs=[batch_output_audio, batch_status, batch_progress, batch_files],
                )

                # 刷新音色列表按钮
                batch_refresh_speakers.click(
                    fn=lambda: gr.Dropdown(choices=get_all_speaker_choices()),
                    outputs=[batch_speaker],
                )

        # 页脚
        gr.HTML("""
        <div style="text-align: center; padding: 20px; color: #666;">
            <p>Powered by <a href="https://github.com/QwenLM/Qwen3-TTS" target="_blank">Qwen3-TTS</a>
            | Models: <strong>CustomVoice + VoiceDesign</strong> + Base (可选)</p>
        </div>
        """)

    return app


if __name__ == "__main__":
    import argparse
    import atexit
    from memory_manager import cleanup_memory

    # 注册退出清理函数
    atexit.register(cleanup_memory)

    parser = argparse.ArgumentParser(description="千问语音克隆 - Qwen3-TTS WebUI")
    parser.add_argument("--share", action="store_true", help="创建公网分享链接")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, default=7860, help="服务器端口")
    args = parser.parse_args()

    try:
        app = create_ui()
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            inbrowser=True,
        )
    except KeyboardInterrupt:
        print("\n正在清理内存...")
        cleanup_memory()
        print("清理完成，程序退出")
    except Exception as e:
        print(f"程序异常: {e}")
        cleanup_memory()
        raise
