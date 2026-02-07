#!/usr/bin/env python3
"""
Qwen3-TTS 1.7B-CustomVoice 部署脚本
支持自定义音色生成、语音克隆和语音设计
"""
import os
import sys
import torch
import soundfile as sf
import argparse
from pathlib import Path

# 添加当前目录到路径以使用本地模型
sys.path.insert(0, str(Path(__file__).parent))

from qwen_tts import Qwen3TTSModel

# 模型路径
MODEL_PATH = os.path.expanduser("~/qwen3-tts/models")


def generate_custom_voice(
    text: str,
    language: str = "Auto",
    speaker: str = "vivian",
    instruct: str = None,
    output_file: str = "output.wav"
):
    """
    使用预置音色生成语音

    Args:
        text: 要转换的文本
        language: 语言 (Auto/Chinese/English/Japanese/Korean/German/French/Russian/Portuguese/Spanish/Italian)
        speaker: 预置音色 (9种可选: aiden, dylan, eric, ono_anna, ryan, serena, sohee, uncle_fu, vivian)
        instruct: 额外的语音风格指令
        output_file: 输出音频文件路径
    """
    print(f"加载模型: {MODEL_PATH}")
    print("-" * 50)

    model = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map="cpu",  # 使用 CPU，如需 GPU 请改为 "cuda:0"
        dtype=torch.float32,  # CPU 使用 float32
    )

    print(f"生成语音: {text}")
    print(f"语言: {language}")
    print(f"音色: {speaker}")
    if instruct:
        print(f"指令: {instruct}")
    print("-" * 50)

    wavs, sr = model.generate_custom_voice(
        text=text,
        language=language,
        speaker=speaker,
        instruct=instruct,
    )

    sf.write(output_file, wavs[0], sr)
    print(f"音频已保存: {output_file}")
    return output_file


def voice_clone(
    text: str,
    ref_audio: str,
    ref_text: str,
    output_file: str = "output_clone.wav"
):
    """
    声音克隆：使用参考音频克隆声音

    Args:
        text: 要转换的文本
        ref_audio: 参考音频文件路径
        ref_text: 参考音频对应的文本
        output_file: 输出音频文件路径
    """
    print(f"加载模型: {MODEL_PATH}")
    print("-" * 50)

    model = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map="cpu",
        dtype=torch.float32,
    )

    print(f"创建声音克隆提示...")
    print(f"参考文本: {ref_text}")

    voice_clone_prompt = model.create_voice_clone_prompt(
        ref_audio=ref_audio,
        ref_text=ref_text,
    )

    print(f"生成语音: {text}")
    print("-" * 50)

    wavs, sr = model.generate_custom_voice(
        text=text,
        voice_clone_prompt=voice_clone_prompt,
    )

    sf.write(output_file, wavs[0], sr)
    print(f"克隆音频已保存: {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS 1.7B-CustomVoice 部署脚本")
    subparsers = parser.add_subparsers(dest="mode", help="运行模式")

    # 自定义音色模式
    custom_parser = subparsers.add_parser("custom", help="使用预置音色生成语音")
    custom_parser.add_argument("--text", required=True, help="要转换的文本")
    custom_parser.add_argument("--language", default="Auto", help="语言")
    custom_parser.add_argument("--speaker", default="vivian",
                              help="预置音色 (aiden/dylan/eric/ono_anna/ryan/serena/sohee/uncle_fu/vivian)")
    custom_parser.add_argument("--instruct", help="额外的语音风格指令")
    custom_parser.add_argument("--output", default="output.wav", help="输出文件路径")

    # 声音克隆模式
    clone_parser = subparsers.add_parser("clone", help="声音克隆")
    clone_parser.add_argument("--text", required=True, help="要转换的文本")
    clone_parser.add_argument("--ref-audio", required=True, help="参考音频文件")
    clone_parser.add_argument("--ref-text", required=True, help="参考音频对应的文本")
    clone_parser.add_argument("--output", default="output_clone.wav", help="输出文件路径")

    args = parser.parse_args()

    if args.mode == "custom":
        generate_custom_voice(
            text=args.text,
            language=args.language,
            speaker=args.speaker,
            instruct=args.instruct,
            output_file=args.output,
        )
    elif args.mode == "clone":
        voice_clone(
            text=args.text,
            ref_audio=args.ref_audio,
            ref_text=args.ref_text,
            output_file=args.output,
        )
    else:
        # 默认演示模式
        print("=" * 50)
        print("Qwen3-TTS 1.7B-CustomVoice 演示")
        print("=" * 50)
        print("\n支持的预置音色 (speaker):")
        print("  - vivian      (女声-年轻-可爱-亲切)")
        print("  - serena      (女声-年轻-中性)")
        print("  - ono_anna    (女声-成熟-温柔)")
        print("  - aiden       (男声-年轻-自然)")
        print("  - dylan       (男声-成熟-自然)")
        print("  - ryan        (男声-成熟-旁白)")
        print("  - uncle_fu    (男声-成熟-深沉)")
        print("  - eric        (男童-可爱)")
        print("  - sohee       (女童-可爱)")
        print("\n示例命令:")
        print("  python run_tts.py custom --text '你好，世界！' --speaker vivian")
        print("\n或直接运行演示:")
        generate_custom_voice(
            text="Hello, this is Qwen3-TTS, a powerful text-to-speech model. 你好，这是Qwen3-TTS语音合成模型。",
            language="Auto",
            speaker="vivian",
            output_file="demo.wav",
        )


if __name__ == "__main__":
    main()
