#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一数据服务模块
负责数据的存储、加载、分类等核心功能
避免爬虫和 Web 应用重复实现相同逻辑
"""

import json
import os
import redis
import time
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional, Union
from app.services.item_classifier import classifier
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataService:
    """统一数据服务类"""
    
    def __init__(self, data_dir="trading_price_data"):
        self.data_dir = data_dir
        self.redis_client = None
        self._setup_storage()
    
    def _setup_storage(self):
        """设置存储系统"""
        # Redis连接配置
        redis_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'db': int(os.getenv('REDIS_DB', 0)),
            'password': os.getenv('REDIS_PASSWORD', None),
            'socket_connect_timeout': 5,
            'socket_timeout': 5,
            'decode_responses': True,
            'retry_on_timeout': True,
            'health_check_interval': 30
        }
        
        try:
            self.redis_client = redis.Redis(**redis_config)
            self.redis_client.ping()
            logger.info(f"✓ Redis连接成功 ({redis_config['host']}:{redis_config['port']})")
        except Exception as e:
            logger.warning(f"✗ Redis连接失败: {e}")
            logger.info("将使用文件存储作为备用方案")
            self.redis_client = None
    
    def save_trading_data(self, category: str, trading_data: Dict) -> bool:
        """保存交易数据（统一接口）- 优化后的版本"""
        if self.redis_client:
            return self._save_to_redis_optimized(category, trading_data)
        else:
            return self._save_to_file(category, trading_data)
    
    def load_trading_data(self) -> List[Dict]:
        """加载交易数据（仅从 Redis 加载）"""
        if self.redis_client:
            # 优先使用优化版本加载数据
            items_data = self._load_from_redis_optimized()
            if items_data:
                return items_data
            
            # 如果优化版本未找到数据，尝试旧版本
            logger.info("优化版本未找到数据，尝试旧版本...")
            return self._load_from_redis()
        else:
            logger.warning("Redis 未连接，无法加载数据")
            return []
    
    def get_statistics(self) -> Dict:
        """获取数据统计信息（仅从 Redis 获取）"""
        if self.redis_client:
            # 优先使用优化统计
            stats = self._get_redis_stats_optimized()
            # 如果优化版本没有数据，回退到旧版本
            if stats.get('total_items', 0) == 0:
                return self._get_redis_stats()
            return stats
        else:
            logger.warning("Redis 未连接，无法获取统计数据")
            return {'storage_type': 'Redis', 'error': 'Redis 未连接', 'total_items': 0}
    
    def classify_item(self, item_name: str) -> str:
        """统一物品分类接口"""
        return classifier.classify(item_name)
    
    def _save_to_redis(self, category: str, trading_data: Dict) -> bool:
        """保存数据到 Redis（旧版本，保留用于兼容）"""
        try:
            import time
            timestamp = int(time.time())
            key = f"trading_data:{category}:{timestamp}"
                
            # 保存数据
            data_json = json.dumps(trading_data, ensure_ascii=False)
            self.redis_client.set(key, data_json)
            self.redis_client.expire(key, 7 * 24 * 60 * 60)  # 7 天过期
                
            # 保存元数据
            metadata = {
                'timestamp': timestamp,
                'category': category,
                'items_count': len(trading_data.get('items', [])),
                'url': trading_data.get('url', ''),
                'crawl_time': trading_data.get('crawl_time', '')
            }
            metadata_key = f"metadata:{key}"
            self.redis_client.set(metadata_key, json.dumps(metadata, ensure_ascii=False))
            self.redis_client.expire(metadata_key, 7 * 24 * 60 * 60)
                
            logger.info(f"✓ 已保存到 Redis: {key} (共{metadata['items_count']}个物品)")
            return True
                
        except Exception as e:
            logger.error(f"Redis 保存失败：{e}")
            return False
        
    def _save_to_redis_optimized(self, category: str, trading_data: Dict) -> bool:
        """优化后的 Redis 存储方法 - 支持历史价格记录"""
        try:
            import time
            timestamp = int(time.time())
            crawl_time = trading_data.get('crawl_time', time.strftime('%Y-%m-%d %H:%M:%S'))
            items = trading_data.get('items', [])
                
            if not items:
                logger.warning("没有物品数据需要保存")
                return False
                
            # 1. 按物品分类存储（每个物品一个 key，便于查询和更新）
            saved_items = 0
            price_changes = 0  # 记录价格变化次数
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                # 处理物品数据
                processed_item = self._process_item(item, crawl_time)
                if not processed_item or not processed_item['name']:
                    continue
                    
                item_name = processed_item['name']
                item_category = processed_item['category']
                    
                # 单个物品的 key：trading:item:{category}:{item_name}
                item_key = f"trading:item:{item_category}:{item_name}"
                
                # 使用该物品的实际分类创建索引键
                category_index_key = f"trading:index:{item_category}"
                    
                # 获取上次爬取的价格
                old_price = None
                if self.redis_client.exists(item_key):
                    old_price = self.redis_client.hget(item_key, 'price')
                    
                # 构建物品数据哈希
                item_data = {
                    'name': item_name,
                    'price': processed_item['price'],
                    'currency': processed_item['currency'],
                    'category': item_category,
                    'source': '交易行',
                    'crawl_time': crawl_time,
                    'image_url': processed_item.get('image_url', ''),
                    'update_timestamp': timestamp
                }
                    
                # 使用 Hash 存储，节省空间且便于更新
                self.redis_client.hset(item_key, mapping=item_data)
                self.redis_client.expire(item_key, 30 * 24 * 60 * 60)  # 30 天过期
                    
                # 添加到分类索引（Set 类型）
                self.redis_client.sadd(category_index_key, item_name)
                self.redis_client.expire(category_index_key, 30 * 24 * 60 * 60)
                    
                # 如果价格变化，记录历史
                if old_price is None or float(old_price) != float(processed_item['price']):
                    history_key = f"trading:history:{item_name}"
                    # 添加到 Sorted Set (timestamp -> price)
                    self.redis_client.zadd(history_key, {str(timestamp): float(processed_item['price'])})
                    self.redis_client.expire(history_key, 30 * 24 * 60 * 60)  # 保留 30 天
                    price_changes += 1
                    
                saved_items += 1
                
            # 2. 保存完整快照（用于备份和历史记录）
            snapshot_key = f"trading:snapshot:{timestamp}"
            snapshot_data = {
                'timestamp': timestamp,
                'crawl_time': crawl_time,
                'category': category,
                'items_count': saved_items,
                'url': trading_data.get('url', ''),
                'data': json.dumps(items, ensure_ascii=False)
            }
            self.redis_client.hset(snapshot_key, mapping=snapshot_data)
            self.redis_client.expire(snapshot_key, 30 * 24 * 60 * 60)
                
            # 3. 更新最后时间戳
            self.redis_client.set('trading:meta:last_update', str(timestamp))
            self.redis_client.expire('trading:meta:last_update', 30 * 24 * 60 * 60)
                
            # 4. 更新分类统计
            stats_key = f"trading:stats:{category}"
            self.redis_client.hincrby(stats_key, 'total_updates', 1)
            self.redis_client.hset(stats_key, 'last_update_time', crawl_time)
            self.redis_client.hset(stats_key, 'last_items_count', saved_items)
            self.redis_client.expire(stats_key, 30 * 24 * 60 * 60)
                
            logger.info(f"✓ 已优化保存到 Redis：{saved_items}个物品，分类：{category}")
            logger.info(f"   - 价格变化：{price_changes}个物品")
            return True
                
        except Exception as e:
            logger.error(f"Redis 优化保存失败：{e}", exc_info=True)
            return False
    
    def _save_to_file(self, category: str, trading_data: Dict) -> bool:
        """保存数据到文件"""
        try:
            import time
            # 创建目录
            category_dir = os.path.join(self.data_dir, self._get_safe_filename(category))
            os.makedirs(category_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = int(time.time())
            filename = f"trading_data_{timestamp}.json"
            filepath = os.path.join(category_dir, filename)
            
            # 保存数据
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(trading_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ 已保存交易数据: {category}/{filename}")
            return True
        except Exception as e:
            logger.error(f"文件保存失败: {e}")
            return False
    
    def _load_from_redis(self) -> List[Dict]:
        """从Redis加载数据"""
        items_data = []
        try:
            keys = self.redis_client.keys("trading_data:*")
            if not keys:
                logger.warning("Redis中未找到交易数据")
                return items_data
            
            logger.info(f"从Redis找到 {len(keys)} 条数据记录")
            
            # 按时间戳排序，获取最新的数据
            sorted_keys = sorted(keys, key=lambda k: int(k.split(':')[-1]), reverse=True)
            
            for key in sorted_keys:
                try:
                    data_json = self.redis_client.get(key)
                    if data_json:
                        data = json.loads(data_json)
                        items = data.get('items', [])
                        
                        for item in items:
                            if isinstance(item, dict):
                                processed_item = self._process_item(item, data.get('crawl_time', ''))
                                if processed_item and processed_item['name']:
                                    items_data.append(processed_item)
                except Exception as e:
                    logger.error(f"处理Redis数据失败 {key}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Redis数据加载异常: {e}")
        
        return items_data
    
    def _load_from_files(self) -> List[Dict]:
        """从文件加载数据"""
        items_data = []
        
        if not os.path.exists(self.data_dir):
            logger.warning(f"数据目录不存在: {self.data_dir}")
            return items_data
        
        # 优先加载改进后的数据文件
        improved_data_file = os.path.join(self.data_dir, '交易行数据', 'improved_fixed_trading_data.json')
        if os.path.exists(improved_data_file):
            items_data.extend(self._load_improved_data(improved_data_file))
            return items_data
        
        # 其次尝试加载修复数据
        fixed_data_file = os.path.join(self.data_dir, '交易行数据', 'fixed_trading_data.json')
        if os.path.exists(fixed_data_file):
            items_data.extend(self._load_fixed_data(fixed_data_file))
            return items_data
        
        # 最后使用原始文件
        items_data.extend(self._load_raw_files())
        return items_data
    
    def _load_improved_data(self, filepath: str) -> List[Dict]:
        """加载改进后的数据"""
        items_data = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data.get('items', [])
                
                for item in items:
                    if isinstance(item, dict):
                        processed_item = {
                            'name': item.get('物品', ''),
                            'price': int(item.get('价格', 0)),
                            'currency': '哈弗币',
                            'quantity': 1,
                            'category': item.get('分类', '其他'),
                            'source': '交易行',
                            'crawl_time': data.get('timestamp', ''),
                            'raw_data': item,
                            'image_url': item.get('image_url', '')
                        }
                        if processed_item['name']:
                            items_data.append(processed_item)
        except Exception as e:
            logger.error(f"读取改进文件失败 {filepath}: {e}")
        return items_data
    
    def _load_fixed_data(self, filepath: str) -> List[Dict]:
        """加载修复后的数据"""
        items_data = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data.get('items', [])
                
                for item in items:
                    if isinstance(item, dict):
                        processed_item = {
                            'name': item.get('物品', ''),
                            'price': float(item.get('价格', 0)),
                            'currency': '哈弗币',
                            'quantity': 1,
                            'category': item.get('分类', '其他'),
                            'source': '交易行',
                            'crawl_time': data.get('timestamp', ''),
                            'raw_data': item,
                            'image_url': ''
                        }
                        if processed_item['name']:
                            items_data.append(processed_item)
        except Exception as e:
            logger.error(f"读取修复文件失败 {filepath}: {e}")
        return items_data
    
    def _load_raw_files(self) -> List[Dict]:
        """加载原始数据文件"""
        items_data = []
        file_count = 0
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                if file.startswith('trading_data_') and file.endswith('.json'):
                    file_count += 1
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            items = data.get('items', [])
                            
                            for item in items:
                                if isinstance(item, dict):
                                    processed_item = self._process_item(item, data.get('crawl_time', ''))
                                    if processed_item:
                                        items_data.append(processed_item)
                    except Exception as e:
                        logger.error(f"读取文件失败 {filepath}: {e}")
        return items_data
    
    def _process_item(self, item: Dict, crawl_time: str) -> Optional[Dict]:
        """处理单个物品数据 - 直接使用爬虫提供的分类"""
        processed = {
            'name': '',
            'price': 0,
            'currency': '哈弗币',
            'quantity': 1,
            'category': '未知',
            'source': '交易行',
            'crawl_time': crawl_time,
            'raw_data': item,
            'image_url': item.get('image_url', '')
        }
        
        # 提取物品名称
        name_fields = ['物品', '名称', 'name', '商品', 'item']
        for field in name_fields:
            if field in item and item[field]:
                raw_name = str(item[field]).strip()
                # 清洗物品名称，去除多余后缀
                processed['name'] = self._clean_item_name(raw_name)
                break
        
        # 提取价格
        import re
        price_fields = ['价格', 'price', '售价', 'cost', '金额', '当前价格']
        for field in price_fields:
            if field in item and item[field]:
                price_info = str(item[field])
                # 处理模板字符串 {{NumQfw(981424)}}
                template_match = re.search(r'\{\{NumQfw\((\d+(?:\.\d+)?)\)\}\}', price_info)
                if template_match:
                    processed['price'] = int(float(template_match.group(1)))
                    processed['currency'] = '哈弗币'
                    break
                else:
                    # 提取普通数字价格（支持带逗号的格式，如 30,467,068）
                    # 先移除所有逗号
                    price_clean = price_info.replace(',', '')
                    # 然后提取数字
                    price_match = re.search(r'(\d+(?:\.\d+)?)', price_clean)
                    if price_match:
                        processed['price'] = int(float(price_match.group(1)))
                        break
        
        # 直接使用爬虫提供的分类字段
        category_fields = ['分类', 'category', '类别']
        for field in category_fields:
            if field in item and item[field]:
                processed['category'] = str(item[field]).strip()
                break
        
        return processed if (processed['name'] and processed['price'] > 0) else None
    
    def _clean_item_name(self, raw_name: str) -> str:
        """清洗物品名称，去除多余后缀"""
        if not raw_name:
            return ''
        
        name = raw_name.strip()
        
        # 定义需要去除的后缀模式
        suffix_patterns = [
            # 推荐方式后缀
            (' 推荐方式：', None),
            (' 推荐方式:', None),
            # 品质后缀
            (' 品质：', None),
            (' 品质:', None),
            # 等级后缀
            (' 等级：', None),
            (' 等级:', None),
        ]
        
        # 依次检查并去除后缀
        for start_pattern, end_pattern in suffix_patterns:
            if start_pattern in name:
                # 找到后缀开始位置
                start_index = name.find(start_pattern)
                
                # 如果有结束符，找到结束位置
                if end_pattern:
                    end_index = name.find(end_pattern, start_index)
                    if end_index != -1:
                        name = name[:start_index] + name[end_index + len(end_pattern):]
                else:
                    # 没有结束符，直接截断到末尾
                    name = name[:start_index]
        
        # 处理中文括号（...）和英文括号 (...) 的情况
        import re
        # 匹配 (...)/(...) 并移除
        name = re.sub(r'[（(][^）)]*[）)]', '', name)
        
        # 再次清理可能的多重后缀和空白字符
        name = name.strip()
        
        # 去除末尾的冒号、空格等
        while name and name[-1] in ['：', ':', ' ', '（', '(']:
            name = name[:-1]
        
        return name.strip()
    
    def _get_redis_stats(self) -> Dict:
        """获取 Redis 统计信息（旧版本）"""
        try:
            trading_keys = self.redis_client.keys("trading_data:*")
            metadata_keys = self.redis_client.keys("metadata:trading_data:*")
                
            total_items = 0
            categories = defaultdict(int)
                
            for key in trading_keys:
                try:
                    data_json = self.redis_client.get(key)
                    if data_json:
                        data = json.loads(data_json)
                        items = data.get('items', [])
                        total_items += len(items)
                            
                        for item in items:
                            if isinstance(item, dict):
                                category = item.get('category', '未知')
                                categories[category] += 1
                except Exception as e:
                    continue
                
            return {
                'storage_type': 'Redis',
                'total_records': len(trading_keys),
                'total_items': total_items,
                'categories': dict(categories),
                'metadata_records': len(metadata_keys)
            }
        except Exception as e:
            logger.error(f"Redis 统计获取失败：{e}")
            return {'storage_type': 'Redis', 'error': str(e)}
        
    def _get_redis_stats_optimized(self) -> Dict:
        """获取优化后的 Redis 统计信息"""
        try:
            stats = {
                'storage_type': 'Redis (Optimized)',
                'categories': {},
                'total_items': 0,
                'last_update': None
            }
                
            # 获取最后更新时间
            last_update = self.redis_client.get('trading:meta:last_update')
            if last_update:
                stats['last_update'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(last_update)))
                
            # 遍历所有分类索引
            index_keys = self.redis_client.keys("trading:index:*")
            for index_key in index_keys:
                # 提取分类名称
                parts = index_key.split(':')
                if len(parts) >= 3:
                    category = ':'.join(parts[2:])  # 支持中文分类名
                        
                    # 获取该分类下的物品数量
                    item_count = self.redis_client.scard(index_key)
                    stats['categories'][category] = item_count
                    stats['total_items'] += item_count
                        
                    # 获取分类统计
                    cat_stats_key = f"trading:stats:{category}"
                    cat_stats = self.redis_client.hgetall(cat_stats_key)
                    if cat_stats:
                        stats[f'{category}_updates'] = cat_stats.get('total_updates', '0')
                
            return stats
        except Exception as e:
            logger.error(f"Redis 优化统计获取失败：{e}")
            return {'storage_type': 'Redis (Optimized)', 'error': str(e)}
    
    def _get_file_stats(self) -> Dict:
        """获取文件统计信息"""
        try:
            total_items = 0
            categories = defaultdict(int)
            
            for root, dirs, files in os.walk(self.data_dir):
                for file in files:
                    if file.startswith('trading_data_') and file.endswith('.json'):
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                items = data.get('items', [])
                                total_items += len(items)
                                
                                for item in items:
                                    if isinstance(item, dict):
                                        category = item.get('category', '未知')
                                        categories[category] += 1
                        except Exception as e:
                            continue
            
            return {
                'storage_type': 'File',
                'total_items': total_items,
                'categories': dict(categories),
                'data_directory': self.data_dir
            }
        except Exception as e:
            logger.error(f"文件统计获取失败: {e}")
            return {'storage_type': 'File', 'error': str(e)}
    
    def _get_safe_filename(self, text: str) -> str:
        """生成安全的文件名"""
        import re
        safe_text = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', text)
        return safe_text[:50] if len(safe_text) > 50 else safe_text
    
    def _load_from_redis_optimized(self) -> List[Dict]:
        """从 Redis 优化加载数据 - 按分类索引加载"""
        items_data = []
        try:
            # 获取所有分类索引
            index_keys = self.redis_client.keys("trading:index:*")
            if not index_keys:
                logger.warning("Redis 中未找到分类索引")
                return items_data
            
            logger.info(f"找到 {len(index_keys)} 个分类索引")
            
            # 遍历每个分类
            for index_key in index_keys:
                try:
                    # 从索引键中提取分类名称
                    parts = index_key.split(':')
                    if len(parts) >= 3:
                        category = ':'.join(parts[2:])  # 支持分类名中包含冒号
                    else:
                        logger.warning(f"无效的索引键格式：{index_key}")
                        continue
                    
                    # 从 Set 中获取该分类下的所有物品名称
                    item_names = self.redis_client.smembers(index_key)
                    
                    for item_name in item_names:
                        # 直接从该分类的 Hash 中获取物品数据
                        item_key = f"trading:item:{category}:{item_name}"
                        if self.redis_client.exists(item_key):
                            item_data = self.redis_client.hgetall(item_key)
                            if item_data:
                                # 转换数据类型
                                processed_item = {
                                    'name': item_data.get('name', ''),
                                    'price': int(float(item_data.get('price', 0))),
                                    'currency': item_data.get('currency', '哈弗币'),
                                    'quantity': 1,
                                    'category': item_data.get('category', category),
                                    'source': '交易行',
                                    'crawl_time': item_data.get('crawl_time', ''),
                                    'raw_data': {},
                                    'image_url': item_data.get('image_url', '')
                                }
                                if processed_item['name'] and processed_item['price'] > 0:
                                    items_data.append(processed_item)
                except Exception as e:
                    logger.error(f"处理分类索引失败 {index_key}: {e}")
                    continue
            
            logger.info(f"优化加载完成，共 {len(items_data)} 个物品")
                    
        except Exception as e:
            logger.error(f"Redis 优化数据加载异常：{e}")
        
        return items_data

    def get_price_history(self, item_name: str, days: int = 7) -> List[Dict]:
        """获取物品的历史价格数据"""
        try:
            if not self.redis_client:
                return []
            
            history_key = f"trading:history:{item_name}"
            
            # 检查 key 是否存在
            if not self.redis_client.exists(history_key):
                logger.warning(f"历史数据 key 不存在：{history_key}")
                return []
            
            # 获取所有历史记录（不限制时间范围）
            # 因为 Redis Sorted Set 的 score 是字符串类型的时间戳，需要用 zrange
            history_data = self.redis_client.zrange(history_key, 0, -1, withscores=True)
            
            logger.debug(f"从 Redis 获取 {len(history_data)} 条历史记录")
            
            if not history_data:
                logger.warning(f"历史数据为空：{history_key}")
                return []
            
            # 转换为前端可用格式
            result = []
            for timestamp_str, price in history_data:
                try:
                    # 将字符串时间戳转换为整数
                    timestamp = int(float(timestamp_str))
                    result.append({
                        'time': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M'),
                        'price': price,
                        'timestamp': timestamp
                    })
                except Exception as e:
                    logger.error(f"时间戳转换失败：{timestamp_str}, {e}")
                    continue
            
            # 按时间排序（从旧到新）
            result.sort(key=lambda x: x['timestamp'])
            
            logger.debug(f"转换后 {len(result)} 条记录")
            
            # 如果指定了天数，过滤最近的数据
            if days and days > 0:
                now = int(time.time())
                start_time = now - (days * 24 * 60 * 60)
                logger.debug(f"时间过滤：now={now}, start_time={start_time}, days={days}")
                
                filtered = [r for r in result if r['timestamp'] >= start_time]
                logger.debug(f"过滤后 {len(filtered)} 条记录")
                result = filtered
            
            return result
            
        except Exception as e:
            logger.error(f"获取价格历史失败：{e}", exc_info=True)
            return []

# 全局数据服务实例
data_service = DataService()