#!/bin/bash

# 千问语音克隆 - Qwen3-TTS WebUI 启动脚本 (Linux/Mac)

echo ""
echo "============================================"
echo "   千问语音克隆 - Qwen3-TTS WebUI"
echo "============================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.10+"
    echo "Ubuntu/Debian: sudo apt install python3 python3-venv"
    echo "CentOS/RHEL: sudo yum install python3"
    echo "macOS: brew install python3"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "[1/4] 检测到 Python 版本: $PYTHON_VERSION"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ -d "venv" ]; then
    echo "[2/4] 虚拟环境已存在"
else
    echo "[2/4] 正在创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 虚拟环境创建失败，请确保安装了 python3-venv"
        echo "Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
    echo "[2/4] 虚拟环境创建完成"
fi
echo ""

# 安装依赖
echo "[3/4] 正在检查/安装依赖包..."
source venv/bin/activate
pip install -q -r requirements.txt

# 安装内存管理依赖和音色优化依赖
echo "正在安装内存监控和音色优化依赖..."
pip install -q psutil memory-profiler

echo "[3/4] 依赖包检查完成"
echo ""

# 显示模型状态
echo "[4/4] 模型状态检查..."
if [ -f "models/model.safetensors" ]; then
    echo "   ✅ CustomVoice 预置音色模型 - 已安装"
else
    echo "   ❌ CustomVoice 模型 - 未找到"
fi
if [ -f "models-base/model.safetensors" ]; then
    echo "   ✅ Base 声音克隆模型 - 已安装"
else
    echo "   ⬇️ Base 声音克隆模型 - 未安装"
fi
if [ -f "models-voicedesign/model.safetensors" ]; then
    echo "   ✅ VoiceDesign 声音设计模型 - 已安装"
else
    echo "   ⬇️ VoiceDesign 声音设计模型 - 未安装"
fi
echo ""

# 取消代理设置（避免 Gradio/httpx 启动问题）
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY 2>/dev/null
unset socks_proxy SOCKS_PROXY all_proxy ALL_PROXY 2>/dev/null
unset ftp_proxy FTP_PROXY 2>/dev/null
unset no_proxy NO_PROXY 2>/dev/null

# 启动 WebUI
echo "正在启动 WebUI 界面..."
echo ""
echo "============================================"
echo " WebUI 界面将在浏览器中自动打开"
echo " 访问地址: http://localhost:7860"
echo " 按 Ctrl+C 停止服务"
echo "============================================"
echo ""

# 使用虚拟环境的Python启动应用
source venv/bin/activate
python webui.py --host 0.0.0.0 --port 7860
