#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 Redis 中哮喘吸入器的原始数据"""

import redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# 获取所有记录
history_key = 'trading:history:哮喘吸入器'
all_data = r.zrange(history_key, 0, -1, withscores=True)

print(f"总记录数：{len(all_data)}\n")

if all_data:
    print("前 3 条:")
    for ts_str, price in all_data[:3]:
        print(f"  时间戳：{ts_str!r} (类型:{type(ts_str).__name__}), 价格：{price}")
        
    print("\n最后 3 条:")
    for ts_str, price in all_data[-3:]:
        print(f"  时间戳：{ts_str!r} (类型:{type(ts_str).__name__}), 价格：{price}")
    
    # 尝试转换时间戳
    print("\n尝试转换时间戳:")
    for ts_str, price in all_data[:3]:
        try:
            ts = int(float(ts_str))
            from datetime import datetime
            dt = datetime.fromtimestamp(ts)
            print(f"  {ts_str!r} -> {ts} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"  {ts_str!r} -> 转换失败：{e}")
