#!/bin/bash
# 交易行数据可视化系统 - Web 应用启动脚本

echo "======================================"
echo "🚀 启动交易行数据可视化系统"
echo "======================================"

# 检查 Python
if ! command -v python &> /dev/null; then
    echo "❌ 错误：未找到 Python"
    exit 1
fi

echo "✓ Python 版本：$(python --version)"

# 激活虚拟环境（如果存在）
if [ -d ".venv" ]; then
    echo "✓ 激活虚拟环境..."
    source .venv/bin/activate
fi

# 启动应用
echo ""
echo "🌐 启动 Web 服务器..."
echo "💾 访问地址：http://localhost:5000"
echo "======================================"
python app.py
