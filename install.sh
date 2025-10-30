#!/bin/bash

# AutoMatResearch 安装脚本
# 用于快速设置开发环境

set -e

echo "🚀 AutoMatResearch 安装脚本"
echo "=========================="

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+' || echo "0.0")
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python 版本检查通过: $python_version"
else
    echo "❌ 需要 Python 3.8 或更高版本，当前版本: $python_version"
    exit 1
fi

# 检查 pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 未安装，请先安装 pip3"
    exit 1
fi
echo "✅ pip3 已安装"

# 创建虚拟环境（推荐）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建完成"
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "⬆️ 升级 pip..."
pip install --upgrade pip

# 可编辑安装
echo "📥 进行可编辑安装..."
pip install -e ".[dev]"

# 复制环境变量文件
if [ ! -f ".env" ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件"
    echo "⚠️  请编辑 .env 文件，设置你的 API 密钥和配置"
else
    echo "✅ .env 文件已存在"
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p data/logs data/database data/exports data/insights
echo "✅ 目录创建完成"

echo ""
echo "🎉 安装完成！"
echo ""
echo "📋 下一步操作："
echo "1. 编辑 .env 文件，设置你的 DEEPSEEK_API_KEY"
echo "2. 激活虚拟环境: source venv/bin/activate"
echo "3. 运行程序: python run.py --mode cli"
echo "4. 或者启动 Web 界面: python run.py --mode web"
echo ""
echo "💡 更多使用方法请查看 README.md"