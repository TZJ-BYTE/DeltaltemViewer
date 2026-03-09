#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 路由模块
提供数据接口服务
"""

from flask import Blueprint, jsonify, request, send_from_directory
import os
import json
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
from datetime import datetime, timedelta

bp = Blueprint('api', __name__)

# 全局可视化器实例（从主应用导入）
visualizer = None

def set_visualizer(vis):
    """设置可视化器实例"""
    global visualizer
    visualizer = vis

@bp.route('/items')
def api_items():
    """API: 获取物品数据"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    # 处理 URL 编码问题
    if category:
        try:
            category = category.encode('latin1').decode('utf-8')
        except:
            pass
    
    # 如果内存中没有数据，才从 Redis 加载
    if not visualizer.items_data:
        try:
            visualizer.load_trading_data()
        except Exception as e:
            return jsonify({
                'error': f'数据加载失败：{str(e)}',
                'items': [],
                'total': 0
            }), 500
    
    # 过滤数据
    filtered_data = visualizer.items_data
    if category and category != '全部':
        filtered_data = [item for item in filtered_data if item['category'] == category]
    
    # 搜索过滤
    if search:
        search_lower = search.lower()
        filtered_data = [item for item in filtered_data if search_lower in item['name'].lower()]
    
    # 分页
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_data = filtered_data[start_idx:end_idx]
    
    # 确保价格为整数
    processed_items = []
    for item in paginated_data:
        processed_item = item.copy()
        processed_item['price'] = int(processed_item.get('price', 0))
        processed_items.append(processed_item)
    
    return jsonify({
        'items': processed_items,
        'total': len(filtered_data),
        'page': page,
        'per_page': per_page,
        'categories': list(set([item['category'] for item in visualizer.items_data]))
    })

@bp.route('/categories')
def api_categories():
    """API: 获取所有分类列表（从 Redis 动态加载）"""
    try:
        # 从 Redis 获取分类索引
        redis_client = visualizer.data_service.redis_client
        if redis_client:
            index_keys = redis_client.keys('trading:index:*')
            categories = []
            for key in index_keys:
                # 提取分类名称
                parts = key.split(':')
                if len(parts) >= 3:
                    category = ':'.join(parts[2:])
                    categories.append(category)
            
            # 排序并返回
            categories.sort()
            return jsonify({
                'success': True,
                'categories': categories
            })
        else:
            # 如果没有 Redis，返回内存中的分类
            categories = list(set([item['category'] for item in visualizer.items_data]))
            categories.sort()
            return jsonify({
                'success': True,
                'categories': categories
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/statistics')
def api_statistics():
    """API: 获取统计信息"""
    stats = visualizer.get_price_statistics()
    
    # 添加存储信息
    service_stats = visualizer.data_service.get_statistics()
    stats.update(service_stats)
    
    return jsonify(stats)

@bp.route('/charts/price-distribution')
def chart_price_distribution():
    """API: 价格分布图数据"""
    if not visualizer.items_data:
        return jsonify({'error': '没有数据'})
    
    df = pd.DataFrame(visualizer.items_data)
    
    # 创建价格区间
    bins = [0, 100, 500, 1000, 5000, 10000, float('inf')]
    labels = ['0-100', '100-500', '500-1000', '1000-5000', '5000-10000', '10000+']
    
    df['price_range'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)
    price_dist = df['price_range'].value_counts().sort_index()
    
    # 创建柱状图
    fig = px.bar(
        x=price_dist.index,
        y=price_dist.values,
        labels={'x': '价格区间', 'y': '物品数量'},
        title='物品价格分布'
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graph_json

@bp.route('/charts/category-distribution')
def chart_category_distribution():
    """API: 分类分布图数据"""
    if not visualizer.items_data:
        return jsonify({'error': '没有数据'})
    
    df = pd.DataFrame(visualizer.items_data)
    category_counts = df['category'].value_counts()
    
    # 创建饼图
    fig = px.pie(
        values=category_counts.values,
        names=category_counts.index,
        title='物品分类分布'
    )
    
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graph_json

@bp.route('/charts/price-trend')
def chart_price_trend():
    """API: 价格趋势图数据"""
    trend_data = visualizer.get_price_trend_data()
    
    if not trend_data:
        return jsonify({'error': '没有趋势数据'})
    
    df = pd.DataFrame(trend_data)
    
    # 创建折线图
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['avg_price'],
        mode='lines+markers',
        name='平均价格',
        line=dict(color='#1f77b4', width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['min_price'],
        mode='lines',
        name='最低价格',
        line=dict(color='#ff7f0e', width=2, dash='dot')
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['max_price'],
        mode='lines',
        name='最高价格',
        line=dict(color='#2ca02c', width=2, dash='dot')
    ))
    
    fig.update_layout(
        title='价格趋势变化',
        xaxis_title='日期',
        yaxis_title='价格',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified'
    )
    
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graph_json

@bp.route('/item-history/<item_name>')
def api_item_history(item_name):
    """API: 获取特定物品的历史价格数据（仅从 Redis 获取真实数据）"""
    try:
        days = int(request.args.get('days', 7))
        history_data = visualizer.data_service.get_price_history(item_name, days)
        
        if history_data:
            return jsonify(history_data)
        else:
            # 没有历史数据时返回空数组，不再使用模拟数据
            return jsonify([])
            
    except Exception as e:
        logger.error(f"获取物品历史数据失败：{e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/items/<item_name>/history')
def api_item_price_history(item_name):
    """API: 获取物品的历史价格数据（新版本）"""
    try:
        days = int(request.args.get('days', 7))
        history_data = visualizer.data_service.get_price_history(item_name, days)
        
        if not history_data:
            # 如果没有历史数据，返回当前价格作为单条记录
            current_item = None
            for item in visualizer.items_data:
                if item['name'] == item_name:
                    current_item = item
                    break
            
            if current_item:
                return jsonify([{
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'price': current_item['price'],
                    'timestamp': int(datetime.now().timestamp())
                }])
            else:
                return jsonify([])
        
        return jsonify(history_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/items-with-images')
def api_items_with_images():
    """API: 获取带图片的物品数据"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    # 筛选有图片的物品
    items_with_images = [item for item in visualizer.items_data if item.get('image_url')]
    
    # 分页
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_data = items_with_images[start_idx:end_idx]
    
    return jsonify({
        'items': paginated_data,
        'total': len(items_with_images),
        'page': page,
        'per_page': per_page
    })

@bp.route('/static/images/<filename>')
def serve_local_image(filename):
    """提供本地缓存的图片"""
    image_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'local_image_cache')
    return send_from_directory(image_dir, filename)

