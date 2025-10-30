import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote
import logging
import sys
import re
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.database import Paper, DatabaseManager
from config.settings import settings

logger = logging.getLogger(__name__)

class ArxivScraper:
    def __init__(self, keyword: str = None):
        self.base_url = "http://export.arxiv.org/api/query"
        self.arxiv_base_url = "https://arxiv.org/abs/"
        self.keyword = keyword
        # 根据关键词获取数据库管理器
        if keyword:
            from src.data.keyword_manager import keyword_manager
            db_manager = keyword_manager.get_database_manager(keyword)
            self.db = db_manager
        else:
            self.db = DatabaseManager(settings.database_path)
        # 设置请求头，模拟浏览器
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_submission_date_from_page(self, arxiv_id: str) -> Optional[datetime]:
        """
        从arXiv详情页面获取准确的提交日期

        Args:
            arxiv_id: arXiv论文ID

        Returns:
            提交日期datetime对象，如果获取失败返回None
        """
        try:
            url = f"{self.arxiv_base_url}{arxiv_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # 使用正则表达式查找 "Submitted on" 日期
            # 匹配模式：Submitted on [day] [month] [year]
            patterns = [
                r'Submitted on (\d{1,2})\s+(\w+)\s+(\d{4})',
                r'Submitted\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
                r'(\d{1,2})\s+(\w+)\s+(\d{4})\s*\(Submitted',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    day, month_str, year = matches[0]

                    # 月份映射
                    month_map = {
                        'january': 1, 'jan': 1,
                        'february': 2, 'feb': 2,
                        'march': 3, 'mar': 3,
                        'april': 4, 'apr': 4,
                        'may': 5,
                        'june': 6, 'jun': 6,
                        'july': 7, 'jul': 7,
                        'august': 8, 'aug': 8,
                        'september': 9, 'sep': 9, 'sept': 9,
                        'october': 10, 'oct': 10,
                        'november': 11, 'nov': 11,
                        'december': 12, 'dec': 12
                    }

                    month = month_map.get(month_str.lower())
                    if month:
                        submission_date = datetime(int(year), month, int(day))
                        logger.info(f"从arXiv页面获取提交日期: {arxiv_id} -> {submission_date.strftime('%Y-%m-%d')}")
                        return submission_date
                    else:
                        logger.warning(f"无法解析月份: {month_str}")

            # 如果正则表达式没找到，尝试查找其他日期模式
            # 查找页面中的任何日期信息作为备选
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            ]

            for pattern in date_patterns:
                matches = re.findall(pattern, response.text)
                if matches:
                    # 取第一个匹配的日期
                    date_str = matches[0]
                    if '-' in date_str:  # YYYY-MM-DD格式
                        try:
                            submission_date = datetime.strptime(date_str, '%Y-%m-%d')
                            logger.info(f"从arXiv页面获取日期(备选): {arxiv_id} -> {submission_date.strftime('%Y-%m-%d')}")
                            return submission_date
                        except ValueError:
                            continue
                    elif '/' in date_str:  # MM/DD/YYYY格式
                        try:
                            month, day, year = date_str.split('/')
                            submission_date = datetime(int(year), int(month), int(day))
                            logger.info(f"从arXiv页面获取日期(备选): {arxiv_id} -> {submission_date.strftime('%Y-%m-%d')}")
                            return submission_date
                        except ValueError:
                            continue

            logger.warning(f"无法从arXiv页面找到提交日期: {arxiv_id}")
            return None

        except requests.RequestException as e:
            logger.error(f"请求arXiv页面失败 {arxiv_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"解析arXiv页面时出错 {arxiv_id}: {e}")
            return None

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
            # 检查关键词是否已经包含搜索字段前缀（如 all:, ti:, au: 等）
            if any(keyword.startswith(prefix) for prefix in ['all:', 'ti:', 'au:', 'cat:']):
                # 如果已经包含字段前缀，直接使用（支持复杂查询语法）
                query_parts.append(f'({keyword})')
            else:
                # 使用all:字段在标题、摘要和作者中搜索
                query_parts.append(f'all:"{keyword}"')

        # 使用AND关系，要求论文同时包含所有关键词
        search_query = " AND ".join(query_parts)

        # 根据需要调整时间范围和搜索策略
        if max_results > 30:
            # 对于大量请求，扩大时间范围并分批搜索
            days_back = min(days_back * 3, 90)  # 最多回溯90天
        elif max_results > 20:
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

            # 提取发布日期 - 优先从arXiv详情页面获取准确的提交日期
            published_date = None

            # 方法1: 从arXiv详情页面获取准确的提交日期（最准确）
            try:
                page_date = self.get_submission_date_from_page(arxiv_id)
                if page_date:
                    published_date = page_date
                    logger.info(f"从arXiv页面获取准确提交日期: {arxiv_id} -> {published_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                logger.warning(f"从arXiv页面获取日期失败 {arxiv_id}: {e}")

            # 方法2: 如果页面获取失败，尝试从arXiv ID解析年月信息
            if published_date is None:
                try:
                    # arXiv ID格式: YYMM.xxxxxx 或 YYMM.Nxxxxx
                    arxiv_parts = arxiv_id.split('.')
                    if len(arxiv_parts) > 0:
                        date_part = arxiv_parts[0]
                        if len(date_part) == 4 and date_part.isdigit():
                            year = 2000 + int(date_part[:2])
                            month = int(date_part[2:4])
                            published_date = datetime(year, month, 1)
                            logger.info(f"从arXiv ID解析发表日期: {arxiv_id} -> {published_date.strftime('%Y-%m-%d')}")
                except (ValueError, IndexError) as e:
                    logger.warning(f"无法从arXiv ID解析日期 {arxiv_id}: {e}")

            # 方法3: 如果上述方法都失败，尝试从API字段获取
            if published_date is None:
                logger.warning(f"无法获取准确日期，尝试从API字段获取日期: {arxiv_id}")

                # 检查是否有更详细的发布信息
                if hasattr(entry, 'published'):
                    try:
                        if isinstance(entry.published, str):
                            # 处理带时区的日期字符串
                            if 'T' in entry.published:
                                api_date = datetime.fromisoformat(entry.published.replace('Z', '+00:00'))
                            else:
                                # 处理简化的日期格式
                                api_date = datetime.strptime(entry.published, '%Y-%m-%d')
                        else:
                            api_date = entry.published

                        # 检查API日期是否合理（不应该太接近当前时间）
                        now = datetime.now()
                        if (now - api_date).days > 1:  # 如果API日期至少比当前时间早1天
                            published_date = api_date
                            logger.info(f"使用API发布日期: {arxiv_id} -> {published_date.strftime('%Y-%m-%d')}")
                        else:
                            logger.warning(f"API发布日期过于接近当前时间，可能不准确: {api_date}")
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"无法解析发布日期 {entry.published}: {e}")

                # 如果published字段不可用，尝试updated字段
                if published_date is None and hasattr(entry, 'updated'):
                    try:
                        if isinstance(entry.updated, str):
                            # 处理带时区的日期字符串
                            if 'T' in entry.updated:
                                api_date = datetime.fromisoformat(entry.updated.replace('Z', '+00:00'))
                            else:
                                # 处理简化的日期格式
                                api_date = datetime.strptime(entry.updated, '%Y-%m-%d')
                        else:
                            api_date = entry.updated

                        # 检查API日期是否合理
                        now = datetime.now()
                        if (now - api_date).days > 1:
                            published_date = api_date
                            logger.info(f"使用API更新日期: {arxiv_id} -> {published_date.strftime('%Y-%m-%d')}")
                        else:
                            logger.warning(f"API更新日期过于接近当前时间，可能不准确: {api_date}")
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"无法解析更新日期 {entry.updated}: {e}")

            # 最后的备选方案：使用当前时间（但这应该很少发生）
            if published_date is None:
                logger.error(f"所有方法都无法确定论文 {arxiv_id} 的发布日期，使用当前时间")
                published_date = datetime.now()

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

        # 增量爬取逻辑：从最新论文的前一天开始，向过去搜索
        try:
            latest_paper_date = self.db.get_latest_paper_date()
            if latest_paper_date:
                # 增量爬取应该搜索比最新论文更早的论文
                from datetime import timedelta

                # 计算搜索的起始日期（最新论文的前一天）
                search_end_date = latest_paper_date - timedelta(days=1)

                # 根据请求数量决定搜索多长时间范围
                if additional_count <= 10:
                    # 小量请求：搜索前7天
                    search_start_date = search_end_date - timedelta(days=7)
                    days_back = 8  # 总共8天范围
                elif additional_count <= 50:
                    # 中量请求：搜索前30天
                    search_start_date = search_end_date - timedelta(days=30)
                    days_back = 31
                else:
                    # 大量请求：搜索前90天
                    search_start_date = search_end_date - timedelta(days=90)
                    days_back = 91

                logger.info(f"增量爬取：搜索范围 {search_start_date.date()} 到 {search_end_date.date()}（最新论文：{latest_paper_date.date()}）")
            else:
                # 数据库为空，搜索最近的论文
                from datetime import timedelta
                search_end_date = datetime.now()
                search_start_date = search_end_date - timedelta(days=7)
                days_back = 7
                logger.info("数据库为空，搜索最近7天的论文")
        except Exception as e:
            logger.warning(f"获取最新论文日期失败：{e}，使用默认策略")
            from datetime import timedelta
            search_end_date = datetime.now()
            search_start_date = search_end_date - timedelta(days=7)
            days_back = 7

        # 根据请求数量动态调整搜索策略
        if additional_count <= 10:
            search_limit = min(additional_count * 5, 50)  # 小量请求：5倍搜索
        elif additional_count <= 50:
            search_limit = min(additional_count * 3, 150)  # 中量请求：3倍搜索
        else:
            search_limit = min(additional_count * 2, 300)  # 大量请求：2倍搜索

        logger.info(f"搜索策略：目标 {additional_count} 篇，搜索 {search_limit} 篇候选论文")

        # 实现多轮搜索，自动扩展时间范围
        all_papers = []
        current_search_start_date = search_start_date
        current_search_end_date = search_end_date
        max_expansion_rounds = 5  # 最多扩展5轮时间范围
        expansion_days = 7  # 每轮扩展7天

        for round_num in range(max_expansion_rounds):
            logger.info(f"=== 第 {round_num + 1} 轮搜索：{current_search_start_date.date()} 到 {current_search_end_date.date()} ===")

            # 使用连续搜索在这个时间范围内搜索
            round_papers = self._search_in_time_range(
                keywords=keywords,
                start_date=current_search_start_date,
                end_date=current_search_end_date,
                search_limit=search_limit
            )

            # 过滤掉已存在的论文
            new_papers = []
            for paper in round_papers:
                if not self.db.paper_exists(paper.arxiv_id):
                    new_papers.append(paper)

            logger.info(f"第 {round_num + 1} 轮找到 {len(new_papers)} 篇新论文（总共搜索到 {len(round_papers)} 篇）")

            all_papers.extend(new_papers)

            # 如果已经获得足够的新论文就停止
            if len(all_papers) >= additional_count:
                logger.info(f"已找到足够的新论文 ({len(all_papers)} >= {additional_count})，停止搜索")
                break

            # 如果这轮没有找到新论文，或者找到的不够，继续扩展时间范围
            if len(new_papers) == 0 or len(all_papers) < additional_count:
                if round_num < max_expansion_rounds - 1:  # 不是最后一轮
                    # 扩展时间范围：向更早的时间扩展
                    current_search_end_date = current_search_start_date - timedelta(days=1)
                    current_search_start_date = current_search_start_date - timedelta(days=expansion_days)
                    logger.info(f"第 {round_num + 1} 轮未找到足够新论文，扩展时间范围到 {current_search_start_date.date()} 到 {current_search_end_date.date()}")
                else:
                    logger.info("已达到最大搜索轮数，停止搜索")
            else:
                # 找到了一些新论文，但还不够，可以继续在当前时间范围内搜索更多批次
                logger.info(f"第 {round_num + 1} 轮找到 {len(new_papers)} 篇新论文，总共 {len(all_papers)} 篇")

        logger.info(f"搜索完成，总共找到 {len(all_papers)} 篇新候选论文")
        saved_count = 0

        for paper in all_papers:
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

    def _search_in_time_range(self, keywords: List[str], start_date: datetime, end_date: datetime, search_limit: int) -> List[Paper]:
        """
        在指定时间范围内进行连续搜索

        Args:
            keywords: 搜索关键词列表
            start_date: 搜索开始日期
            end_date: 搜索结束日期
            search_limit: 搜索限制数量

        Returns:
            找到的论文列表
        """
        all_papers = []
        batch_size = 30  # arXiv API单次最多返回30篇

        # 计算需要多少批次
        num_batches = (search_limit + batch_size - 1) // batch_size

        for batch in range(num_batches):
            start_index = batch * batch_size
            batch_limit = min(batch_size, search_limit - start_index)

            logger.debug(f"执行第 {batch + 1}/{num_batches} 批连续搜索，从索引 {start_index} 开始，获取 {batch_limit} 篇")

            # 使用连续搜索
            batch_papers = self.search_papers_continuous_with_range(
                keywords=keywords,
                max_results=batch_limit,
                start_index=start_index,
                start_date=start_date,
                end_date=end_date
            )

            if not batch_papers:
                logger.debug("本批次没有找到论文，停止本轮搜索")
                break

            all_papers.extend(batch_papers)

            # 如果本批次找到的论文少于请求数量，可能已经到了搜索结果的末尾
            if len(batch_papers) < batch_limit:
                logger.debug(f"本批次返回论文数量 ({len(batch_papers)}) 少于请求数量 ({batch_limit})，已到达搜索结果末尾")
                break

            # 避免请求过于频繁
            import time
            time.sleep(1)

        logger.debug(f"时间范围 {start_date.date()} 到 {end_date.date()} 搜索完成，找到 {len(all_papers)} 篇论文")
        return all_papers

    def search_papers_continuous_with_range(self, keywords: List[str], max_results: int = 30,
                                         start_index: int = 0, start_date: datetime = None,
                                         end_date: datetime = None) -> List[Paper]:
        """
        使用arXiv API的start参数进行连续搜索，支持自定义时间范围

        Args:
            keywords: 搜索关键词列表
            max_results: 最大结果数
            start_index: 开始索引（用于分页）
            start_date: 搜索开始日期
            end_date: 搜索结束日期

        Returns:
            论文列表
        """
        # 构建搜索查询
        query_parts = []
        for keyword in keywords:
            # 检查关键词是否已经包含搜索字段前缀（如 all:, ti:, au: 等）
            if any(keyword.startswith(prefix) for prefix in ['all:', 'ti:', 'au:', 'cat:']):
                # 如果已经包含字段前缀，直接使用（支持复杂查询语法）
                query_parts.append(f'({keyword})')
            else:
                # 使用all:字段在标题、摘要和作者中搜索
                query_parts.append(f'all:"{keyword}"')

        # 使用AND关系，要求论文同时包含所有关键词
        search_query = " AND ".join(query_parts)

        # 使用自定义时间范围
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # 构建完整的查询
        full_query = f'({search_query}) AND submittedDate:[{start_date.strftime("%Y%m%d%H%M%S")} TO {end_date.strftime("%Y%m%d%H%M%S")}]'

        params = {
            'search_query': full_query,
            'start': start_index,  # 关键：使用start参数实现连续搜索
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'  # 按提交日期降序排列，确保最新的在前
        }

        logger.debug(f"连续搜索查询: {full_query}")
        logger.debug(f"搜索参数: start={start_index}, max_results={max_results}")

        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)
            papers = []

            for entry in feed.entries:
                try:
                    # 提取作者信息
                    authors = []
                    if hasattr(entry, 'authors') and entry.authors:
                        authors = [author.name for author in entry.authors]
                    elif hasattr(entry, 'author'):
                        authors = [entry.author]

                    # 提取分类信息
                    categories = []
                    if hasattr(entry, 'tags') and entry.tags:
                        categories = [tag.term for tag in entry.tags]

                    # 从arXiv ID中提取准确的提交日期
                    arxiv_id = entry.id.split('/')[-1]
                    published_date = self.get_submission_date_from_page(arxiv_id)

                    # 如果无法从页面获取日期，使用entry中的日期作为备用
                    if not published_date:
                        if hasattr(entry, 'published'):
                            published_date = entry.published
                        elif hasattr(entry, 'updated'):
                            published_date = entry.updated
                        else:
                            published_date = datetime.now()
                        logger.warning(f"无法从页面获取日期，使用备用日期: {arxiv_id} -> {published_date}")

                    paper = Paper(
                        title=entry.title,
                        authors=authors,
                        abstract=getattr(entry, 'summary', ''),
                        arxiv_id=arxiv_id,
                        published_date=published_date,
                        categories=categories,
                        pdf_url=entry.link.replace('/abs/', '/pdf/') + '.pdf'
                    )
                    papers.append(paper)

                except Exception as e:
                    logger.error(f"解析论文条目失败: {e}")
                    continue

            logger.info(f"连续搜索完成: 索引 {start_index}-{start_index + len(papers)}，找到 {len(papers)} 篇论文")
            return papers

        except requests.exceptions.RequestException as e:
            logger.error(f"连续搜索请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"连续搜索失败: {e}")
            return []

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
        return [word for word, _ in word_freq.most_common(10)]