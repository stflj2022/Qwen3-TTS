#!/usr/bin/env python3
"""
紧急内存泄漏修复脚本
解决千问语音克隆内存泄漏问题
"""

import os
import sys
import time
import gc
import torch
import psutil
from pathlib import Path

def check_memory_usage():
    """检查当前内存使用"""
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_gb = memory_info.rss / (1024 ** 3)
    return memory_gb, memory_info

def force_memory_cleanup():
    """强制内存清理"""
    print("🧹 执行紧急内存清理...")
    
    # 清理Python垃圾
    collected = gc.collect()
    print(f"Python GC回收了 {collected} 个对象")
    
    # 清理GPU缓存
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        print("GPU缓存已清理")
    
    # 再次垃圾回收
    collected = gc.collect()
    print(f"第二次GC回收了 {collected} 个对象")
    
    return True

def check_model_memory():
    """检查模型内存占用"""
    try:
        # 检查PyTorch模型
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / (1024 ** 3)
                cached = torch.cuda.memory_reserved(i) / (1024 ** 3)
                print(f"GPU {i}: 分配 {allocated:.2f}GB, 缓存 {cached:.2f}GB")
        
        # 检查大对象
        large_objects = []
        for obj in gc.get_objects():
            if hasattr(obj, '__sizeof__'):
                try:
                    size = sys.getsizeof(obj) / (1024 ** 2)
                    if size > 0.1:  # 大于100MB的对象
                        large_objects.append((type(obj).__name__, size))
                except:
                    pass
        
        if large_objects:
            print("⚠️ 发现大对象:")
            for obj_type, size in sorted(large_objects, key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {obj_type}: {size:.2f}GB")
        
    except Exception as e:
        print(f"检查模型内存时出错: {e}")

def restart_application():
    """重启应用"""
    print("🔄 正在重启应用...")
    
    # 清理所有可能的残留
    force_memory_cleanup()
    
    # 给用户重启建议
    print("\n💡 应用已安全退出，请重新启动:")
    print("cd /home/wu/文档/千问语音克隆")
    print("./启动WebUI.sh")
    print("\n🔧 如果仍有问题，建议:")
    print("1. 重启电脑清理内存")
    print("2. 检查是否有其他内存密集型程序")
    print("3. 考虑增加系统虚拟内存")

def main():
    """主函数"""
    print("🚨 千问语音克隆 - 紧急内存泄漏修复工具")
    print("=" * 50)
    
    # 检查当前内存状态
    current_memory, memory_info = check_memory_usage()
    print(f"📊 当前内存使用: {current_memory:.2f}GB")
    
    # 检查模型内存占用
    print("🔍 检查模型内存占用...")
    check_model_memory()
    
    # 强制内存清理
    force_memory_cleanup()
    
    # 再次检查内存
    after_memory, _ = check_memory_usage()
    memory_freed = current_memory - after_memory
    
    print(f"✅ 内存清理完成:")
    print(f"   清理前: {current_memory:.2f}GB")
    print(f"   清理后: {after_memory:.2f}GB")
    print(f"   释放内存: {memory_freed:.2f}GB")
    
    # 如果内存仍然过高，建议重启
    if after_memory > 6.0:  # 超过6GB建议重启
        print(f"\n⚠️ 内存使用仍然过高: {after_memory:.2f}GB")
        restart_application()
        return False
    
    print("\n💾 内存使用已降至安全范围，可以继续使用")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)