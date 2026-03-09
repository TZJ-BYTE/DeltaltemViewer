#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 get_price_history 方法"""

import sys
sys.path.insert(0, '/home/tzj/project/python/PythonProject')

from app.services.data_service import DataService
import time

ds = DataService()

# 测试获取历史数据
result = ds.get_price_history("哮喘吸入器", days=30)

print(f"返回结果数：{len(result)}")
print(f"当前时间戳：{int(time.time())}")
print(f"30 天前时间戳：{int(time.time()) - (30 * 24 * 60 * 60)}")

if result:
    print("\n前 3 条:")
    for r in result[:3]:
        print(f"  {r['time']} - {r['price']:.2f} (timestamp: {r['timestamp']})")
    
    print("\n最后 3 条:")
    for r in result[-3:]:
        print(f"  {r['time']} - {r['price']:.2f} (timestamp: {r['timestamp']})")
