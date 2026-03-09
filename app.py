#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易行数据可视化系统 - 主启动文件

使用方法:
    python app.py
    或
    python -m flask --app app run --debug --host=0.0.0.0 --port=5000
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# 创建 Flask 应用实例
app, visualizer = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 启动交易行数据可视化系统")
    print("=" * 60)
    print(f"📊 已加载 {len(visualizer.items_data)} 个物品数据")
    print(f"💾 存储类型：{'Redis' if visualizer.data_service.redis_client else '文件'}")
    print(f"🌐 访问地址：http://localhost:5000")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=5000)
