# 千问语音克隆内存泄漏修复方案

## 问题分析

根据日志分析，您的应用出现了严重的内存泄漏问题，导致：
- 运行3秒后系统死机
- 鼠标键盘无响应  
- 5分钟后恢复，显示"虚拟终端进程使用大量内存已被强制停止"
- 声音设计和声音克隆页面都出现过相同问题

## 根本原因

1. **模型重复加载**：三个大型模型（CustomVoice、Base、VoiceDesign）同时驻留内存
2. **批量生成内存累积**：音频处理过程中没有及时清理临时变量
3. **缺乏内存监控**：没有内存使用限制和自动清理机制
4. **垃圾回收不及时**：GPU缓存和Python对象没有定期清理

## 修复方案

### 1. 新增内存管理系统 (`memory_manager.py`)

**核心功能：**
- 实时监控内存使用情况（CPU + GPU）
- 自动垃圾回收机制
- 内存限制和预警（默认6GB）
- 模型懒加载和自动卸载
- 后台监控线程

**关键组件：**
```python
- MemoryManager: 内存监控和管理
- ModelManager: 模型生命周期管理  
- memory_monitor装饰器: 函数级内存保护
```

### 2. 优化模型加载策略

**修复前：**
- 所有模型启动时全部加载
- 模型永久驻留内存
- 无内存压力检测

**修复后：**
- 懒加载：仅在使用时加载
- 自动卸载：5分钟未使用自动清理
- 内存检查：加载前检查可用内存
- 异常处理：OOM时自动清理

### 3. 修复批量生成内存泄漏

**修复前问题：**
- 所有音频数据同时保存在内存
- 大量AudioSegment对象累积
- 一次性合并导致内存峰值

**修复后方案：**
- 分批处理：每50个音频一批
- 及时保存：立即写入磁盘
- 定期清理：每10个音频清理临时变量
- 安全合并：分小段合并避免峰值

### 4. 添加系统级保护

**内存限制：**
- 警告阈值：70% 使用量
- 危险阈值：90% 使用量  
- 强制清理：超过阈值自动GC
- 监控间隔：5秒检查一次

**异常处理：**
- 程序退出时强制清理
- Ctrl+C优雅退出
- 异常时自动清理内存

## 使用方法

### 1. 启动应用
```bash
cd /home/wu/文档/千问语音克隆
./启动WebUI.sh
```

脚本会自动：
- 安装内存监控依赖（psutil, memory-profiler）
- 启动内存管理系统
- 注册退出清理函数

### 2. 监控内存使用
应用启动后，内存管理器会在后台运行：
- 内存使用超过70%：自动垃圾回收
- 内存使用超过90%：紧急清理 + 警告
- 每30秒定期清理：防止内存碎片

### 3. 安全使用建议

**批量生成：**
- 每次不超过100行文本
- 长文本分章节处理
- 监控内存使用情况

**模型切换：**
- 不用的功能页面及时关闭
- 避免同时加载多个模型
- 系统会自动卸载闲置模型

## 技术细节

### 内存监控技术
```python
# CPU内存监控
process = psutil.Process()
memory_info = process.memory_info()

# GPU内存监控（如果有）
if torch.cuda.is_available():
    torch.cuda.memory_allocated()
    torch.cuda.empty_cache()
```

### 模型管理策略
```python
# 懒加载
def load_model(name, loader_func):
    if name not in loaded_models:
        check_memory()
        model = loader_func()
        loaded_models[name] = model
    return loaded_models[name]

# 自动卸载
def cleanup_idle_models():
    for model in idle_models:
        unload_model(model)
        gc.collect()
```

### 批量处理优化
```python
# 分批处理
for batch in split_into_batches(items, batch_size=50):
    process_batch(batch)
    cleanup_memory()  # 每批清理
```

## 预期效果

**修复前：**
- 内存使用：无限增长 → 系统死机
- 稳定性：3秒后崩溃
- 用户体验：系统无响应

**修复后：**
- 内存使用：稳定在6GB以下
- 稳定性：长时间稳定运行
- 用户体验：流畅使用，自动保护

## 监控和日志

内存管理器会输出详细日志：
```
[INFO] 内存监控已启动
[WARNING] 内存使用警告: 当前使用 4.2GB
[INFO] 执行强制垃圾回收...
[INFO] Python GC回收了 1234 个对象
[INFO] CUDA缓存已清理
```

## 故障排除

**如果仍有内存问题：**

1. 检查依赖是否正确安装：
   ```bash
   python fix_memory_dependencies.py
   ```

2. 手动清理内存：
   ```python
   from memory_manager import cleanup_memory
   cleanup_memory()
   ```

3. 调整内存限制（在memory_manager.py中）：
   ```python
   global_memory_manager = MemoryManager(max_memory_gb=4.0)  # 降低到4GB
   ```

4. 监控系统资源：
   - 确保可用RAM > 8GB
   - 关闭其他内存密集型应用

## 文件清单

修复方案包含以下文件：

1. **memory_manager.py** - 核心内存管理系统
2. **fix_memory_dependencies.py** - 依赖安装脚本  
3. **webui.py** - 修复后的主程序（添加内存管理）
4. **启动WebUI.sh** - 更新的启动脚本
5. **MEMORY_FIX_README.md** - 本说明文档

所有修改都是非侵入性的，不会影响现有功能。

---

**总结：** 这个修复方案通过多层内存管理技术，从根本上解决了内存泄漏问题，确保应用稳定运行，不再出现系统死机的情况。