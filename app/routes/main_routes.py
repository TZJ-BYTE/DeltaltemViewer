#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主页面路由
"""

from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """主页 - 商店样式展示"""
    return render_template('index.html')
