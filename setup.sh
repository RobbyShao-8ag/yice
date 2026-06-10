#!/bin/bash
# 易策 一键安装脚本

set -e

echo "🌟 易策 (yice) 安装脚本"
echo ""

# Check Python version and prefer any available Python 3.11+
PYTHON_BIN=""
for candidate in python python3.12 python3.11 python3; do
    if command -v "$candidate" > /dev/null 2>&1; then
        if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' > /dev/null 2>&1; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ 需要 Python 3.11+"
    echo "   当前 python: $(python --version 2>&1 || echo '未找到')"
    echo "   当前 python3: $(python3 --version 2>&1 || echo '未找到')"
    echo "   请升级 Python: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON_BIN" --version 2>&1 | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION ($PYTHON_BIN)"

# Check if models.json exists
if [ ! -f "models.json" ]; then
    echo ""
    echo "⚠️  未找到 models.json 配置文件"
    if [ -f "models.example.json" ]; then
        echo "   复制示例配置..."
        cp models.example.json models.json
        echo "✅ 已创建 models.json"
        echo ""
        echo "   🔑 如需启用 LLM 推演，请编辑 models.json 配置你的 API 密钥："
        echo "      - DeepSeek: https://platform.deepseek.com"
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

    if [ -d "venv" ] && [ ! -x "venv/bin/python" ] && [ ! -x "venv/Scripts/python.exe" ]; then
        echo "   检测到不完整的虚拟环境，重新创建..."
        rm -rf venv
    fi

    if [ ! -d "venv" ]; then
        echo "   创建虚拟环境..."
        "$PYTHON_BIN" -m venv venv
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
echo "  1. 先试 CLI 本地演示: python main.py"
echo "  2. 如需 LLM 推演，编辑 models.json 配置 API 密钥"
echo "  3. Web 运行: python web/main.py"
echo ""
