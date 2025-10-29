#!/usr/bin/env python3
"""
安装和配置脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 需要Python 3.8或更高版本")
        sys.exit(1)
    print(f"✅ Python版本: {sys.version}")

def install_dependencies():
    """安装依赖包"""
    print("📦 安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖包安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖包安装失败: {e}")
        sys.exit(1)

def setup_directories():
    """创建必要的目录"""
    directories = ["logs", "insights", "reports", "trends", "exports"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ 目录结构创建完成")

def setup_env_file():
    """设置环境变量文件"""
    env_file = Path(".env")
    if not env_file.exists():
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ 已创建.env文件，请编辑其中的配置")
            print("💡 特别注意设置DEEPSEEK_API_KEY")
        else:
            print("⚠️ 未找到.env.example文件")
    else:
        print("✅ .env文件已存在")

def test_database():
    """测试数据库连接"""
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        print("✅ 数据库连接测试通过")
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {e}")

def test_config():
    """测试配置加载"""
    try:
        from config.settings import settings
        print(f"✅ 配置加载成功")
        print(f"   最大论文数: {settings.MAX_PAPERS_PER_DAY}")
        print(f"   关键词: {settings.SEARCH_KEYWORDS}")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        print("💡 请检查.env文件中的配置")

def main():
    """主安装流程"""
    print("🚀 开始安装arXiv论文爬取Agent...")
    print("=" * 50)

    check_python_version()
    install_dependencies()
    setup_directories()
    setup_env_file()
    test_database()
    test_config()

    print("\n" + "=" * 50)
    print("🎉 安装完成！")
    print("\n📋 下一步:")
    print("1. 编辑.env文件，设置你的DeepSeek API密钥")
    print("2. 运行 'python main.py --help' 查看使用方法")
    print("3. 运行 'python cli.py' 进入交互式界面")
    print("4. 运行 'python main.py --run-once' 测试爬取功能")

if __name__ == "__main__":
    main()