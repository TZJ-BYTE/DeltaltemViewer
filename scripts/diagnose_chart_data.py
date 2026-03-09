#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表数据问题诊断脚本
检查 Redis 数据、API 返回和前端显示的数据量
"""

import redis
import requests
from datetime import datetime

print("=" * 70)
print("🔍 图表数据显示问题诊断")
print("=" * 70)

# 测试物品列表
test_items = [
    "哮喘吸入器",
    "野战急救包",
    "战术快拆手术包",
    "M2 肌肉注射剂"
]

# Redis 连接
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

print(f"\n检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"服务器地址：http://82.156.116.206:5000")

for item_name in test_items:
    print(f"\n{'='*60}")
    print(f"物品：{item_name}")
    print(f"{'='*60}")
    
    # 1. 检查 Redis 中的数据
    history_key = f"trading:history:{item_name}"
    redis_count = r.zcard(history_key)
    
    if redis_count > 0:
        print(f"✅ Redis 历史记录：{redis_count} 条")
        
        # 获取第一条和最后一条记录
        first = r.zrange(history_key, 0, 0, withscores=True)[0]
        last = r.zrange(history_key, -1, -1, withscores=True)[0]
        
        try:
            first_date = datetime.fromtimestamp(int(float(first[1]))).strftime('%Y-%m-%d %H:%M')
            last_date = datetime.fromtimestamp(int(float(last[1]))).strftime('%Y-%m-%d %H:%M')
            
            print(f"   时间范围：{first_date} 至 {last_date}")
            print(f"   价格范围：{float(first[0]):.2f} - {float(last[0]):.2f} 哈弗币")
        except Exception as e:
            print(f"   时间戳格式异常：{e}")
            print(f"   原始数据：{first}, {last}")
    else:
        print(f"❌ Redis 中无历史记录")
        continue
    
    # 2. 检查 API 返回的数据
    try:
        api_url = f"http://localhost:5000/api/items/{item_name}/history?days=30"
        response = requests.get(api_url, timeout=5)
        
        if response.status_code == 200:
            api_data = response.json()
            api_count = len(api_data)
            
            print(f"✅ API 返回数据：{api_count} 条")
            
            if api_count > 0:
                first_record = api_data[0]
                last_record = api_data[-1]
                print(f"   第一条：{first_record.get('time', 'N/A')} - {first_record.get('price', 0):.2f}")
                print(f"   最后一条：{last_record.get('time', 'N/A')} - {last_record.get('price', 0):.2f}")
            
            # 对比 Redis 和 API
            if api_count < redis_count:
                print(f"⚠️  警告：API 返回的数据 ({api_count}条) 少于 Redis 中的数据 ({redis_count}条)")
                print(f"   可能原因：API 的 days 参数限制了返回的数据量")
            elif api_count == redis_count:
                print(f"✅ 数据一致性：良好")
        else:
            print(f"❌ API 请求失败：HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ API 请求异常：{e}")

# 总结
print(f"\n{'='*70}")
print("📊 诊断总结")
print(f"{'='*70}")
print("""
如果 Redis 中有数据但图表只显示一条，可能的原因：

1. **浏览器缓存问题** (最常见)
   解决方案：按 Ctrl+F5 强制刷新浏览器
   或清除浏览器缓存后重新访问

2. **JavaScript 代码错误**
   检查方法：打开浏览器开发者工具 (F12)
   查看 Console 标签是否有错误信息

3. **字段名不匹配**
   已修复：前端代码已更新为 d.time || d.date
   需要刷新浏览器才能生效

4. **Plotly 图表渲染问题**
   检查方法：在 Console 中输入以下命令查看数据
   console.log('历史数据:', historyData);
   console.log('日期数组:', dates);
   console.log('价格数组:', prices);

💡 建议操作步骤：
1. 打开 http://82.156.116.206:5000
2. 按 F12 打开开发者工具
3. 按 Ctrl+F5 强制刷新
4. 点击任意物品卡片
5. 查看 Console 中的日志输出
6. 确认 dates 和 prices 数组的长度是否正确
""")
print(f"{'='*70}\n")
