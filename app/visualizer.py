#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易数据可视化器
负责数据加载、统计和图表生成
"""

import json
import os
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
from datetime import datetime

class TradingDataVisualizer:
    """交易行数据可视化器"""
    
    def __init__(self, data_dir="trading_price_data"):
        self.data_dir = data_dir
        self.items_data = []
        from app.services.data_service import data_service
        self.data_service = data_service
        
        print(f"数据服务初始化完成，存储类型：{data_service.redis_client is not None}")
        self.load_trading_data()
    
    def load_trading_data(self):
        """加载交易行数据（仅从 Redis 加载）"""
        self.items_data = []
        
        try:
            # 使用统一数据服务从 Redis 加载数据
            self.items_data = self.data_service.load_trading_data()
            if self.items_data:
                print(f"✓ 从 Redis 成功加载 {len(self.items_data)} 个物品数据")
                print(f"  存储类型：Redis (优化格式)")
                return  # Redis 有数据，直接返回
        except Exception as e:
            print(f"✗ Redis 数据加载失败：{e}")
            self.items_data = []
        
        # Redis 无数据时，不降级到文件加载，直接返回空数据
        print("⚠️ Redis 中无数据，请检查爬虫是否已运行并保存数据到 Redis")
        print("  提示：运行爬虫脚本将数据保存到 Redis")
    
    def _process_item_data(self, item, crawl_time):
        """处理单个物品数据（已移至 DataService）"""
        return self.data_service._process_item(item, crawl_time)
    
    def get_price_statistics(self):
        """获取价格统计信息"""
        if not self.items_data:
            return {}
        
        df = pd.DataFrame(self.items_data)
        
        # 确保数值类型可 JSON 序列化
        stats = {
            'total_items': int(len(df)),
            'avg_price': float(df['price'].mean()),
            'min_price': float(df['price'].min()),
            'max_price': float(df['price'].max()),
            'price_std': float(df['price'].std()) if not df['price'].std() != df['price'].std() else 0,  # 处理 NaN
            'categories': {k: int(v) for k, v in df['category'].value_counts().to_dict().items()},
            'currency_distribution': {k: int(v) for k, v in df['currency'].value_counts().to_dict().items()}
        }
        
        return stats
    
    def get_redis_stats(self):
        """获取 Redis 存储统计信息"""
        if not self.data_service.redis_client or not self._check_redis_connection():
            return None
            
        try:
            # 获取交易数据统计
            trading_keys = self.data_service.redis_client.keys("trading_data:*")
            metadata_keys = self.data_service.redis_client.keys("metadata:trading_data:*")
            
            total_items = 0
            categories = defaultdict(int)
            
            # 统计物品数量和分类
            for key in trading_keys:
                try:
                    data_json = self.data_service.redis_client.get(key)
                    if data_json:
                        data = json.loads(data_json)
                        items = data.get('items', [])
                        total_items += len(items)
                        
                        for item in items:
                            if isinstance(item, dict):
                                category = item.get('category', '未知')
                                categories[category] += 1
                except Exception as e:
                    print(f"读取 Redis 数据失败 {key}: {e}")
                    continue
            
            return {
                'total_records': len(trading_keys),
                'total_items': total_items,
                'categories': dict(categories),
                'metadata_records': len(metadata_keys)
            }
        except Exception as e:
            print(f"Redis 统计获取失败：{e}")
            return None
    
    def get_price_trend_data(self):
        """获取价格趋势数据"""
        if not self.items_data:
            return []
        
        # 按时间分组统计
        trend_data = []
        time_groups = defaultdict(list)
        
        for item in self.items_data:
            if item['crawl_time']:
                date_key = item['crawl_time'][:10]  # 取日期部分
                time_groups[date_key].append(item['price'])
        
        for date, prices in sorted(time_groups.items()):
            trend_data.append({
                'date': date,
                'avg_price': sum(prices) / len(prices),
                'count': len(prices),
                'min_price': min(prices),
                'max_price': max(prices)
            })
        
        return trend_data
    
    def _check_redis_connection(self):
        """检查 Redis 连接状态"""
        try:
            self.data_service.redis_client.ping()
            return True
        except:
            return False
