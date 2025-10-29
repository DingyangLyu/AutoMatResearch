import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.database import Paper, DatabaseManager
from config.settings import settings

logger = logging.getLogger(__name__)

class ArxivScraper:
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.db = DatabaseManager(settings.database_path)

    def search_papers(self, keywords: List[str], max_results: int = 10, days_back: int = 7) -> List[Paper]:
        """
        根据关键词搜索arXiv论文

        Args:
            keywords: 搜索关键词列表
            max_results: 最大结果数
            days_back: 回溯天数

        Returns:
            论文列表
        """
        # 构建搜索查询
        query_parts = []
        for keyword in keywords:
            # 使用all:字段在标题、摘要和作者中搜索
            query_parts.append(f'all:"{keyword}"')

        # 使用AND关系，要求论文同时包含所有关键词
        search_query = " AND ".join(query_parts)

        # 根据需要调整时间范围
        # 如果请求更多结果，扩大时间范围
        if max_results > 20:
            days_back = min(days_back * 2, 30)  # 最多回溯30天

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # 构建完整的查询
        full_query = f'({search_query}) AND submittedDate:[{start_date.strftime("%Y%m%d%H%M%S")} TO {end_date.strftime("%Y%m%d%H%M%S")}]'

        params = {
            'search_query': full_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }

        try:
            logger.info(f"搜索查询: {full_query}")
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            # 解析Atom feed
            feed = feedparser.parse(response.content)

            papers = []
            for entry in feed.entries:
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)

            logger.info(f"找到 {len(papers)} 篇新论文")
            return papers

        except requests.RequestException as e:
            logger.error(f"请求arXiv API失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析arXiv响应失败: {e}")
            return []

    def _parse_entry(self, entry) -> Optional[Paper]:
        """解析arXiv条目"""
        try:
            # 提取作者信息
            authors = []
            if hasattr(entry, 'authors'):
                authors = [author.name for author in entry.authors]

            # 提取分类信息
            categories = []
            if hasattr(entry, 'tags'):
                categories = [tag.term for tag in entry.tags]

            # 提取arXiv ID
            arxiv_id = entry.id.split('/')[-1]

            # 提取发布日期
            published_date = datetime.now()
            if hasattr(entry, 'published'):
                if isinstance(entry.published, str):
                    published_date = datetime.fromisoformat(entry.published.replace('Z', '+00:00'))
                else:
                    published_date = entry.published
            elif hasattr(entry, 'updated'):
                if isinstance(entry.updated, str):
                    published_date = datetime.fromisoformat(entry.updated.replace('Z', '+00:00'))
                else:
                    published_date = entry.updated

            # 构建PDF URL
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            return Paper(
                title=entry.title.strip(),
                authors=authors,
                abstract=entry.summary.strip(),
                arxiv_id=arxiv_id,
                published_date=published_date,
                categories=categories,
                pdf_url=pdf_url
            )

        except Exception as e:
            logger.error(f"解析论文条目失败: {e}")
            return None

    def scrape_and_save(self, keywords: List[str], max_papers: int = None, incremental: bool = True) -> int:
        """
        爬取并保存论文

        Args:
            keywords: 关键词列表
            max_papers: 最大论文数量
            incremental: 是否支持增量爬取（如果当天已有论文，继续爬取更多）

        Returns:
            成功保存的论文数量
        """
        if max_papers is None:
            max_papers = settings.MAX_PAPERS_PER_DAY

        # 如果启用了增量爬取，检查当天已保存的论文数量
        if incremental:
            today_papers_count = self._get_today_papers_count()
            logger.info(f"今天已保存 {today_papers_count} 篇论文")

            # 如果今天已有论文，则继续爬取直到达到max_papers的倍数
            # 例如：已有10篇，目标再增加10篇，总共20篇
            target_total = ((today_papers_count // max_papers) + 1) * max_papers
            search_limit = target_total - today_papers_count

            # 确保至少搜索max_papers篇
            search_limit = max(search_limit, max_papers)

            logger.info(f"增量爬取模式：目标再增加 {search_limit} 篇论文")
        else:
            search_limit = max_papers

        papers = self.search_papers(keywords, search_limit)
        saved_count = 0

        for paper in papers:
            if self.db.save_paper(paper):
                saved_count += 1
                logger.info(f"保存论文: {paper.title} (ID: {paper.arxiv_id})")
            else:
                logger.debug(f"论文已存在，跳过: {paper.arxiv_id}")

        logger.info(f"成功保存 {saved_count} 篇论文")
        return saved_count

    def _get_today_papers_count(self) -> int:
        """获取今天已保存的论文数量"""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM papers
                    WHERE DATE(created_at) = DATE('now')
                """)
                return cursor.fetchone()[0] or 0
        except Exception as e:
            logger.error(f"获取今日论文数量失败: {e}")
            return 0

    def scrape_more_papers(self, keywords: List[str], additional_count: int = 10) -> int:
        """
        专门用于增量爬取更多论文的方法

        Args:
            keywords: 关键词列表
            additional_count: 希望额外爬取的论文数量

        Returns:
            成功保存的论文数量
        """
        logger.info(f"开始增量爬取，目标增加 {additional_count} 篇论文")

        # 扩大搜索范围以获得更多候选论文
        # 搜索更多的论文来确保有足够的新论文
        search_limit = additional_count * 3  # 搜索3倍的量，确保有足够的新论文

        # 对于增量爬取，扩大时间范围来找到更多论文
        papers = self.search_papers(keywords, search_limit, days_back=14)
        saved_count = 0

        for paper in papers:
            if self.db.save_paper(paper):
                saved_count += 1
                logger.info(f"保存论文: {paper.title} (ID: {paper.arxiv_id})")

                # 达到目标数量就停止
                if saved_count >= additional_count:
                    break
            else:
                logger.debug(f"论文已存在，跳过: {paper.arxiv_id}")

        logger.info(f"增量爬取完成，成功保存 {saved_count} 篇论文")
        return saved_count

    def get_trending_topics(self, days: int = 7) -> List[str]:
        """
        获取最近的热门主题（基于出现频率最高的关键词）

        Args:
            days: 分析的天数

        Returns:
            热门主题列表
        """
        papers = self.db.get_recent_papers(days)

        # 简单的关键词提取（可以后续改进为更复杂的NLP方法）
        from collections import Counter
        import re

        all_words = []
        for paper in papers:
            # 从标题和摘要中提取单词
            text = f"{paper.title} {paper.abstract}".lower()
            words = re.findall(r'\b\w+\b', text)
            # 过滤掉常见词汇
            words = [word for word in words if len(word) > 3 and word not in
                     ['this', 'that', 'with', 'from', 'they', 'have', 'been', 'will', 'are', 'our', 'can']]
            all_words.extend(words)

        word_freq = Counter(all_words)
        return [word for word, count in word_freq.most_common(10)]