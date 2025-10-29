"""
配置模块 - 兼容性包装器
使用统一的配置管理系统
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings as _settings

# 为了向后兼容，导出统一的配置
settings = _settings