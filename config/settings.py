"""
统一配置管理
"""
import os
from pathlib import Path
from typing import List, Dict, Any
import json
from dotenv import load_dotenv

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
ENV_FILE = PROJECT_ROOT / ".env"
USER_CONFIG_FILE = CONFIG_DIR / "user_config.json"

# 加载 .env 文件
load_dotenv(ENV_FILE)

class Settings:
    """应用配置类"""

    def __init__(self):
        self.load_from_env()
        self.load_user_config()

    def load_from_env(self):
        """从环境变量加载配置"""
        # DeepSeek API配置 - 默认值
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
        self.DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
        self.DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

        # 数据库配置
        self.DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATABASE_DIR}/arxiv_papers.db')

        # 爬取配置
        self.MAX_PAPERS_PER_DAY = int(os.getenv('MAX_PAPERS_PER_DAY', '10'))
        search_keywords = os.getenv('SEARCH_KEYWORDS', '["materials science", "machine learning"]')
        try:
            self.SEARCH_KEYWORDS = json.loads(search_keywords)
        except:
            self.SEARCH_KEYWORDS = ["materials science", "machine learning"]

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

                    # 加载API配置
                    if 'api_config' in user_config:
                        api_config = user_config['api_config']
                        # 用户配置优先级高于环境变量
                        if 'api_key' in api_config and api_config['api_key']:
                            self.DEEPSEEK_API_KEY = api_config['api_key']
                        if 'base_url' in api_config and api_config['base_url']:
                            self.DEEPSEEK_BASE_URL = api_config['base_url']
                        if 'model' in api_config and api_config['model']:
                            self.DEEPSEEK_MODEL = api_config['model']

                    # 加载用户偏好设置
                    if 'user_preferences' in user_config:
                        user_prefs = user_config['user_preferences']

                        # 加载用户偏好配置
                        if 'max_papers_per_day' in user_prefs:
                            self.MAX_PAPERS_PER_DAY = int(user_prefs['max_papers_per_day'])
                        if 'schedule_time' in user_prefs:
                            self.SCHEDULE_TIME = user_prefs['schedule_time']

                        # 存储用户偏好供其他模块使用
                        self.user_preferences = user_prefs

                    # 兼容旧的扁平配置结构（向后兼容）
                    for key, value in user_config.items():
                        if key not in ['api_config', 'user_preferences'] and hasattr(self, key):
                            setattr(self, key, value)

            except Exception as e:
                print(f"加载用户配置失败: {e}")
        else:
            # 如果没有用户配置文件，初始化空的偏好设置
            self.user_preferences = {}

    def save_user_config(self, section: str, config_data: dict):
        """保存用户配置到文件"""
        try:
            user_config = {}
            if USER_CONFIG_FILE.exists():
                with open(USER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)

            # 更新指定section的配置
            user_config[section] = config_data

            # 确保目录存在
            USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            # 保存配置
            with open(USER_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(user_config, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"保存用户配置失败: {e}")
            return False

    def save_user_preferences(self, preferences_data: dict):
        """保存用户偏好设置"""
        return self.save_user_config('user_preferences', preferences_data)

    def get_user_preferences(self) -> dict:
        """获取用户偏好设置"""
        return getattr(self, 'user_preferences', {})

    def get_api_config(self) -> dict:
        """获取当前API配置"""
        return {
            'api_key': self.DEEPSEEK_API_KEY,
            'base_url': self.DEEPSEEK_BASE_URL,
            'model': self.DEEPSEEK_MODEL
        }

    @property
    def log_file_path(self) -> Path:
        """获取日志文件完整路径"""
        return LOGS_DIR / self.LOG_FILE

    @property
    def logs_dir(self) -> Path:
        """获取日志目录路径"""
        return LOGS_DIR

    @property
    def database_path(self) -> str:
        """获取数据库路径"""
        return str(DATABASE_DIR / "arxiv_papers.db")

# 全局配置实例
settings = Settings()