#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
交易行数据爬虫 - Playwright 版本
用于爬取动态渲染的交易行物品价格数据
"""

import sys
import os
import json
import time
import hashlib
import re
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright 未安装，请先安装:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)

# 先初始化 Flask app
from app import create_app
app, _ = create_app()

from app.services.data_service import data_service


class TradingDataCrawler:
    """交易行数据爬虫（使用 Playwright）"""
    
    def __init__(self):
        self.base_url = "https://orzice.com"
        self.data_service = data_service
        self.stats = {
            'crawl_start_time': None,
            'total_items': 0,
            'categories': {},
            'errors': [],
            'images_cached': 0
        }
        
        # 图片缓存目录
        self.image_cache_dir = os.path.join(project_root, 'static', 'item_images')
        os.makedirs(self.image_cache_dir, exist_ok=True)
        print(f"图片缓存目录：{self.image_cache_dir}")
        
    def crawl_all_categories(self):
        """爬取所有分类的物品数据（包含分页）"""
        # 定义所有分类页面
        categories = [
            {'name': '收集品', 'url': f'{self.base_url}/v/item_jz'},  # 物品页面实际是收集品
            {'name': '子弹', 'url': f'{self.base_url}/v/ammo'},
            {'name': '钥匙卡', 'url': f'{self.base_url}/v/keys'},
            {'name': '收集品', 'url': f'{self.base_url}/v/collection'},  # 额外的收集品页面
            {'name': '消耗品', 'url': f'{self.base_url}/v/consume'},
            {'name': '战备', 'url': f'{self.base_url}/v/zhanbei'},
        ]
        
        print("=" * 60)
        print("🚀 开始爬取交易行数据...")
        print("=" * 60)
        
        self.stats['crawl_start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            total_items = 0
            
            for category in categories:
                try:
                    print(f"\n📦 正在爬取分类：{category['name']}")
                    print(f"   URL: {category['url']}")
                    
                    # 访问页面
                    page.goto(category['url'], timeout=30000)
                    
                    # 等待页面加载完成（等待表格出现）
                    page.wait_for_selector('table', timeout=10000)
                    time.sleep(2)
                    
                    # 爬取所有页的数据
                    category_items = []
                    page_num = 1
                    max_pages = 10  # 最多爬取 10 页，防止过多
                    
                    while page_num <= max_pages:
                        print(f"   第 {page_num} 页...")
                        
                        # 提取当前页数据
                        items = self.extract_items_from_page(page, category['name'])
                        if items:
                            category_items.extend(items)
                            print(f"      ✓ 获取 {len(items)} 个物品")
                        else:
                            print(f"      ⚠ 未找到数据")
                            break
                        
                        # 检查是否有下一页
                        has_next = self.go_to_next_page(page)
                        if not has_next:
                            print(f"   ✓ 已到最后一页")
                            break
                        
                        page_num += 1
                        time.sleep(1)  # 翻页延迟
                    
                    if category_items:
                        print(f"   ✓ 分类 {category['name']} 共获取 {len(category_items)} 个物品")
                        total_items += len(category_items)
                        
                        # 保存数据到 Redis
                        trading_data = {
                            'url': category['url'],
                            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'items': category_items,
                            'category': category['name'],
                            'total_pages': page_num,
                            'timestamp': int(time.time())
                        }
                        
                        if self.data_service.save_trading_data(category['name'], trading_data):
                            print(f"   ✓ 数据已保存到 Redis")
                        else:
                            print(f"   ✗ 数据保存失败")
                    else:
                        print(f"   ⚠ 未找到物品数据")
                        
                except Exception as e:
                    error_msg = f"爬取分类 {category['name']} 失败：{str(e)}"
                    print(f"   ✗ {error_msg}")
                    self.stats['errors'].append(error_msg)
            
            browser.close()
        
        # 更新统计
        self.stats['total_items'] = total_items
        self.stats['crawl_end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print("\n" + "=" * 60)
        print(f"✅ 爬取完成!")
        print(f"   总物品数：{total_items}")
        print(f"   开始时间：{self.stats['crawl_start_time']}")
        print(f"   结束时间：{self.stats['crawl_end_time']}")
        print(f"   错误数：{len(self.stats['errors'])}")
        print("=" * 60)
        
        return total_items
    
    def extract_items_from_page(self, page, category_name):
        """从页面中提取物品数据（包含图片）"""
        items = []
            
        try:
            # 使用 JavaScript 获取渲染后的表格数据（包含图片 URL）
            table_data = page.evaluate(f'''() => {{
                const items = [];
                const rows = document.querySelectorAll('table tr');
                const category = "{category_name}";
                                
                rows.forEach((row, index) => {{
                    // 跳过表头
                    if (index === 0) return;
                                    
                    const cells = row.querySelectorAll('td, th');
                    if (cells.length >= 4) {{
                        const itemName = cells[0].textContent.trim();
                                    
                        // 查找价格列 - 需要找到正确的价格列
                        let price = '';
                        // 尝试不同的价格列位置
                        for (let i = 1; i < cells.length; i++) {{
                            const cellText = cells[i].textContent.trim();
                            // 检查是否包含数字（价格）
                            if (/^\d+(\.\d+)?$/.test(cellText.replace(/,/g, ''))) {{
                                price = cellText;
                                break;
                            }}
                        }}
                                    
                        // 如果没有找到价格，默认使用第 2 列
                        if (!price && cells[1]) {{
                            price = cells[1].textContent.trim();
                        }}
                                        
                        // 查找物品图片
                        let imageUrl = '';
                        const imgTag = cells[0].querySelector('img');
                        if (imgTag && imgTag.src) {{
                            imageUrl = imgTag.src;
                        }}
                                        
                        // 根据页面分类和物品名称确定最终分类
                        let finalCategory = category;
                                        
                        // 如果是"战备"分类，需要根据物品名称进一步细分
                        if (category === '战备') {{
                            // 配件类关键词
                            const accessoryKeywords = ['枪', '头', '甲', '胸挂', '背包', '弹匣', '瞄', '镜', '握把', '托', '消音', '补偿', '扩展'];
                                            
                            // 检查是否包含配件关键词
                            const isAccessory = accessoryKeywords.some(keyword => itemName.includes(keyword));
                                            
                            if (isAccessory) {{
                                finalCategory = '配件';
                            }} else {{
                                finalCategory = '装备';
                            }}
                        }}
                                        
                        const item = {{
                            '物品': itemName,
                            '价格': price,
                            '分类': finalCategory,
                            '数量': 1,
                            '原始分类': category,
                            'image_url': imageUrl  // 保存原始图片 URL
                        }};
                        items.push(item);
                    }}
                }});
                                
                return items;
            }}''')
                
            if table_data:
                # 下载图片并转换为本地路径
                for item in table_data:
                    if item.get('image_url'):
                        local_path = self.download_and_cache_image(
                            item['image_url'], 
                            item['物品']
                        )
                        if local_path:
                            item['image_url'] = local_path
                            self.stats['images_cached'] += 1
                    items.append(item)
                    
        except Exception as e:
            print(f"   提取数据失败：{e}")
                
        return items
        
    def download_and_cache_image(self, image_url, item_name):
        """下载图片并缓存到本地"""
        try:
            # 生成唯一的文件名
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:16]
            file_extension = os.path.splitext(image_url)[1] or '.jpg'
            safe_name = re.sub(r'[^\w\u4e00-\u9fff_-]', '_', item_name)[:30]
            local_filename = f"{safe_name}_{url_hash}{file_extension}"
            local_path = os.path.join(self.image_cache_dir, local_filename)
                
            # 如果文件已存在，直接返回相对路径
            if os.path.exists(local_path):
                return f"/static/item_images/{local_filename}"
                
            # 下载图片
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
                
            # 保存图片
            with open(local_path, 'wb') as f:
                f.write(response.content)
                
            print(f"  ✓ 图片缓存：{local_filename}")
            return f"/static/item_images/{local_filename}"
                
        except Exception as e:
            print(f"  ✗ 图片下载失败 {image_url}: {str(e)}")
            return None
    
    def go_to_next_page(self, page):
        """点击下一页按钮，返回是否成功"""
        try:
            # 尝试多种分页选择器
            pagination_selectors = [
                'button:has-text("下一页")',
                'a:has-text("下一页")',
                'button:has-text(">>")',
                'a:has-text(">>")',
                'button:has-text("Next")',
                'a:has-text("Next")',
                '.pagination .next',
                '[class*="pagination"] button:last-child',
                '[class*="page"] button:last-child',
            ]
            
            for selector in pagination_selectors:
                next_button = page.query_selector(selector)
                if next_button:
                    # 检查按钮是否禁用
                    is_disabled = next_button.is_disabled()
                    if not is_disabled:
                        next_button.click()
                        page.wait_for_load_state('networkidle', timeout=10000)
                        time.sleep(1)  # 等待内容加载
                        return True
                    else:
                        return False  # 按钮已禁用，说明是最后一页
            
            # 如果没找到按钮，尝试通过页码判断
            # 查找当前页码
            current_page = page.evaluate('''() => {
                const pageElements = document.querySelectorAll('[class*="page"], [class*="pagination"]');
                for (const elem of pageElements) {
                    const text = elem.textContent;
                    const match = text.match(/(\d+)\s*\/\s*(\d+)/);
                    if (match) {
                        return parseInt(match[1]);
                    }
                }
                return -1;
            }''')
            
            if current_page > 0:
                # 尝试点击下一个数字
                next_page_btn = page.query_selector(f'text="{current_page + 1}"')
                if next_page_btn:
                    next_page_btn.click()
                    page.wait_for_load_state('networkidle', timeout=10000)
                    time.sleep(1)
                    return True
            
            return False  # 没有找到下一页
            
        except Exception as e:
            print(f"   翻页失败：{e}")
            return False


def main():
    """主函数"""
    crawler = TradingDataCrawler()
    crawler.crawl_all_categories()


if __name__ == "__main__":
    main()
