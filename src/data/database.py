import sqlite3
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

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
                WHERE created_at >= datetime('now', '-{} days')
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