#!/usr/bin/env python3
"""
内存管理模块 - 解决千问语音克隆的内存泄漏问题
主要功能：
1. 实时监控内存使用情况
2. 自动垃圾回收
3. 内存限制和预警
4. 模型卸载和清理
"""

import gc
import os
import psutil
import torch
import threading
import time
from typing import Optional, Callable, Dict, Any
from functools import wraps
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemoryManager:
    """内存管理器 - 监控和管理应用内存使用"""
    
    def __init__(self, max_memory_gb: float = 8.0, check_interval: float = 5.0):
        """
        初始化内存管理器
        
        Args:
            max_memory_gb: 最大允许内存使用量（GB）
            check_interval: 内存检查间隔（秒）
        """
        self.max_memory_bytes = max_memory_gb * 1024 * 1024 * 1024
        self.check_interval = check_interval
        self.process = psutil.Process()
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.callbacks: Dict[str, Callable] = {}
        self.last_gc_time = time.time()
        self.gc_interval = 30.0  # 垃圾回收间隔
        
        # 注册回调函数
        self.register_callback('memory_warning', self._default_memory_warning)
        self.register_callback('memory_critical', self._default_memory_critical)
        
    def register_callback(self, event: str, callback: Callable):
        """注册事件回调函数"""
        self.callbacks[event] = callback
        
    def get_memory_info(self) -> Dict[str, Any]:
        """获取当前内存使用信息"""
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        # 获取GPU内存（如果有）
        gpu_memory = {}
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                gpu_memory[f'gpu_{i}'] = {
                    'allocated': torch.cuda.memory_allocated(i),
                    'cached': torch.cuda.memory_reserved(i),
                    'max_allocated': torch.cuda.max_memory_allocated(i),
                }
        
        return {
            'rss': memory_info.rss,  # 物理内存
            'vms': memory_info.vms,  # 虚拟内存
            'percent': memory_percent,
            'gpu_memory': gpu_memory,
            'timestamp': time.time()
        }
    
    def get_memory_usage_gb(self) -> float:
        """获取当前内存使用量（GB）"""
        return self.process.memory_info().rss / (1024 ** 3)
    
    def is_memory_critical(self) -> bool:
        """检查内存是否达到危险水平"""
        current_memory = self.process.memory_info().rss
        return current_memory > self.max_memory_bytes * 0.9
    
    def is_memory_warning(self) -> bool:
        """检查内存是否需要警告"""
        current_memory = self.process.memory_info().rss
        return current_memory > self.max_memory_bytes * 0.7
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        logger.info("执行强制垃圾回收...")
        
        # 清理Python垃圾
        collected = gc.collect()
        logger.info(f"Python GC回收了 {collected} 个对象")
        
        # 清理CUDA缓存（如果有）
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            logger.info("CUDA缓存已清理")
        
        self.last_gc_time = time.time()
    
    def _default_memory_warning(self, memory_info: Dict[str, Any]):
        """默认内存警告处理"""
        logger.warning(f"内存使用警告: 当前使用 {memory_info['rss'] / (1024**3):.2f}GB")
        self.force_garbage_collection()
    
    def _default_memory_critical(self, memory_info: Dict[str, Any]):
        """默认内存危险处理"""
        logger.error(f"内存使用危险: 当前使用 {memory_info['rss'] / (1024**3):.2f}GB")
        self.force_garbage_collection()
        
        # 在危险情况下，可以触发更激进的清理措施
        logger.critical("内存使用超过安全限制，建议重启应用")
    
    def _monitor_loop(self):
        """内存监控循环"""
        logger.info("内存监控线程已启动")
        
        while self.monitoring:
            try:
                memory_info = self.get_memory_info()
                
                # 检查是否需要垃圾回收
                if time.time() - self.last_gc_time > self.gc_interval:
                    if self.is_memory_warning():
                        self.callbacks['memory_warning'](memory_info)
                    
                    if self.is_memory_critical():
                        self.callbacks['memory_critical'](memory_info)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"内存监控出错: {e}")
                time.sleep(self.check_interval)
    
    def start_monitoring(self):
        """开始内存监控"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("内存监控已启动")
    
    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("内存监控已停止")
    
    def __enter__(self):
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_monitoring()


def memory_monitor(max_memory_gb: float = 8.0):
    """内存监控装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 检查当前内存使用
            process = psutil.Process()
            current_memory = process.memory_info().rss / (1024 ** 3)
            
            if current_memory > max_memory_gb * 0.8:
                logger.warning(f"函数 {func.__name__} 执行前内存已较高: {current_memory:.2f}GB")
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            try:
                result = func(*args, **kwargs)
                
                # 函数执行后检查内存
                after_memory = process.memory_info().rss / (1024 ** 3)
                if after_memory > max_memory_gb:
                    logger.error(f"函数 {func.__name__} 执行后内存超限: {after_memory:.2f}GB")
                    # 强制垃圾回收
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                
                return result
                
            except Exception as e:
                logger.error(f"函数 {func.__name__} 执行出错: {e}")
                # 出错时清理内存
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                raise
                
        return wrapper
    return decorator


