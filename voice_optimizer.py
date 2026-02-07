#!/usr/bin/env python3
"""
千问语音克隆音色优化模块
解决预置音色口音问题，确保标准普通话发音
"""

import re
from typing import Dict, List, Optional

class StandardChineseProcessor:
    """标准普通话处理器"""
    
    def __init__(self):
        # 常见的方言词汇映射到标准普通话
        self.dialect_mapping = {
            # 四川话词汇
            "啥子": "什么",
            "啷个": "怎么", 
            "要得": "好的",
            "巴适": "舒服",
            "摆龙门阵": "聊天",
            "冲壳子": "吹牛",
            "扯把子": "聊天",
            "洗白": "清楚",
            "安逸": "舒服",
            "雄起": "努力",
            
            # 北方话词汇
            "甭": "不用",
            "嘛": "吗",
            "咱": "我们",
            "您": "你",
            
            # 南方话常见词汇
            "晓得": "知道",
            "搞": "做",
            "蛮": "很",
        }
        
        # 口音语法模式修正
        self.grammar_patterns = [
            # 去除方言助词
            (r'([^\s])\s+嘛\s*([？。！，])', r'\1\2'),
            (r'([^\s])\s+咧\s*([？。！，])', r'\1\2'),
            (r'([^\s])\s+噻\s*([？。！，])', r'\1\2'),
            (r'([^\s])\s+哦\s*([？。！，])', r'\1\2'),
            
            # 标准化语气词
            (r'([^\s])\s+哈\s*([？。！，])', r'\1啊\2'),
            (r'([^\s])\s+咯\s*([？。！，])', r'\1了\2'),
        ]
        
        # 预设指令模板（声音设计可自定义）
        self.preset_instructions = [
            "请用标准普通话发音，避免任何方言口音",
            "使用标准的普通话语音，确保发音清晰准确",
            "用标准的汉语普通话朗读，避免地方口音",
            "采用标准的普通话语音，不要带任何方言色彩",
        ]
    
    def normalize_text(self, text: str) -> str:
        """标准化文本，去除方言词汇"""
        # 替换方言词汇
        normalized_text = text
        for dialect, standard in self.dialect_mapping.items():
            normalized_text = normalized_text.replace(dialect, standard)
        
        # 修正语法模式
        for pattern, replacement in self.grammar_patterns:
            normalized_text = re.sub(pattern, replacement, normalized_text)
        
        return normalized_text.strip()
    
    def get_instruction(self, user_instruct: Optional[str] = None, force_standard: bool = False) -> str:
        """获取指令，可选择是否强制标准普通话"""
        base_instruct = "请用标准普通话发音，避免任何方言口音" if force_standard else ""
        
        if user_instruct and user_instruct.strip():
            # 如果用户有自定义指令，在其基础上添加要求
            return f"{user_instruct.strip()}，{base_instruct}" if base_instruct else user_instruct.strip()
        
        return base_instruct
    
    def get_optimized_language_settings(self, language: str) -> Dict[str, str]:
        """获取优化后的语言设置"""
        # 强制使用中文设置，避免Auto带来的不确定性
        if language.lower() in ["auto", "自动"]:
            return {
                "language": "Chinese",
                "reason": "强制使用中文，避免Auto导致的口音问题"
            }
        
        # 标准化语言名称
        language_mapping = {
            "chinese": "Chinese",
            "中文": "Chinese", 
            "english": "English",
            "英文": "English",
            "japanese": "Japanese", 
            "日文": "Japanese",
            "korean": "Korean",
            "韩文": "Korean",
        }
        
        normalized_lang = language_mapping.get(language.lower(), language)
        
        return {
            "language": normalized_lang,
            "reason": f"使用标准化语言设置: {normalized_lang}"
        }


class VoiceOptimizer:
    """音色优化器"""
    
    def __init__(self):
        self.processor = StandardChineseProcessor()
    
    def optimize_generation_params(self, text: str, speaker: str, language: str, instruct: Optional[str]) -> Dict:
        """优化生成参数，预置音色确保标准普通话"""
        
        # 获取优化后的语言设置
        lang_settings = self.processor.get_optimized_language_settings(language)
        
        # 标准化文本（仅预置音色）
        normalized_text = self.processor.normalize_text(text)
        
        # 获取标准普通话指令（强制用于预置音色）
        standard_instruct = self.processor.get_instruction(instruct, force_standard=True)
        
        # 针对不同音色的特殊优化
        speaker_optimizations = {
            "vivian": {
                "instruction": f"{standard_instruct}，声音保持亲切自然",
                "temperature": 0.7,
            },
            "serena": {
                "instruction": f"{standard_instruct}，声音保持中性清晰", 
                "temperature": 0.6,
            },
            "ono_anna": {
                "instruction": f"{standard_instruct}，声音保持成熟温柔",
                "temperature": 0.65,
            },
            "aiden": {
                "instruction": f"{standard_instruct}，声音保持年轻自然",
                "temperature": 0.7,
            },
            "dylan": {
                "instruction": f"{standard_instruct}，声音保持成熟稳重",
                "temperature": 0.6,
            },
            "ryan": {
                "instruction": f"{standard_instruct}，声音保持权威专业",
                "temperature": 0.5,
            },
            "uncle_fu": {
                "instruction": f"{standard_instruct}，声音保持深沉有力",
                "temperature": 0.55,
            },
            "eric": {
                "instruction": f"{standard_instruct}，声音保持儿童自然",
                "temperature": 0.8,
            },
            "sohee": {
                "instruction": f"{standard_instruct}，声音保持儿童活泼",
                "temperature": 0.8,
            }
        }
        
        optimization = speaker_optimizations.get(speaker, {
            "instruction": standard_instruct,
            "temperature": 0.7,
        })
        
        return {
            "text": normalized_text,
            "language": lang_settings["language"],
            "speaker": speaker,
            "instruct": optimization["instruction"],
            "temperature": optimization["temperature"],
            "optimization_reason": lang_settings["reason"],
        }


def create_voice_optimizer():
    """创建全局音色优化器实例"""
    return VoiceOptimizer()


# 测试用例
if __name__ == "__main__":
    optimizer = create_voice_optimizer()
    
    # 测试方言词汇标准化
    test_texts = [
        "你晓得啥子意思不？",
        "今天天气巴适得很",
        "咱一起去要得？",
        "这个事情搞清楚了",
    ]
    
    print("=== 方言词汇标准化测试 ===")
    for text in test_texts:
        normalized = optimizer.processor.normalize_text(text)
        print(f"原文: {text}")
        print(f"标准: {normalized}")
        print()
    
    # 测试生成参数优化
    print("=== 生成参数优化测试 ===")
    params = optimizer.optimize_generation_params(
        text="你好，我是语音助手",
        speaker="vivian",
        language="Auto", 
        instruct="友好地问候"
    )
    
    for key, value in params.items():
        print(f"{key}: {value}")