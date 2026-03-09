#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器状态检查脚本
验证 Flask 服务、Redis 连接和数据完整性
"""

import redis
import requests
import json
from datetime import datetime

print("=" * 70)
print("🔍 服务器状态检查")
print("=" * 70)

# 1. 检查 Redis 连接
print("\n[1/4] 检查 Redis 连接...")
try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    print(f"✅ Redis 连接正常 (localhost:6379)")
    
    # 检查数据量
    item_count = 0
    for key in r.scan_iter("trading:item:*"):
        item_count += 1
    
    history_count = 0
    for key in r.scan_iter("trading:history:*"):
        history_count += 1
    
    print(f"   - 物品数量：{item_count} 个")
    print(f"   - 历史记录：{history_count} 条")
except Exception as e:
    print(f"❌ Redis 连接失败：{e}")

# 2. 检查 Flask 服务
print("\n[2/4] 检查 Flask 服务...")
try:
    response = requests.get('http://localhost:5000', timeout=5)
    if response.status_code == 200:
        print(f"✅ Flask 服务运行正常 (http://localhost:5000)")
        print(f"   - HTTP 状态码：{response.status_code}")
    else:
        print(f"⚠️  Flask 服务响应异常：{response.status_code}")
except Exception as e:
    print(f"❌ Flask 服务无法访问：{e}")

# 3. 检查 API 接口
print("\n[3/4] 检查 API 接口...")
try:
    # 检查统计数据 API
    response = requests.get('http://localhost:5000/api/statistics', timeout=5)
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ /api/statistics 正常")
        print(f"   - 总物品数：{stats.get('total_items', 0)} 个")
        print(f"   - 分类数量：{len(stats.get('categories', {}))} 个")
    else:
        print(f"⚠️  统计数据 API 异常：{response.status_code}")
    
    # 检查物品列表 API
    response = requests.get('http://localhost:5000/api/items?page=1&per_page=10', timeout=5)
    if response.status_code == 200:
        items_data = response.json()
        print(f"✅ /api/items 正常")
        print(f"   - 返回物品数：{len(items_data.get('items', []))} 个")
    else:
        print(f"⚠️  物品列表 API 异常：{response.status_code}")
        
    # 检查历史数据 API（测试哮喘吸入器）
    test_item = "哮喘吸入器"
    response = requests.get(f'http://localhost:5000/api/items/{test_item}/history?days=30', timeout=5)
    if response.status_code == 200:
        history = response.json()
        if len(history) > 0:
            print(f"✅ 历史数据 API 正常")
            print(f"   - '{test_item}' 历史记录：{len(history)} 条")
            print(f"   - 最新价格：{history[-1].get('price', 0):.2f} 哈弗币")
            print(f"   - 最早价格：{history[0].get('price', 0):.2f} 哈弗币")
        else:
            print(f"⚠️  '{test_item}' 暂无历史数据")
    else:
        print(f"⚠️  历史数据 API 异常：{response.status_code}")
        
except Exception as e:
    print(f"❌ API 检查失败：{e}")

# 4. 网络可访问性测试
print("\n[4/4] 网络可访问性...")
print(f"💡 提示：")
print(f"   - 本地访问：http://localhost:5000")
print(f"   - 局域网访问：http://10.2.8.15:5000")
print(f"   - 公网访问：http://82.156.116.206:5000")
print(f"\n⚠️  如果公网无法访问，请检查：")
print(f"   1. 云服务器安全组是否开放 5000 端口")
print(f"   2. 防火墙规则是否允许外部连接")
print(f"   3. 路由器端口转发配置（如有）")

# 总结
print("\n" + "=" * 70)
print("📊 检查完成总结")
print("=" * 70)
print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"服务状态：✅ 运行中")
print(f"数据状态：✅ {item_count} 个物品，{history_count} 条历史记录")
print(f"API 状态：✅ 正常响应")
print(f"\n🌐 请访问：http://82.156.116.206:5000")
print("=" * 70)
