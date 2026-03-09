#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看单个物品的历史价格数据
用于调试和验证
"""

import redis
import sys
from datetime import datetime

def view_item_history(item_name):
    """查看指定物品的历史价格"""
    
    # 连接 Redis
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    # 获取当前物品信息
    item_key = f"trading:item:*:{item_name}"
    found = False
    
    for key in r.scan_iter(item_key):
        item_data = r.hgetall(key)
        if item_data and item_data.get('name') == item_name:
            found = True
            print(f"\n{'='*60}")
            print(f"📦 物品信息：{item_name}")
            print(f"{'='*60}")
            print(f"当前价格：{item_data.get('price', 'N/A')} {item_data.get('currency', '哈弗币')}")
            print(f"分类：{item_data.get('category', 'N/A')}")
            print(f"来源：{item_data.get('source', 'N/A')}")
            print(f"更新时间：{item_data.get('crawl_time', 'N/A')}")
            break
    
    if not found:
        print(f"❌ 未找到物品：{item_name}")
        return
    
    # 获取历史价格
    history_key = f"trading:history:{item_name}"
    history_data = r.zrange(history_key, 0, -1, withscores=True)
    
    if not history_data:
        print(f"\n⚠️  该物品暂无历史价格数据")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 历史价格走势（共 {len(history_data)} 条记录）")
    print(f"{'='*60}")
    print(f"{'日期':<12} {'时间':<10} {'价格':>12} {'变化':>10}")
    print(f"{'-'*60}")
    
    prev_price = None
    for timestamp, price in history_data:
        dt = datetime.fromtimestamp(int(float(timestamp)))
        date_str = dt.strftime('%Y-%m-%d')
        time_str = dt.strftime('%H:%M:%S')
        
        if prev_price:
            change = price - prev_price
            change_pct = (change / prev_price) * 100
            change_str = f"{change:+.2f} ({change_pct:+.1f}%)"
        else:
            change_str = "-"
        
        print(f"{date_str:<12} {time_str:<10} {price:>12.2f} {change_str:>10}")
        
        prev_price = price
    
    # 统计信息
    prices = [p for _, p in history_data]
    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)
    current_price = prices[-1]
    first_price = prices[0]
    total_change = current_price - first_price
    total_change_pct = (total_change / first_price) * 100
    
    print(f"\n{'='*60}")
    print(f"📈 统计分析")
    print(f"{'='*60}")
    print(f"最低价：{min_price:.2f}")
    print(f"最高价：{max_price:.2f}")
    print(f"平均价：{avg_price:.2f}")
    print(f"起始价：{first_price:.2f}")
    print(f"当前价：{current_price:.2f}")
    print(f"总变化：{total_change:+.2f} ({total_change_pct:+.1f}%)")
    print(f"波动幅度：{(max_price - min_price):.2f} ({((max_price - min_price) / avg_price * 100):.1f}%)")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法：python scripts/check_item_history.py <物品名称>")
        print("\n示例:")
        print("  python scripts/check_item_history.py 哮喘吸入器")
        print("  python scripts/check_item_history.py \"阵列服务器\"")
        sys.exit(1)
    
    item_name = sys.argv[1]
    view_item_history(item_name)
