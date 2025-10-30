import sqlite3
import hashlib
import logging
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Paper:
    title: str
    authors: List[str]
    abstract: str
    arxiv_id: str
    published_date: datetime
    categories: List[str]
    pdf_url: str
    summary: Optional[str] = None
    created_at: Optional[datetime] = None

class DatabaseManager:
    def __init__(self, db_path: str = "arxiv_papers.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            # 创建论文表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    authors TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    arxiv_id TEXT UNIQUE NOT NULL,
                    published_date TEXT NOT NULL,
                    categories TEXT NOT NULL,
                    pdf_url TEXT NOT NULL,
                    summary TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建洞察缓存表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insights_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    data_hash TEXT NOT NULL,
                    insights TEXT NOT NULL,
                    trending TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def paper_exists(self, arxiv_id: str) -> bool:
        """检查论文是否已存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM papers WHERE arxiv_id = ?", (arxiv_id,))
            return cursor.fetchone() is not None

    def save_paper(self, paper: Paper) -> bool:
        """保存论文到数据库"""
        if self.paper_exists(paper.arxiv_id):
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO papers (title, authors, abstract, arxiv_id, published_date, categories, pdf_url, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.title,
                ','.join(paper.authors),
                paper.abstract,
                paper.arxiv_id,
                paper.published_date.isoformat(),
                ','.join(paper.categories),
                paper.pdf_url,
                paper.summary
            ))
            conn.commit()
        return True

    def get_recent_papers(self, days: int = 7) -> List[Paper]:
        """获取最近几天的论文"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, authors, abstract, arxiv_id, published_date, categories, pdf_url, summary, created_at
                FROM papers
                WHERE published_date >= datetime('now', '-{} days')
                ORDER BY published_date DESC
            """.format(days))

            papers = []
            for row in cursor.fetchall():
                papers.append(Paper(
                    title=row[0],
                    authors=row[1].split(','),
                    abstract=row[2],
                    arxiv_id=row[3],
                    published_date=datetime.fromisoformat(row[4]),
                    categories=row[5].split(','),
                    pdf_url=row[6],
                    summary=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None
                ))
            return papers

    def get_all_papers(self) -> List[Paper]:
        """获取所有论文（不限制时间范围）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, authors, abstract, arxiv_id, published_date, categories, pdf_url, summary, created_at
                FROM papers
                ORDER BY published_date DESC
            """)

            papers = []
            for row in cursor.fetchall():
                papers.append(Paper(
                    title=row[0],
                    authors=row[1].split(','),
                    abstract=row[2],
                    arxiv_id=row[3],
                    published_date=datetime.fromisoformat(row[4]),
                    categories=row[5].split(','),
                    pdf_url=row[6],
                    summary=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None
                ))
            return papers

    def get_latest_paper_date(self) -> Optional[datetime]:
        """
        获取数据库中最新的论文发表日期

        Returns:
            最新论文的发表日期，如果数据库为空返回None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(published_date) FROM papers")
            result = cursor.fetchone()

            if result and result[0]:
                return datetime.fromisoformat(result[0])
            return None

    def get_data_hash(self, days: int = 7) -> str:
        """
        获取数据的哈希值，用于检测数据变化

        Args:
            days: 分析的天数（基于论文发表时间）

        Returns:
            数据哈希字符串
        """
        import hashlib

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 使用论文发表时间而不是数据库创建时间，并排除可能变化的字段
            cursor.execute("""
                SELECT title, authors, abstract, arxiv_id, published_date, categories
                FROM papers
                WHERE published_date >= datetime('now', '-{} days')
                ORDER BY arxiv_id
            """.format(days))

            # 获取所有数据并生成哈希
            all_data = []
            for row in cursor.fetchall():
                all_data.append(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}|{row[5]}")

            # 生成MD5哈希
            content = "|".join(sorted(all_data))
            hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()

            # 添加数据总数到哈希中，确保数据量变化也能被检测到
            total_papers = len(all_data)
            final_hash = hashlib.md5(f"{hash_value}_{total_papers}".encode('utf-8')).hexdigest()

            return final_hash

    def save_insights_cache(self, cache_key: str, data_hash: str, insights: str, trending: List[str]) -> bool:
        """
        保存洞察缓存到数据库

        Args:
            cache_key: 缓存键
            data_hash: 数据哈希值
            insights: 洞察内容
            trending: 热门主题

        Returns:
            是否保存成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS insights_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key TEXT UNIQUE NOT NULL,
                        data_hash TEXT NOT NULL,
                        insights TEXT NOT NULL,
                        trending TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    INSERT OR REPLACE INTO insights_cache
                    (cache_key, data_hash, insights, trending, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (
                    cache_key,
                    data_hash,
                    insights,
                    ",".join(trending)
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"保存洞察缓存失败: {e}")
            return False

    def get_insights_cache(self, cache_key: str) -> dict:
        """
        获取洞察缓存

        Args:
            cache_key: 缓存键

        Returns:
            缓存数据字典，包含insights, trending, data_hash等
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT insights, trending, data_hash, created_at, updated_at
                    FROM insights_cache
                    WHERE cache_key = ?
                """, (cache_key,))

                row = cursor.fetchone()
                if row:
                    return {
                        'insights': row[0],
                        'trending': row[1].split(',') if row[1] else [],
                        'data_hash': row[2],
                        'created_at': row[3],
                        'updated_at': row[4]
                    }
                else:
                    return {}
        except Exception as e:
            logger.error(f"获取洞察缓存失败: {e}")
            return {}

    def search_papers(self, keyword: str) -> List[Paper]:
        """搜索包含关键词的论文"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, authors, abstract, arxiv_id, published_date, categories, pdf_url, summary, created_at
                FROM papers
                WHERE title LIKE ? OR abstract LIKE ? OR summary LIKE ?
                ORDER BY published_date DESC
            """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))

            papers = []
            for row in cursor.fetchall():
                papers.append(Paper(
                    title=row[0],
                    authors=row[1].split(','),
                    abstract=row[2],
                    arxiv_id=row[3],
                    published_date=datetime.fromisoformat(row[4]),
                    categories=row[5].split(','),
                    pdf_url=row[6],
                    summary=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None
                ))
            return papers

    def get_all_papers(self) -> List[Paper]:
        """获取所有论文"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, authors, abstract, arxiv_id, published_date, categories, pdf_url, summary, created_at
                FROM papers
                ORDER BY published_date DESC
            """)

            papers = []
            for row in cursor.fetchall():
                papers.append(Paper(
                    title=row[0],
                    authors=row[1].split(','),
                    abstract=row[2],
                    arxiv_id=row[3],
                    published_date=datetime.fromisoformat(row[4]),
                    categories=row[5].split(','),
                    pdf_url=row[6],
                    summary=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None
                ))
            return papers

    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        """根据arxiv_id获取论文"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT title, authors, abstract, arxiv_id, published_date, categories, pdf_url, summary, created_at
                FROM papers
                WHERE arxiv_id = ?
            """, (arxiv_id,))

            row = cursor.fetchone()
            if row:
                return Paper(
                    title=row[0],
                    authors=row[1].split(','),
                    abstract=row[2],
                    arxiv_id=row[3],
                    published_date=datetime.fromisoformat(row[4]),
                    categories=row[5].split(','),
                    pdf_url=row[6],
                    summary=row[7],
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None
                )
            return None