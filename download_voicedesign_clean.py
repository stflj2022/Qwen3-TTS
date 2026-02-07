import os
from huggingface_hub import snapshot_download

# 使用 HTTP 代理
os.environ['http_proxy'] = 'http://127.0.0.1:7890'
os.environ['https_proxy'] = 'http://127.0.0.1:7890'

MODEL_NAME = 'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign'
CACHE_DIR = os.path.expanduser('~/qwen3-tts/models-voicedesign')

print(f"正在下载 VoiceDesign 模型: {MODEL_NAME}")
print(f"目标目录: {CACHE_DIR}")
print("=" * 60)

snapshot_download(
    repo_id=MODEL_NAME,
    local_dir=CACHE_DIR,
    resume_download=True,
)

print("=" * 60)
print(f"模型下载完成!")
