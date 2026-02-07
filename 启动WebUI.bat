@echo off
chcp 65001 >nul
title 千问语音克隆 - Qwen3-TTS WebUI

echo.
echo ============================================
echo    千问语音克隆 - Qwen3-TTS WebUI
echo ============================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/4] 检查 Python 环境... OK
echo.

REM 检查虚拟环境
if exist "venv\" (
    echo [2/4] 虚拟环境已存在，跳过创建
) else (
    echo [2/4] 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [2/4] 虚拟环境创建完成
)
echo.

REM 检查依赖
echo [3/4] 正在检查/安装依赖包...
venv\Scripts\pip install -q -r requirements.txt
if errorlevel 1 (
    echo [警告] 部分依赖安装失败，尝试继续...
)
echo [3/4] 依赖包检查完成
echo.

REM 显示模型状态
echo [4/4] 模型状态检查...
if exist "models\model.safetensors" (
    echo   ✅ CustomVoice 预置音色模型 - 已安装
) else (
    echo   ❌ CustomVoice 模型 - 未找到
)
if exist "models-base\model.safetensors" (
    echo   ✅ Base 声音克隆模型 - 已安装
) else (
    echo   ⬇️ Base 声音克隆模型 - 未安装
)
if exist "models-voicedesign\model.safetensors" (
    echo   ✅ VoiceDesign 声音设计模型 - 已安装
) else (
    echo   ⬇️ VoiceDesign 声音设计模型 - 未安装
)
echo.

REM 取消代理设置（避免 Gradio 启动问题）
set http_proxy=
set https_proxy=
set HTTP_PROXY=
set HTTPS_PROXY=
set all_proxy=
set ALL_PROXY=
set socks_proxy=
set SOCKS_PROXY=
set ftp_proxy=
set FTP_PROXY=
set no_proxy=
set NO_PROXY=

REM 启动 WebUI
echo 正在启动 WebUI 界面...
echo.
echo ============================================
echo  WebUI 界面将在浏览器中自动打开
echo  访问地址: http://localhost:7860
echo  按 Ctrl+C 停止服务
echo ============================================
echo.

venv\Scripts\python webui.py --host 0.0.0.0 --port 7860

pause
