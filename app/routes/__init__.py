#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路由模块初始化
"""

from app.routes.main_routes import bp as main_bp
from app.routes.api_routes import bp as api_bp

__all__ = ['main_bp', 'api_bp']
