#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易行数据可视化 Web 应用
提供物品价格查询、统计分析和可视化展示
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from datetime import datetime
import os
from app.services.data_service import data_service
from app.visualizer import TradingDataVisualizer

def create_app():
    """创建 Flask 应用实例"""
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(
        __name__,
        template_folder=os.path.join(root_dir, 'templates'),
        static_folder=os.path.join(root_dir, 'static') if os.path.exists(os.path.join(root_dir, 'static')) else None
    )
    
    # 配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    # 使用 crawlers 目录下的交易价格数据
    app.config['DATA_DIR'] = os.getenv('DATA_DIR', os.path.join(root_dir, 'crawlers', 'trading_price_data'))
    
    # 注册自定义 Jinja2 过滤器
    @app.template_filter('format_time')
    def format_time_filter(time_string):
        """格式化时间字符串为中文格式"""
        if not time_string:
            return '未知时间'
        try:
            # 尝试解析 ISO 格式
            date = datetime.fromisoformat(time_string.replace('Z', '+00:00'))
            return date.strftime('%Y-%m-%d %H:%M:%S')
        except:
            # 如果解析失败，返回原始字符串
            return str(time_string)
    
    # 初始化数据服务
    data_service_instance = data_service
    
    # 初始化可视化器
    visualizer = TradingDataVisualizer(data_dir=app.config['DATA_DIR'])
    
    # 注册路由
    from app.routes import main_routes
    app.register_blueprint(main_routes.bp)
    
    # 注册 API 路由并设置可视化器
    from app.routes import api_routes
    api_routes.set_visualizer(visualizer)
    app.register_blueprint(api_routes.bp, url_prefix='/api')
    
    return app, visualizer

# 创建应用实例
app, visualizer = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
