#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的物品分类模块
提供一致的分类逻辑供所有模块使用
"""

import re

class ItemClassifier:
    """物品分类器 - 基于精确物品名称哈希表的分类"""
    
    def __init__(self):
        # 精确物品名称到分类的映射表（最高优先级）
        self.exact_item_mapping = {
            # 消耗品类
            '自制护甲维修包': '消耗品',
            '自制头盔维修包': '消耗品',
            '车载急救包': '消耗品',
            '战术快拆手术包': '消耗品',
            '强效注射器': '消耗品',
            '简易注射器': '消耗品',
            '弹性绷带': '消耗品',
            'CAT止血带': '消耗品',
            '去甲肾上腺素': '消耗品',
            '缓释止痛片': '消耗品',
            
            # 钥匙类
            '酒店方片房': '钥匙',
            '顶层办公室': '钥匙',
            '检查站库房': '钥匙',
            '雷达站会议室': '钥匙',
            '中心贵宾室': '钥匙',
            '监控室': '钥匙',
            '档案室': '钥匙',
            '实验室': '钥匙',
            '武器库': '钥匙',
            '指挥中心': '钥匙',
            '通讯室': '钥匙',
            '医疗室': '钥匙',
            '休息室': '钥匙',
            '储藏室': '钥匙',
            '电梯控制室': '钥匙',
            '发电机房': '钥匙',
            '通风系统': '钥匙',
            '安全通道': '钥匙',
            
            # 弹药类
            '7.62x39mm PS': '弹药',
            '9x19mm AP6.3': '弹药',
            '5.45x39mm PS': '弹药',
            '5.56x45mm SS109': '弹药',
            '7.62x51mm FMJ': '弹药',
            '9x39mm SP5': '弹药',
            '12.7x55mm STs-130': '弹药',
            '5.7x28mm L191': '弹药',
            '4.6x30mm FMJ': '弹药',
            
            # 收集品类
            '渡鸦项坠': '收集品',
            '特种钢': '收集品',
            '扑克牌-2': '收集品',
            '古老的海盗望远镜': '收集品',
            '扑克牌-大王': '收集品',
            '古老的地图碎片': '收集品',
            '神秘的徽章': '收集品',
            '珍贵的邮票': '收集品',
            '古董怀表': '收集品',
            
            # 其他类
            '犄角墙饰': '收集品',
            '格赫罗斯的审判': '钥匙',
            '蓝室数据中心': '钥匙',
            '红色紧急按钮': '其他',
            '废弃的终端设备': '收集品',
            '破损的显示器': '收集品',
            '生锈的金属零件': '收集品',
            '老旧的电路板': '收集品',
            '损坏的传感器': '收集品',
            '断裂的光纤': '收集品',
            '腐蚀的芯片': '收集品',
            '失效的电池': '收集品'
        }
        
        # 原有的关键词分类规则（后备方案）
        self.classification_rules = {
            # 第一优先级：明确的钥匙相关关键词
            'key_keywords': [
                '钥匙', '侧门钥匙', '房卡', '通行证', '门禁卡'
            ],
            
            # 第二优先级：房间设施名称（统一归类为钥匙）
            'room_names': [
                '酒店方片房', '酒店将军房', '酒店王子房', '中心贵宾室',
                '雷达站数据中心', '雷达站控制室', '雷达站会议室',
                '铁脊车站售票室', '生物数据机房', '实验楼资料室',
                '检查站库房', '水泥厂办公室', '顶层办公间', '实验楼办公室',
                '运输机会议室', '中控室三楼'
            ],
            
            # 第三优先级：消耗品关键词
            'consumable_keywords': [
                '急救包', '止血带', '绷带', '注射器', '抗生素', '强化剂',
                '医疗', '药品', '治疗', '维修包', '修理包', '维护包',
                '手术包', 'cat', '车载', '简易', '强效', '体能'
            ],
            
            # 第四优先级：收集品关键词
            'collection_keywords': [
                '扑克牌', '特种钢', '聚乙烯纤维', '海盗望远镜', '渡鸦项坠',
                '处理器', '电台', '碳纤维', '非洲之心', '海洋',
                '古董', '收藏', '纪念品', '文物', '箭矢', '柳叶', '散射'
            ],
            
            # 第五优先级：装备类关键词
            'equipment_keywords': [
                '防弹衣', '头盔', '护甲', '背包', '战术背心', '夜视仪',
                '防毒面具', '战术手套', '战术靴', '防护装备',
                'ha-2', 'level', 'armor', 'helmet', 'vest'
            ],
            
            # 第七优先级：枪械类关键词
            'weapon_keywords': [
                '枪', '步枪', '狙击', '冲锋', '手枪', '霰弹', '榴弹',
                'ak', 'm4', 'scar', 'g36', 'aug', 'qbz', '95',
                'awm', 'm24', 'kar98', 'svd', 'mk14',
                'mp5', 'ump', 'vector', 'p90',
                'glock', 'm9', 'usp', 'p226', 'beretta'
            ],
            
            # 第六优先级：配件类关键词
            'accessory_keywords': [
                '瞄准镜', '瞄具', '握把', '枪口', '弹匣', '枪托', '激光',
                'scope', 'grip', 'muzzle', 'magazine', 'stock', 'laser',
                '倍镜', '红点', '全息', '消音器', '补偿器', '枪管'
            ],
            
            # 第八优先级：弹药类关键词
            'ammo_keywords': [
                '子弹', '弹药', 'ammo', 'bullet', '弹夹', '弹链',
                '5.56', '7.62', '9mm', '12.7', '手雷', '榴弹'
            ]
        }
    
    def classify(self, item_name):
        """
        根据物品名称进行分类
        优先使用精确物品名称映射，后备使用关键词规则
        """
        if not item_name:
            return '其他'
        
        # 1. 首先检查精确物品名称映射（最高优先级）
        clean_name = item_name.split('推荐方式')[0].strip()  # 移除推荐方式文案
        if clean_name in self.exact_item_mapping:
            return self.exact_item_mapping[clean_name]
        
        # 2. 统一转换为小写进行比较（保持中文字符不变）
        name_lower = item_name.lower()
        
        # 3. 按原有优先级顺序检查分类（后备方案）
        
        # 明确的钥匙关键词
        for keyword in self.classification_rules['key_keywords']:
            if keyword in item_name:
                return '钥匙'
        
        # 房间名称（统一归类为钥匙）
        for room_name in self.classification_rules['room_names']:
            if room_name in item_name:
                return '钥匙'
        
        # 消耗品关键词
        for keyword in self.classification_rules['consumable_keywords']:
            if keyword.lower() in name_lower:
                return '消耗品'
        
        # 收集品关键词
        for keyword in self.classification_rules['collection_keywords']:
            if keyword.lower() in name_lower:
                return '收集品'
        
        # 装备类关键词
        for keyword in self.classification_rules['equipment_keywords']:
            if keyword.lower() in name_lower:
                return '装备'
        
        # 特殊配件关键词（提前检查避免与枪械冲突）
        special_accessories = ['枪管', '瞄准镜', '握把', '枪托', '消音器', '补偿器', '弹匣']
        for keyword in special_accessories:
            if keyword in item_name:
                return '配件'
        
        # 枪械类关键词
        for keyword in self.classification_rules['weapon_keywords']:
            if keyword.lower() in name_lower:
                return '枪械'
        
        # 其他配件关键词
        other_accessories = [kw for kw in self.classification_rules['accessory_keywords'] 
                           if kw not in special_accessories]
        for keyword in other_accessories:
            if keyword.lower() in name_lower:
                return '配件'
        
        # 弹药类关键词
        for keyword in self.classification_rules['ammo_keywords']:
            if keyword.lower() in name_lower:
                return '弹药'
        
        # 默认分类
        return '其他'
    
    def get_category_stats(self, items):
        """统计各类别物品数量"""
        from collections import defaultdict
        stats = defaultdict(int)
        for item in items:
            category = self.classify(item.get('物品', item.get('name', '')))
            stats[category] += 1
        return dict(stats)

# 创建全局分类器实例
classifier = ItemClassifier()

def classify_item(item_name):
    """便捷函数：分类单个物品"""
    return classifier.classify(item_name)

def get_classification_stats(items):
    """便捷函数：获取分类统计"""
    return classifier.get_category_stats(items)