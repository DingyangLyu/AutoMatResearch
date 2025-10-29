#!/usr/bin/env python3
"""
一键启动脚本
提供多种启动选项
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    import argparse

    parser = argparse.ArgumentParser(description='arXiv论文爬取Agent启动器')
    parser.add_argument('--mode', choices=['cli', 'web', 'scheduler', 'setup'],
                       default='cli', help='启动模式')
    parser.add_argument('--port', type=int, default=5000, help='Web界面端口')

    args = parser.parse_args()

    print("🚀 arXiv论文爬取Agent")
    print("=" * 40)

    if args.mode == 'setup':
        print("🔧 运行安装脚本...")
        import subprocess
        subprocess.call([sys.executable, str(PROJECT_ROOT / 'scripts' / 'setup.py')])

    elif args.mode == 'cli':
        print("💻 启动交互式命令行界面...")
        from src.cli.cli import main as cli_main
        cli_main()

    elif args.mode == 'web':
        print("🌐 启动Web界面...")
        print(f"📱 访问地址: http://localhost:{args.port}")
        try:
            from src.web.web_app import app
            app.run(host='0.0.0.0', port=args.port, debug=False)
        except ImportError as e:
            print(f"❌ 导入错误: {e}")
            print("💡 请确保已安装Flask: pip install flask")
            sys.exit(1)

    elif args.mode == 'scheduler':
        print("⏰ 启动定时调度器...")
        from src.core.scheduler import PaperScheduler
        scheduler = PaperScheduler()
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print("\n⏹️ 调度器已停止")

if __name__ == "__main__":
    main()