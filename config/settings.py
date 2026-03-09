#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目配置文件
"""

import os

class Config:
    """基础配置类"""
    # 基础配置
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # 数据目录配置
    DATA_DIR = os.getenv('DATA_DIR', 'trading_price_data')
    IMAGE_CACHE_DIR = os.getenv('IMAGE_CACHE_DIR', 'local_image_cache')
    
    # Redis 配置
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    # 爬虫配置
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    REQUEST_TIMEOUT = 15
    
    # 分页配置
    ITEMS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY')  # 必须从环境变量获取


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
