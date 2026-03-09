#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块
提供通用的辅助函数
"""

import re
import os
import json


def get_safe_filename(text, max_length=50):
    """生成安全的文件名
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        安全的文件名字符串
    """
    safe_text = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', text)
    return safe_text[:max_length] if len(safe_text) > max_length else safe_text


def parse_price(price_str):
    """解析价格字符串，处理各种格式
    
    Args:
        price_str: 价格字符串（可能包含模板、货币符号等）
        
    Returns:
        解析后的整数价格，失败返回 0
    """
    if not price_str:
        return 0
    
    price_str = str(price_str)
    
    # 处理模板字符串 {{NumQfw(981424)}}
    template_match = re.search(r'\{\{NumQfw\((\d+(?:\.\d+)?)\)\}\}', price_str)
    if template_match:
        return int(float(template_match.group(1)))
    
    # 提取普通数字
    price_match = re.search(r'(\d+(?:\.\d+)?)', price_str)
    if price_match:
        return int(float(price_match.group(1)))
    
    return 0


def load_json_file(filepath):
    """加载 JSON 文件
    
    Args:
        filepath: 文件路径
        
    Returns:
        解析后的数据，失败返回 None
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载 JSON 文件失败 {filepath}: {e}")
        return None


def save_json_file(data, filepath, indent=2):
    """保存数据到 JSON 文件
    
    Args:
        data: 要保存的数据
        filepath: 文件路径
        indent: JSON 缩进空格数
        
    Returns:
        成功返回 True，失败返回 False
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        print(f"保存 JSON 文件失败 {filepath}: {e}")
        return False


def format_number(num, precision=2):
    """格式化数字显示
    
    Args:
        num: 数字
        precision: 小数精度
        
    Returns:
        格式化后的字符串
    """
    if isinstance(num, (int, float)):
        if num == int(num):
            return str(int(num))
        else:
            return f"{num:.{precision}f}"
    return str(num)
