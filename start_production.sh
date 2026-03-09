#!/bin/bash
# 交易行数据可视化系统 - 生产环境启动脚本

echo "======================================"
echo "🚀 启动交易行数据可视化系统（生产环境）"
echo "======================================"

# 进入脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境（如果存在）- 移到前面！
if [ -d ".venv" ]; then
    echo "✓ 激活虚拟环境..."
    source .venv/bin/activate
fi

# 检查 Python（现在虚拟环境已激活）
if ! command -v python &> /dev/null; then
    echo "❌ 错误：未找到 Python"
    exit 1
fi

echo "✓ Python 版本：$(python --version)"

# 检查 Redis 是否运行
if ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️  Redis 未运行，请先启动 Redis:"
    echo "   sudo systemctl start redis"
    exit 1
fi
echo "✓ Redis 服务正常运行"

# 创建日志目录
mkdir -p logs

# 禁用 Flask debug 模式
export FLASK_DEBUG=0
export FLASK_ENV=production

# 启动应用
echo "🌐 启动 Web 服务器..."
echo "💾 访问地址：http://0.0.0.0:5000 "
echo "======================================"
exec python app.py