class ModelManager:
    """模型管理器 - 管理模型的加载和卸载"""
    
    def __init__(self):
        self.loaded_models: Dict[str, Any] = {}
        self.model_access_time: Dict[str, float] = {}
        self.max_idle_time = 300  # 5分钟未使用则卸载
        self.memory_manager = MemoryManager()
        
    def load_model(self, model_name: str, loader_func: Callable, *args, **kwargs) -> Any:
        """加载模型（带内存管理）"""
        current_time = time.time()
        
        # 如果模型已加载，更新访问时间
        if model_name in self.loaded_models:
            self.model_access_time[model_name] = current_time
            return self.loaded_models[model_name]
        
        # 检查内存是否足够
        if self.memory_manager.is_memory_warning():
            self.memory_manager.force_garbage_collection()
            self._unload_idle_models()
        
        # 加载新模型
        logger.info(f"正在加载模型: {model_name}")
        model = loader_func(*args, **kwargs)
        
        self.loaded_models[model_name] = model
        self.model_access_time[model_name] = current_time
        
        logger.info(f"模型 {model_name} 加载完成")
        return model
    
    def unload_model(self, model_name: str):
        """卸载指定模型"""
        if model_name in self.loaded_models:
            model = self.loaded_models[model_name]
            
            # 清理模型
            if hasattr(model, 'cpu'):
                model.cpu()
            if hasattr(model, 'eval'):
                del model
            
            del self.loaded_models[model_name]
            if model_name in self.model_access_time:
                del self.model_access_time[model_name]
            
            # 强制垃圾回收
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"模型 {model_name} 已卸载")
    
    def _unload_idle_models(self):
        """卸载闲置模型"""
        current_time = time.time()
        idle_models = []
        
        for model_name, access_time in self.model_access_time.items():
            if current_time - access_time > self.max_idle_time:
                idle_models.append(model_name)
        
        for model_name in idle_models:
            logger.info(f"卸载闲置模型: {model_name}")
            self.unload_model(model_name)
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """获取已加载的模型"""
        if model_name in self.loaded_models:
            self.model_access_time[model_name] = time.time()
            return self.loaded_models[model_name]
        return None
    
    def cleanup_all_models(self):
        """清理所有模型"""
        model_names = list(self.loaded_models.keys())
        for model_name in model_names:
            self.unload_model(model_name)
        
        logger.info("所有模型已清理")


# 全局内存管理器实例 - 调整到更合理限制
global_memory_manager = MemoryManager(max_memory_gb=10.0)  # 10GB限制
global_model_manager = ModelManager()

def init_memory_management():
    """初始化内存管理"""
    global_memory_manager.start_monitoring()
    logger.info("内存管理系统已初始化")

def cleanup_memory():
    """清理内存"""
    global_memory_manager.force_garbage_collection()
    global_model_manager.cleanup_all_models()
    logger.info("内存清理完成")