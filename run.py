#!/usr/bin/env python3
"""
AutoMatResearch 主启动脚本
"""

import sys
import os
from pathlib import Path

# 确保项目根目录在Python路径中
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    from src.main import main
    main()