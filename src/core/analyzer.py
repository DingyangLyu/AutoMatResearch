import openai
import os
from typing import List, Optional
import logging
from src.data.database import Paper, DatabaseManager
from config.settings import settings
from pathlib import Path

logger = logging.getLogger(__name__)

class DeepSeekAnalyzer:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        # 使用绝对路径确保数据库连接一致性
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            # 如果是相对路径，转换为基于项目根目录的绝对路径
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / db_path
        self.db = DatabaseManager(str(db_path))

    def generate_summary(self, paper: Paper) -> Optional[str]:
        """
        使用DeepSeek生成论文摘要

        Args:
            paper: 论文对象

        Returns:
            生成的摘要文本
        """
        try:
            prompt = f"""
请为以下论文生成一个简洁的中文摘要，突出其主要贡献、方法和结论：

标题：{paper.title}

作者：{', '.join(paper.authors)}

摘要：{paper.abstract}

分类：{', '.join(paper.categories)}

请用中文回答，控制在200-300字以内。
"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的学术论文分析师，擅长提取论文的核心内容和贡献。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"成功生成论文 {paper.arxiv_id} 的摘要")
            return summary

        except Exception as e:
            logger.error(f"生成论文摘要失败 {paper.arxiv_id}: {e}")
            return None

    def analyze_papers_batch(self, papers: List[Paper]) -> List[Paper]:
        """
        批量分析论文并生成摘要

        Args:
            papers: 论文列表

        Returns:
            已分析的论文列表
        """
        analyzed_papers = []

        for i, paper in enumerate(papers):
            logger.info(f"分析论文进度: {i+1}/{len(papers)} - {paper.title[:50]}...")

            # 检查是否已有摘要
            if not paper.summary:
                summary = self.generate_summary(paper)
                if summary:
                    paper.summary = summary
                    # 更新数据库
                    self._update_paper_summary(paper.arxiv_id, summary)

            analyzed_papers.append(paper)

            # 添加延迟以避免API限制
            import time
            time.sleep(1)

        return analyzed_papers

    def _update_paper_summary(self, arxiv_id: str, summary: str):
        """更新数据库中的论文摘要"""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute(
                    "UPDATE papers SET summary = ? WHERE arxiv_id = ?",
                    (summary, arxiv_id)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"更新论文摘要失败 {arxiv_id}: {e}")

    def get_research_insights(self, days: int = 7) -> str:
        """
        基于最近的论文生成研究洞察（智能缓存版本）

        Args:
            days: 分析的天数

        Returns:
            研究洞察文本
        """
        cache_key = f"insights_{days}"

        try:
            # 获取当前数据的哈希值
            current_hash = self.db.get_data_hash(days)

            # 检查是否有缓存的洞察且数据未变化
            cached_data = self.db.get_insights_cache(cache_key)

            if cached_data and cached_data.get('data_hash') == current_hash:
                logger.info(f"使用缓存的洞察数据，数据未变化: {cache_key}")
                return cached_data['insights']

            logger.info(f"数据已变化或无缓存，重新生成洞察: {cache_key}")

            # 数据变化了，需要重新生成洞察
            papers = self.db.get_recent_papers(days)
            if not papers:
                return "没有找到最近的论文数据。"

            # 准备论文信息用于分析
            papers_info = []
            # 按类别分组分析，确保覆盖不同的研究领域
            papers_to_analyze = papers if len(papers) <= 25 else papers[:25]  # 最多分析25篇
            for i, paper in enumerate(papers_to_analyze):
                papers_info.append({
                    'index': i + 1,
                    'title': paper.title,
                    'summary': paper.summary or paper.abstract[:400],  # 稍微缩短摘要
                    'categories': paper.categories,
                    'authors': paper.authors[:3] if paper.authors else []  # 只取前3个作者
                })

            prompt = f"""
你是一个专业的学术分析师。请基于最近{days}天的{len(papers_to_analyze)}篇研究论文进行分析：

论文数据：
{papers_info}

请提供深入的研究洞察分析，包括：

1. **研究趋势分析**：识别当前最主要的研究热点和趋势方向
2. **技术突破点**：找出重要的技术创新和方法突破
3. **跨学科融合**：识别不同研究领域之间的交叉融合趋势
4. **未来展望**：基于当前研究趋势预测未来发展方向
5. **关键研究团队**：识别活跃的研究机构和作者群体

要求：
- 用中文回答
- 提供具体、有深度的分析
- 字数控制在800-1200字之间
- 基于实际论文内容进行分析，不要泛泛而谈
"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的研究趋势分析师，擅长从学术论文中提取有价值的洞察。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,  # 增加token限制以支持更长的分析
                temperature=0.3,   # 降低随机性，提高稳定性
                timeout=45         # 设置45秒超时
            )

            insights = response.choices[0].message.content.strip()
            logger.info("成功生成研究洞察")

            # 同时获取热门主题并保存到缓存
            try:
                trending_topics = self.get_trending_topics(days)

                # 保存到数据库缓存
                self.db.save_insights_cache(cache_key, current_hash, insights, trending_topics)
                logger.info(f"洞察已缓存到数据库: {cache_key}")

            except Exception as e:
                logger.warning(f"获取热门主题失败: {e}")
                # 保存到内存缓存作为备选
                global _insights_cache
                _cache_insights(cache_key, insights, [])

            return insights

        except Exception as e:
            logger.error(f"生成研究洞察失败: {e}")
            return f"生成洞察失败: {str(e)}"

    def compare_papers(self, paper_ids: List[str]) -> str:
        """
        比较多篇论文的异同

        Args:
            paper_ids: 论文arXiv ID列表

        Returns:
            比较分析结果
        """
        try:
            papers = []
            for paper_id in paper_ids:
                # 从数据库获取论文
                import sqlite3
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT title, abstract, summary FROM papers WHERE arxiv_id = ?",
                        (paper_id,)
                    )
                    result = cursor.fetchone()
                    if result:
                        papers.append({
                            'id': paper_id,
                            'title': result[0],
                            'abstract': result[1],
                            'summary': result[2] or result[1][:500]
                        })

            if len(papers) < 2:
                return "需要至少两篇论文进行比较。"

            prompt = f"""
请比较分析以下几篇论文的异同点：

{papers}

请从以下几个方面进行比较：
1. 研究目标和问题的异同
2. 方法论的区别
3. 主要贡献和创新点
4. 优缺点对比
5. 适用场景的差异

请用中文回答，结构化输出。
"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的学术比较分析师，擅长深入分析和比较不同研究论文。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )

            comparison = response.choices[0].message.content.strip()
            logger.info(f"成功完成 {len(papers)} 篇论文的比较分析")
            return comparison

        except Exception as e:
            logger.error(f"论文比较分析失败: {e}")
            return "论文比较分析时出现错误。"