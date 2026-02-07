#!/usr/bin/env python3
"""
修复千问语音克隆内存泄漏问题的补丁
安装必要的内存监控依赖包
"""

import subprocess
import sys
import os

def install_package(package):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {package} 安装失败")
        return False

def main():
    """主函数"""
    print("正在安装内存监控依赖包...")
    
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 需要安装的包
    packages = [
        "psutil",
        "memory-profiler",
    ]
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n安装完成: {success_count}/{len(packages)} 个包")
    
    if success_count == len(packages):
        print("✅ 所有依赖安装成功！")
        print("现在可以启动应用：./启动WebUI.sh")
    else:
        print("❌ 部分依赖安装失败，请手动安装")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())