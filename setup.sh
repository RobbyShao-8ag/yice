#!/bin/bash
# 易策 一键安装脚本

set -e

echo "🌟 易策 (yice) 安装脚本"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
    echo "❌ 需要 Python 3.11+，当前版本: $PYTHON_VERSION"
    echo "   请升级 Python: https://www.python.org/downloads/"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# Check if models.json exists
if [ ! -f "models.json" ]; then
    echo ""
    echo "⚠️  未找到 models.json 配置文件"
    if [ -f "models.example.json" ]; then
        echo "   复制示例配置..."
        cp models.example.json models.json
        echo "✅ 已创建 models.json"
        echo ""
        echo "   🔑 请编辑 models.json 配置你的 API 密钥："
        echo "      - OpenAI: https://platform.openai.com/api-keys"
        echo "      - DeepSeek: https://platform.deepseek.com"
        echo "      - MiniMax: https://www.minimaxi.com"
    fi
fi

# CLI version - zero dependencies
echo ""
echo "📦 CLI 版本：零依赖，可直接运行"
echo "   python main.py"

# Web interface setup (optional)
echo ""
echo "📦 Web 界面安装（可选）..."
echo ""

# Backend setup
if [ -d "web/backend" ]; then
    echo "   后端依赖..."
    cd web/backend

    if [ ! -d "venv" ]; then
        echo "   创建虚拟环境..."
        python3 -m venv venv
    fi

    # Activate venv (Unix)
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/Scripts/activate" ]; then
        # Windows
        source venv/Scripts/activate
    fi

    pip install -r requirements.txt
    cd ../..
    echo "   ✅ 后端依赖已安装"
fi

# Frontend setup
if [ -d "web/frontend" ] && [ -f "web/frontend/package.json" ]; then
    echo "   前端依赖..."
    cd web/frontend

    # Check Node.js
    if ! command -v npm &> /dev/null; then
        echo "   ⚠️  未检测到 npm，请先安装 Node.js: https://nodejs.org"
    else
        npm install
        echo "   ✅ 前端依赖已安装"
    fi

    cd ../..
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "下一步："
echo "  1. 编辑 models.json 配置 API 密钥"
echo "  2. CLI 运行: python main.py"
echo "  3. Web 运行: python web/main.py"
echo ""