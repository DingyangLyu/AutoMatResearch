"""
统一配置管理
"""
import os
from pathlib import Path
from typing import List, Dict, Any
import json

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录配置
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_DIR = DATA_DIR / "database"
EXPORTS_DIR = DATA_DIR / "exports"
INSIGHTS_DIR = DATA_DIR / "insights"
LOGS_DIR = DATA_DIR / "logs"

# Web资源目录
WEB_DIR = PROJECT_ROOT / "web"
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

# 配置文件路径
CONFIG_DIR = PROJECT_ROOT / "config"
ENV_FILE = CONFIG_DIR / ".env"
USER_CONFIG_FILE = CONFIG_DIR / "user_config.json"

class Settings:
    """应用配置类"""

    def __init__(self):
        self.load_from_env()
        self.load_user_config()

    def load_from_env(self):
        """从环境变量加载配置"""
        # DeepSeek API配置
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
        self.DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')

        # 数据库配置
        self.DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATABASE_DIR}/arxiv_papers.db')

        # 爬取配置
        self.MAX_PAPERS_PER_DAY = int(os.getenv('MAX_PAPERS_PER_DAY', '10'))
        search_keywords = os.getenv('SEARCH_KEYWORDS', '["machine learning", "deep learning", "artificial intelligence", "neural networks"]')
        try:
            self.SEARCH_KEYWORDS = json.loads(search_keywords)
        except:
            self.SEARCH_KEYWORDS = ["machine learning", "deep learning", "artificial intelligence", "neural networks"]

        # 日志配置
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'arxiv_scraper.log')

        # 调度配置
        self.SCHEDULE_TIME = os.getenv('SCHEDULE_TIME', '09:00')

    def load_user_config(self):
        """加载用户配置文件"""
        if USER_CONFIG_FILE.exists():
            try:
                with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    for key, value in user_config.items():
                        setattr(self, key, value)
            except Exception as e:
                print(f"加载用户配置失败: {e}")

    @property
    def log_file_path(self) -> Path:
        """获取日志文件完整路径"""
        return LOGS_DIR / self.LOG_FILE

    @property
    def database_path(self) -> str:
        """获取数据库路径"""
        return str(DATABASE_DIR / "arxiv_papers.db")

# 全局配置实例
settings = Settings()