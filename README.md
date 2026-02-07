# 千问语音克隆 - Qwen3-TTS

> 基于 Alibaba Qwen3-TTS 的语音合成与克隆工具，支持中英日韩等 10 种语言

![Version](https://img.shields.io/badge/版本-1.0-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![Platform](https://img.shields.io/badge/平台-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

---

## 功能特性

| 功能 | 说明 | 模型 |
|------|------|------|
| 🎭 **预置音色** | 9 种高质量预置音色（男/女/老/幼） | CustomVoice (内置) |
| 🎤 **声音克隆** | 3 秒音频快速克隆任意声音 | Base (需额外下载) |
| 🌍 **多语言** | 支持中英日韩德法俄葡西意 10 种语言 | 全部支持 |
| 📝 **批量生成** | 一键批量处理多段文本 | - |
| 🖥️ **Web 界面** | 图形化界面，简单易用 | - |
| 💻 **命令行** | 支持命令行调用 | - |

## 快速开始

### Windows 用户

1. **双击运行** `启动WebUI.bat`
2. 等待自动安装依赖（首次运行较慢）
3. 浏览器会自动打开 http://localhost:7860

### Linux / macOS 用户

```bash
# 添加执行权限并运行
chmod +x 启动WebUI.sh
./启动WebUI.sh
```

---

## 系统要求

| 要求 | 说明 |
|------|------|
| **Python** | 3.10 或更高版本 |
| **内存** | 建议 8GB 以上 |
| **硬盘** | 约 5GB（含模型） |
| **系统** | Windows / Linux / macOS |

### 安装 Python

- **Windows**: https://www.python.org/downloads/ （安装时勾选 "Add Python to PATH"）
- **Ubuntu/Debian**: `sudo apt install python3 python3-venv`
- **macOS**: `brew install python3`

---

## 使用说明

### WebUI 界面

启动后访问 **http://localhost:7860**，包含三个功能页面：

#### 1. 预置音色
- 输入文本
- 选择 9 种预置音色之一
- 点击生成

#### 2. 声音克隆（需要额外模型）

**⚠️ 声音克隆功能需要额外的 Base 模型**

首次使用声音克隆前，需要下载 Base 模型：

```bash
# 激活虚拟环境后运行
python download_clone_model.py
```

下载完成后（约 4.3GB），即可使用声音克隆功能：
- 上传一段 3-10 秒的参考音频
- 输入参考音频对应的文本
- 输入要转换的新文本
- 点击生成克隆语音

#### 3. 批量生成
- 每行输入一句话
- 选择音色和语言
- 自动批量生成并合并音频

---

## 预置音色列表

| 音色代码 | 音色描述 |
|---------|---------|
| `vivian` | 女声-年轻-可爱-亲切 |
| `serena` | 女声-年轻-中性 |
| `ono_anna` | 女声-成熟-温柔 |
| `aiden` | 男声-年轻-自然 |
| `dylan` | 男声-成熟-自然 |
| `ryan` | 男声-成熟-旁白 |
| `uncle_fu` | 男声-成熟-深沉 |
| `eric` | 男童-可爱 |
| `sohee` | 女童-可爱 |

---

## 命令行用法

```bash
# 激活虚拟环境
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

# 预置音色生成
python run_tts.py custom --text "你好，世界！" --speaker vivian --language Chinese

# 声音克隆
python run_tts.py clone --text "新文本" --ref-audio reference.wav --ref-text "参考文本"
```

---

## 目录结构

```
千问语音克隆/
├── 启动WebUI.bat          # Windows 启动脚本
├── 启动WebUI.sh            # Linux/macOS 启动脚本
├── webui.py                # WebUI 主程序
├── run_tts.py              # 命令行程序
├── download_clone_model.py # Base 模型下载脚本
├── requirements.txt        # Python 依赖
├── models/                 # CustomVoice 模型（4.3GB，预置音色）
├── models-base/            # Base 模型（4.3GB，声音克隆，需下载）
├── venv/                   # 虚拟环境（自动创建）
└── outputs/                # 输出音频目录
```

### 模型说明

| 模型 | 用途 | 大小 | 状态 |
|------|------|------|------|
| `models/` | 预置音色生成 | 4.3GB | ✅ 内置 |
| `models-base/` | 声音克隆 | 4.3GB | ⬇️ 需下载 |

---

## 常见问题

### 1. 声音克隆提示"模型未安装"？
声音克隆功能需要额外的 Base 模型。运行以下命令下载：
```bash
python download_clone_model.py
```

### 2. 首次运行很慢？
首次运行需要下载约 2GB 的 Python 依赖包，请耐心等待。后续启动会快很多。

### 3. 浏览器没有自动打开？
手动访问 http://localhost:7860

### 4. 端口 7860 被占用？
编辑 `webui.py`，修改最后的 `port=7860` 为其他端口

### 5. 想在其他设备访问？
- 同一局域网：使用电脑的 IP 地址访问，如 http://192.168.1.100:7860
- 公网访问：在启动脚本中添加 `--share` 参数

### 6. 生成速度慢？
- 当前使用 CPU 运行
- 如有 NVIDIA 显卡，可安装 GPU 版本加速

---

## GPU 加速（可选）

如有 NVIDIA 显卡，可安装 GPU 版本：

```bash
# 卸载 CPU 版本
pip uninstall torch torchaudio

# 安装 GPU 版本
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

然后修改 `webui.py` 中的 `device_map="cpu"` 为 `device_map="cuda:0"`

---

## 技术支持

- **Qwen3-TTS 官方仓库**: https://github.com/QwenLM/Qwen3-TTS
- **模型地址**: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice

---

## 许可证

本工具基于 Apache 2.0 许可证开源。模型使用请遵循 Qwen3-TTS 官方许可协议。

---

**版本**: 1.0 | **更新日期**: 2025-01-25
