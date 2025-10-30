"""
关键词管理器
管理多个关键词的数据库和配置
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import logging
from src.utils.simple_query_generator import generate_simple_query

logger = logging.getLogger(__name__)

@dataclass
class KeywordConfig:
    """关键词配置"""
    name: str
    display_name: str
    db_path: str
    search_query: str
    created_at: datetime
    last_used: datetime
    paper_count: int = 0

class KeywordManager:
    """关键词管理器"""

    def __init__(self, config_dir: str = "data/database"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "keywords_config.json"
        self.current_keyword_file = self.config_dir / "current_keyword.txt"
        self._keywords: Dict[str, KeywordConfig] = {}
        self._current_keyword: str = "default"
        self.load_keywords()
        self.load_current_keyword()

    def load_keywords(self):
        """加载关键词配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, config_data in data.items():
                        self._keywords[name] = KeywordConfig(
                            name=config_data['name'],
                            display_name=config_data['display_name'],
                            db_path=config_data['db_path'],
                            search_query=config_data['search_query'],
                            created_at=datetime.fromisoformat(config_data['created_at']),
                            last_used=datetime.fromisoformat(config_data['last_used']),
                            paper_count=config_data.get('paper_count', 0)
                        )
            except Exception as e:
                logger.error(f"加载关键词配置失败: {e}")

        # 如果没有关键词，创建默认配置
        if not self._keywords:
            self.create_default_keyword()

    def create_default_keyword(self):
        """创建默认关键词配置"""
        default_config = KeywordConfig(
            name="default",
            display_name="默认",
            db_path=str(self.config_dir / "arxiv_papers.db"),
            search_query="all:materials science",
            created_at=datetime.now(),
            last_used=datetime.now()
        )
        self._keywords["default"] = default_config
        self.save_keywords()

    def save_keywords(self):
        """保存关键词配置"""
        try:
            data = {}
            for name, config in self._keywords.items():
                # 更新论文数量
                config.paper_count = self.get_paper_count(config.db_path)

                data[name] = {
                    'name': config.name,
                    'display_name': config.display_name,
                    'db_path': config.db_path,
                    'search_query': config.search_query,
                    'created_at': config.created_at.isoformat(),
                    'last_used': config.last_used.isoformat(),
                    'paper_count': config.paper_count
                }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存关键词配置失败: {e}")

    def load_current_keyword(self):
        """加载当前关键词"""
        if self.current_keyword_file.exists():
            try:
                with open(self.current_keyword_file, 'r', encoding='utf-8') as f:
                    self._current_keyword = f.read().strip()
            except Exception as e:
                logger.error(f"加载当前关键词失败: {e}")
                self._current_keyword = "default"
        else:
            self._current_keyword = "default"

    def set_current_keyword(self, keyword: str) -> bool:
        """设置当前关键词"""
        if keyword not in self._keywords:
            return False

        self._current_keyword = keyword
        self._keywords[keyword].last_used = datetime.now()

        # 保存到文件
        try:
            with open(self.current_keyword_file, 'w', encoding='utf-8') as f:
                f.write(keyword)
            self.save_keywords()
            return True
        except Exception as e:
            logger.error(f"保存当前关键词失败: {e}")
            return False

    def add_keyword_optimized(self, name: str, display_name: str, user_keywords: str,
                             use_and_logic: bool = True, focus_materials: bool = True,
                             focus_ml: bool = True) -> tuple[bool, str]:
        """
        使用优化的查询生成添加新关键词 - 专为跨学科研究设计

        Args:
            name: 关键词名称（英文标识符）
            display_name: 显示名称
            user_keywords: 用户输入的关键词
            use_and_logic: 是否使用AND逻辑
            focus_materials: 是否聚焦材料科学
            focus_ml: 是否聚焦机器学习

        Returns:
            (是否成功, 生成的查询)
        """
        if name in self._keywords:
            return False, ""

        # 使用优化的查询生成器
        generated_query = generate_optimized_arxiv_query(
            user_keywords,
            use_and_logic=use_and_logic,
            focus_materials=focus_materials,
            focus_ml=focus_ml
        )

        # 使用生成的查询添加关键词
        success = self.add_keyword(name, display_name, generated_query)

        if success:
            logger.info(f"优化生成查询: {user_keywords} -> {generated_query}")

        return success, generated_query

    def add_keyword_auto(self, name: str, display_name: str, user_keywords: str,
                        search_fields: List[str] = None, use_categories: bool = True) -> tuple[bool, str]:
        """
        使用自动查询生成添加新关键词

        Args:
            name: 关键词名称（英文标识符）
            display_name: 显示名称
            user_keywords: 用户输入的关键词
            search_fields: 搜索字段 ['all', 'ti', 'au', 'cat']，默认使用全部
            use_categories: 是否自动添加相关分类

        Returns:
            (是否成功, 生成的查询)
        """
        if name in self._keywords:
            return False, ""

        # Use simple query generator without automatic categories
        from src.utils.simple_query_generator import SimpleQueryGenerator
        generator = SimpleQueryGenerator()
        keywords = [kw.strip() for kw in user_keywords.split() if kw.strip()]
        generated_query = generator.generate_arxiv_query(
            keywords=keywords,
            logic="AND",
            use_categories=False
        )

        # 使用生成的查询添加关键词
        success = self.add_keyword(name, display_name, generated_query)

        if success:
            logger.info(f"自动生成查询: {user_keywords} -> {generated_query}")

        return success, generated_query

    def get_query_suggestions(self, user_keywords: str) -> List[str]:
        """
        获取查询建议

        Args:
            user_keywords: 用户输入的关键词

        Returns:
            查询建议列表
        """
        # Use simple query generator for suggestions without automatic categories
        from src.utils.simple_query_generator import SimpleQueryGenerator
        generator = SimpleQueryGenerator()
        keywords = user_keywords.split()
        suggestions = []

        # Suggest AND logic query
        and_query = generator.generate_arxiv_query(keywords=keywords, logic="AND", use_categories=False)
        suggestions.append(and_query)

        # Suggest OR logic query
        or_query = generator.generate_arxiv_query(keywords=keywords, logic="OR", use_categories=False)
        suggestions.append(or_query)

        return suggestions

    def add_keyword_multi(self, name: str, display_name: str, keywords: List[str],
                         logic: str = "AND", use_categories: bool = True) -> tuple[bool, str]:
        """
        Add keyword using multiple user-defined keywords with AND/OR logic

        Args:
            name: Keyword identifier
            display_name: Display name
            keywords: List of user-defined keywords
            logic: "AND" or "OR" logic to combine keywords
            use_categories: Whether to include arXiv category restrictions

        Returns:
            (success, generated_query)
        """
        if name in self._keywords:
            return False, ""

        # Generate simple query from multiple keywords without automatic categories
        from src.utils.simple_query_generator import SimpleQueryGenerator
        generator = SimpleQueryGenerator()
        generated_query = generator.generate_arxiv_query(
            keywords=keywords,
            logic=logic,
            use_categories=use_categories
        )

        # Add keyword using generated query
        success = self.add_keyword(name, display_name, generated_query)

        if success:
            keyword_str = f' {logic} '.join(keywords)
            logger.info(f"Multi-keyword query generated: '{keyword_str}' -> '{generated_query}'")

        return success, generated_query

    def add_keyword(self, name: str, display_name: str, search_query: str) -> bool:
        """Add new keyword"""
        if name in self._keywords:
            return False

        # Create database file path
        db_filename = f"{name.replace(' ', '_').lower()}.db"
        db_path = str(self.config_dir / db_filename)

        config = KeywordConfig(
            name=name,
            display_name=display_name,
            db_path=db_path,
            search_query=search_query,
            created_at=datetime.now(),
            last_used=datetime.now()
        )

        self._keywords[name] = config
        self.save_keywords()
        return True

    def remove_keyword(self, name: str) -> bool:
        """删除关键词"""
        if name not in self._keywords or name == self._current_keyword:
            return False

        del self._keywords[name]

        # 删除数据库文件（可选）
        # db_path = self._keywords[name].db_path
        # if Path(db_path).exists():
        #     Path(db_path).unlink()

        self.save_keywords()
        return True

    def get_keyword_config(self, name: str) -> Optional[KeywordConfig]:
        """获取关键词配置"""
        return self._keywords.get(name)

    def get_current_keyword(self) -> str:
        """获取当前关键词"""
        return self._current_keyword

    def get_current_config(self) -> KeywordConfig:
        """获取当前关键词配置"""
        if self._current_keyword in self._keywords:
            return self._keywords[self._current_keyword]
        elif self._keywords:
            # If current keyword doesn't exist but we have keywords, return the first one
            return list(self._keywords.values())[0]
        else:
            # Return a default config when no keywords exist
            from datetime import datetime
            return KeywordConfig(
                name="default",
                display_name="默认关键词",
                db_path=str(self.config_dir / "default.db"),
                search_query="all:materials science",
                created_at=datetime.now(),
                last_used=datetime.now(),
                paper_count=0
            )

    def get_all_keywords(self) -> List[KeywordConfig]:
        """获取所有关键词配置"""
        return list(self._keywords.values())

    def get_paper_count(self, db_path: str) -> int:
        """获取数据库中的论文数量"""
        try:
            if not Path(db_path).exists():
                return 0

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM papers")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"获取论文数量失败: {e}")
            return 0

    def get_database_manager(self, keyword: str = None):
        """获取指定关键词的数据库管理器"""
        if keyword is None:
            keyword = self._current_keyword

        config = self._keywords.get(keyword)
        if not config:
            config = self._keywords["default"]

        from src.data.database import DatabaseManager
        return DatabaseManager(config.db_path, keyword)

# 全局关键词管理器实例
keyword_manager = KeywordManager()