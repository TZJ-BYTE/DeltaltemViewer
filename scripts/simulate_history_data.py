#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据波动生成脚本
为 Redis 中的物品历史价格数据添加随机波动，使图表更加真实可观
"""

import redis
import random
import time
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoryDataSimulator:
    """历史数据模拟器"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        """初始化 Redis 连接"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        
        # 验证连接
        try:
            self.redis_client.ping()
            logger.info(f"✓ Redis 连接成功 ({redis_host}:{redis_port})")
        except Exception as e:
            logger.error(f"✗ Redis 连接失败：{e}")
            raise
    
    def get_all_items(self):
        """获取所有物品列表"""
        items = []
        
        # 遍历所有 trading:item:* 键
        for key in self.redis_client.scan_iter("trading:item:*"):
            item_data = self.redis_client.hgetall(key)
            if item_data and 'name' in item_data:
                items.append(item_data)
        
        logger.info(f"找到 {len(items)} 个物品")
        return items
    
    def generate_historical_prices(self, current_price, days=30, volatility=0.15):
        """
        生成历史价格序列
        
        参数:
        - current_price: 当前价格
        - days: 生成多少天的数据
        - volatility: 波动率 (0.1 = 10% 的日波动)
        
        返回:
        - [(timestamp, price), ...] 按时间排序
        """
        prices = []
        
        # 从当前价格倒推
        current = current_price
        
        # 生成每天的价格（从今天往前推）
        for i in range(days):
            timestamp = int(time.time()) - (i * 86400)  # 每天的秒数
            
            if i == 0:
                # 今天就是当前价格
                price = current_price
            else:
                # 随机波动：-volatility 到 +volatility
                change_rate = random.uniform(-volatility, volatility)
                price = current / (1 + change_rate)
                current = price
            
            # 确保价格为正数且合理
            price = max(1, round(price, 2))
            prices.append((timestamp, price))
        
        # 按时间正序排列
        prices.reverse()
        return prices
    
    def add_history_to_item(self, item_name, current_price, days=30, volatility=0.15):
        """
        为单个物品添加历史数据
        
        参数:
        - item_name: 物品名称
        - current_price: 当前价格
        - days: 历史天数
        - volatility: 波动率
        """
        try:
            history_key = f"trading:history:{item_name}"
            
            # 检查是否已有历史数据
            existing_count = self.redis_client.zcard(history_key)
            
            if existing_count > 1:
                logger.debug(f"物品 '{item_name}' 已有 {existing_count} 条历史数据，跳过")
                return 0
            
            # 生成历史价格
            historical_prices = self.generate_historical_prices(
                current_price, 
                days=days, 
                volatility=volatility
            )
            
            # 添加到 Redis Sorted Set
            pipe = self.redis_client.pipeline()
            for timestamp, price in historical_prices:
                pipe.zadd(history_key, {str(timestamp): price})
            
            # 设置过期时间（30 天）
            pipe.expire(history_key, 30 * 24 * 60 * 60)
            pipe.execute()
            
            logger.info(f"✓ 已为 '{item_name}' 添加 {len(historical_prices)} 条历史价格记录")
            return len(historical_prices)
            
        except Exception as e:
            logger.error(f"为物品 '{item_name}' 添加历史数据失败：{e}")
            return 0
    
    def simulate_all_items(self, days=30, volatility=0.15, limit=None):
        """
        为所有物品模拟历史数据
        
        参数:
        - days: 历史天数
        - volatility: 波动率
        - limit: 限制处理的物品数量（None 表示全部）
        """
        logger.info("=" * 60)
        logger.info("开始为物品添加历史价格数据")
        logger.info(f"参数：历史天数={days}, 波动率={volatility*100:.0f}%")
        logger.info("=" * 60)
        
        items = self.get_all_items()
        
        if limit:
            items = items[:limit]
            logger.info(f"限制处理前 {limit} 个物品")
        
        total_added = 0
        success_count = 0
        skip_count = 0
        
        start_time = time.time()
        
        for i, item in enumerate(items, 1):
            item_name = item.get('name', '')
            current_price = item.get('price', 0)
            
            if not item_name or not current_price:
                logger.warning(f"第 {i} 个物品数据不完整，跳过")
                skip_count += 1
                continue
            
            try:
                current_price = float(current_price)
                
                # 添加历史数据
                added = self.add_history_to_item(
                    item_name, 
                    current_price, 
                    days=days, 
                    volatility=volatility
                )
                
                if added > 0:
                    total_added += added
                    success_count += 1
                
                # 显示进度
                if i % 50 == 0 or i == len(items):
                    progress = (i / len(items)) * 100
                    elapsed = time.time() - start_time
                    logger.info(f"进度：{i}/{len(items)} ({progress:.1f}%), "
                               f"成功：{success_count}, 跳过：{skip_count}, "
                               f"总记录：{total_added}, 耗时：{elapsed:.1f}s")
                
            except Exception as e:
                logger.error(f"处理物品 '{item_name}' 时出错：{e}")
                skip_count += 1
        
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info("✅ 历史数据模拟完成")
        logger.info(f"总计：{len(items)} 个物品")
        logger.info(f"成功：{success_count} 个，跳过：{skip_count} 个")
        logger.info(f"新增历史价格记录：{total_added} 条")
        logger.info(f"总耗时：{elapsed:.2f} 秒")
        logger.info(f"平均速度：{len(items)/elapsed:.1f} 个/秒")
        logger.info("=" * 60)
        
        return {
            'total_items': len(items),
            'success': success_count,
            'skipped': skip_count,
            'total_records': total_added,
            'elapsed_seconds': elapsed
        }
    
    def clear_all_history(self):
        """清空所有历史数据"""
        logger.warning("准备清空所有历史数据...")
        
        count = 0
        for key in self.redis_client.scan_iter("trading:history:*"):
            self.redis_client.delete(key)
            count += 1
        
        logger.info(f"✓ 已清空 {count} 个物品的历史数据")
        return count
    
    def check_history_stats(self):
        """检查历史数据统计"""
        logger.info("\n" + "=" * 60)
        logger.info("历史数据统计信息")
        logger.info("=" * 60)
        
        total_items = 0
        items_with_history = 0
        total_records = 0
        
        items_without_history = []
        
        for key in self.redis_client.scan_iter("trading:item:*"):
            item_data = self.redis_client.hgetall(key)
            if item_data and 'name' in item_data:
                total_items += 1
                
                history_key = f"trading:history:{item_data['name']}"
                history_count = self.redis_client.zcard(history_key)
                
                if history_count > 0:
                    items_with_history += 1
                    total_records += history_count
                else:
                    items_without_history.append(item_data['name'])
        
        coverage = (items_with_history / total_items * 100) if total_items > 0 else 0
        
        logger.info(f"总物品数：{total_items}")
        logger.info(f"有历史数据的物品：{items_with_history} ({coverage:.1f}%)")
        logger.info(f"无历史数据的物品：{total_items - items_with_history}")
        logger.info(f"历史价格记录总数：{total_records}")
        logger.info(f"平均每个物品的历史记录数：{total_records/items_with_history:.1f}" if items_with_history > 0 else "N/A")
        
        if items_without_history and len(items_without_history) <= 20:
            logger.info(f"\n缺少历史数据的物品示例 (最多 20 个):")
            for name in items_without_history[:20]:
                logger.info(f"  - {name}")
        
        logger.info("=" * 60)
        
        return {
            'total_items': total_items,
            'items_with_history': items_with_history,
            'coverage_percent': coverage,
            'total_records': total_records
        }


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🎭 历史价格波动模拟器")
    print("=" * 60)
    
    try:
        # 创建模拟器实例
        simulator = HistoryDataSimulator()
        
        # 检查当前状态
        stats = simulator.check_history_stats()
        
        # 询问用户操作
        print("\n请选择操作:")
        print("1. 为所有物品生成历史数据（推荐）")
        print("2. 清空所有历史数据")
        print("3. 仅检查统计信息")
        
        choice = input("\n请输入选项 (1/2/3): ").strip()
        
        if choice == '1':
            # 生成历史数据
            days_input = input("历史天数 (默认 30): ").strip()
            days = int(days_input) if days_input else 30
            
            volatility_input = input("波动率 0.05-0.30 (默认 0.15 = 15%): ").strip()
            volatility = float(volatility_input) if volatility_input else 0.15
            
            limit_input = input("限制处理数量 (直接回车表示全部): ").strip()
            limit = int(limit_input) if limit_input else None
            
            print(f"\n开始生成历史数据...")
            print(f"参数：{days}天，波动率 {volatility*100:.0f}%")
            
            if limit:
                confirm = input(f"确定要处理前 {limit} 个物品吗？(y/n): ").strip().lower()
                if confirm != 'y':
                    print("已取消")
                    return
            
            simulator.simulate_all_items(days=days, volatility=volatility, limit=limit)
            
            # 完成后再次检查
            simulator.check_history_stats()
            
        elif choice == '2':
            confirm = input("⚠️  确定要清空所有历史数据吗？此操作不可恢复！(y/n): ").strip().lower()
            if confirm == 'y':
                simulator.clear_all_history()
                simulator.check_history_stats()
            else:
                print("已取消")
        
        elif choice == '3':
            simulator.check_history_stats()
        
        else:
            print("无效的选项")
    
    except KeyboardInterrupt:
        print("\n\n操作已中断")
    
    except Exception as e:
        logger.error(f"程序执行失败：{e}", exc_info=True)
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
