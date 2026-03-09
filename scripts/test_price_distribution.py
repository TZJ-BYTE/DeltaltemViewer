#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格分布图测试脚本
模拟前端 JavaScript 的价格区间计算逻辑
"""

def round_to_nice_number(num):
    """将数字圆整到美观的值"""
    if num <= 0:
        return 100
    
    import math
    magnitude = pow(10, math.floor(math.log10(num)))
    normalized = num / magnitude
    
    if normalized <= 1:
        nice_normalized = 1
    elif normalized <= 2:
        nice_normalized = 2
    elif normalized <= 5:
        nice_normalized = 5
    else:
        nice_normalized = 10
    
    return nice_normalized * magnitude

def format_number(num):
    """格式化数字（添加千位分隔符）"""
    return f"{num:,}"

def calculate_price_ranges(prices):
    """计算价格区间分布"""
    if not prices:
        print("❌ 价格数据为空")
        return
    
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price
    
    print(f"📊 价格数据统计")
    print(f"{'='*60}")
    print(f"最小值：{format_number(min_price)}")
    print(f"最大值：{format_number(max_price)}")
    print(f"价格范围：{format_number(price_range)}")
    print()
    
    # 确定区间数量
    num_ranges = 5
    if len(prices) > 20:
        num_ranges = 7
    if len(prices) > 30:
        num_ranges = 8
    
    # 计算区间大小
    range_size = round_to_nice_number(int(price_range / num_ranges))
    print(f"区间大小：{format_number(range_size)}")
    print(f"区间数量：{num_ranges}")
    print()
    
    # 计算实际范围
    actual_min = int(min_price / range_size) * range_size
    actual_max = int(max_price / range_size + 1) * range_size
    actual_ranges = int((actual_max - actual_min) / range_size)
    
    print(f"实际最小值：{format_number(actual_min)}")
    print(f"实际最大值：{format_number(actual_max)}")
    print(f"实际区间数：{actual_ranges}")
    print()
    
    # 生成区间标签
    range_labels = []
    for i in range(actual_ranges):
        start = actual_min + i * range_size
        end = start + range_size
        range_labels.append(f"{format_number(start)}-{format_number(end)}")
    
    # 统计每个区间的数量
    range_counts = [0] * actual_ranges
    for price in prices:
        index = int((price - actual_min) / range_size)
        if 0 <= index < actual_ranges:
            range_counts[index] += 1
        elif index >= actual_ranges:
            range_counts[actual_ranges - 1] += 1
    
    # 显示结果
    print(f"📈 价格区间分布")
    print(f"{'='*60}")
    print(f"{'区间':<30} {'数量':>10} {'柱状图'}")
    print(f"{'-'*60}")
    
    max_count = max(range_counts) if range_counts else 1
    for i, (label, count) in enumerate(zip(range_labels, range_counts)):
        bar_length = int(count / max_count * 20) if max_count > 0 else 0
        bar = "█" * bar_length
        print(f"{label:<30} {count:>10} {bar}")
    
    print(f"{'='*60}")
    print()

# 测试用例 1: 哮喘吸入器（高价值物品）
print("🧪 测试用例 1: 哮喘吸入器")
print("="*60)
asthma_prices = [
    65984.59, 66577.33, 69187.90, 70799.41, 71694.16, 71912.92,
    73778.43, 75810.91, 76333.19, 78918.05, 82354.65, 82583.00,
    84733.47, 86159.37, 86338.00, 86338.00, 86338.00, 86728.58,
    88028.14, 89165.87, 92243.81, 93848.00, 96252.19, 97861.03,
    98271.26, 100130.49, 105113.00, 110539.90, 112089.10
]
calculate_price_ranges(asthma_prices)

# 测试用例 2: 野战急救包（中等价值物品）
print("🧪 测试用例 2: 野战急救包")
print("="*60)
first_aid_prices = [
    8500, 8650, 8800, 9000, 9200, 9500, 9800, 10000,
    10200, 10500, 10800, 11000, 11200, 11500, 11800,
    12000, 12300, 12500, 12800, 13000, 13200, 13500
]
calculate_price_ranges(first_aid_prices)

# 测试用例 3: 低价值物品
print("🧪 测试用例 3: 低级材料")
print("="*60)
low_value_prices = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120]
calculate_price_ranges(low_value_prices)

print("✅ 所有测试完成！")
print()
print("💡 修复说明:")
print("1. 旧的固定区间 (0-5000) 无法显示高价值物品")
print("2. 新的动态区间根据实际数据自动调整")
print("3. 区间大小会自动圆整到美观的值 (如 100, 500, 1000 等)")
print("4. 所有物品都能正确显示多个价格区间")
