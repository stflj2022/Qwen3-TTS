#!/usr/bin/env python3
"""
下载 Qwen3-TTS VoiceDesign 模型（声音设计）- 使用代理
"""
import os

# 使用代理（Clash 全局模式）
os.environ["http_proxy"] = "http://127.0.0.1:7897"
os.environ["https_proxy"] = "http://127.0.0.1:7897"

from huggingface_hub import snapshot_download

MODEL_NAME = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
CACHE_DIR = os.path.expanduser("~/qwen3-tts/models-voicedesign")

print(f"正在下载 VoiceDesign 模型 (使用代理): {MODEL_NAME}")
print(f"目标目录: {CACHE_DIR}")
print("=" * 60)

os.makedirs(CACHE_DIR, exist_ok=True)

snapshot_download(
    repo_id=MODEL_NAME,
    local_dir=CACHE_DIR,
    resume_download=True,
)

print("=" * 60)
print(f"模型下载完成! 已保存到: {CACHE_DIR}")
