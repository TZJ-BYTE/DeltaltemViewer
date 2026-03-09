#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速生成历史数据脚本
一键为所有物品添加 30 天的随机波动历史数据
"""

import redis
import random
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_historical_prices(current_price, days=30, volatility=0.15):
    """
    生成历史价格序列（倒推法）
    
    参数:
    - current_price: 当前价格
    - days: 生成多少天的数据
    - volatility: 波动率 (0.15 = 15% 的日波动)
    
    返回:
    - [(timestamp, price), ...] 按时间排序
    """
    prices = []
    current = float(current_price)
    
    # 从今天往前推 days 天
    for i in range(days):
        timestamp = int(time.time()) - (i * 86400)  # 每天的秒数
        
        if i == 0:
            # 今天就是当前价格
            price = current
        else:
            # 随机波动：-volatility 到 +volatility
            change_rate = random.uniform(-volatility, volatility)
            price = current / (1 + change_rate)
            current = price
        
        # 确保价格为正数且保留 2 位小数
        price = max(1, round(price, 2))
        prices.append((timestamp, price))
    
    # 按时间正序排列（从旧到新）
    prices.reverse()
    return prices


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🎭 历史价格波动生成器 - 快速版")
    print("=" * 70)
    
    try:
        # 连接 Redis
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        redis_client.ping()
        logger.info("✓ Redis 连接成功")
        
        # 获取所有物品
        items = []
        for key in redis_client.scan_iter("trading:item:*"):
            item_data = redis_client.hgetall(key)
            if item_data and 'name' in item_data:
                items.append(item_data)
        
        logger.info(f"找到 {len(items)} 个物品")
        
        if not items:
            logger.warning("未找到任何物品数据，请先运行爬虫")
            return 1
        
        # 统计
        total_added = 0
        success_count = 0
        skip_count = 0
        
        start_time = time.time()
        
        # 遍历所有物品
        for i, item in enumerate(items, 1):
            item_name = item.get('name', '')
            current_price = item.get('price', 0)
            
            if not item_name or not current_price:
                skip_count += 1
                continue
            
            history_key = f"trading:history:{item_name}"
            
            # 检查是否已有足够的历史数据
            existing_count = redis_client.zcard(history_key)
            if existing_count > 5:  # 如果已有超过 5 条记录，跳过
                skip_count += 1
                continue
            
            try:
                current_price = float(current_price)
                
                # 生成 30 天的历史价格（15% 波动率）
                historical_prices = generate_historical_prices(
                    current_price, 
                    days=30, 
                    volatility=0.15
                )
                
                # 批量添加到 Redis Sorted Set
                pipe = redis_client.pipeline()
                for timestamp, price in historical_prices:
                    pipe.zadd(history_key, {str(timestamp): price})
                
                # 设置 30 天过期
                pipe.expire(history_key, 30 * 24 * 60 * 60)
                pipe.execute()
                
                total_added += len(historical_prices)
                success_count += 1
                
                # 显示进度
                if i % 50 == 0 or i == len(items):
                    progress = (i / len(items)) * 100
                    elapsed = time.time() - start_time
                    logger.info(f"进度：{i}/{len(items)} ({progress:.1f}%) | "
                               f"成功：{success_count} | 跳过：{skip_count} | "
                               f"记录：{total_added} | 耗时：{elapsed:.1f}s")
                
            except Exception as e:
                logger.error(f"处理 '{item_name}' 失败：{e}")
                skip_count += 1
        
        elapsed = time.time() - start_time
        
        # 输出结果
        print("\n" + "=" * 70)
        print("✅ 历史数据生成完成")
        print("=" * 70)
        print(f"总物品数：{len(items)}")
        print(f"成功处理：{success_count} 个")
        print(f"跳过：{skip_count} 个")
        print(f"新增历史记录：{total_added} 条")
        print(f"平均每个物品：{total_added/success_count:.1f} 条记录" if success_count > 0 else "N/A")
        print(f"总耗时：{elapsed:.2f} 秒")
        print(f"处理速度：{len(items)/elapsed:.1f} 个/秒")
        print("=" * 70)
        
        # 验证效果
        print("\n📊 抽样验证（前 5 个成功的物品）:")
        sample_keys = []
        for key in redis_client.scan_iter("trading:item:*"):
            if len(sample_keys) >= 5:
                break
            item_data = redis_client.hgetall(key)
            if item_data and 'name' in item_data:
                history_key = f"trading:history:{item_data['name']}"
                count = redis_client.zcard(history_key)
                if count > 0:
                    sample_keys.append((item_data['name'], count, float(item_data.get('price', 0))))
        
        for name, hist_count, curr_price in sample_keys:
            print(f"  • {name[:30]:<30} | 当前价：{curr_price:>8.2f} | 历史记录：{hist_count:>2}条")
        
        print("\n💡 提示：现在刷新网页，图表应该显示波动的价格曲线了！")
        print("=" * 70 + "\n")
        
        return 0
        
    except redis.ConnectionError as e:
        logger.error(f"Redis 连接失败：{e}")
        logger.error("请确保 Redis 服务正在运行")
        return 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  操作已中断")
        return 1
    
    except Exception as e:
        logger.error(f"程序执行失败：{e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
