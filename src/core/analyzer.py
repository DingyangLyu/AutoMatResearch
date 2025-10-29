import openai
from typing import List, Optional
import logging
from src.data.database import Paper, DatabaseManager
from config.settings import settings

logger = logging.getLogger(__name__)

class DeepSeekAnalyzer:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.db = DatabaseManager(settings.DATABASE_URL.replace("sqlite:///", ""))

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
        基于最近的论文生成研究洞察

        Args:
            days: 分析的天数

        Returns:
            研究洞察文本
        """
        try:
            papers = self.db.get_recent_papers(days)
            if not papers:
                return "没有找到最近的论文数据。"

            # 准备论文信息用于分析
            papers_info = []
            for paper in papers[:10]:  # 限制为最近10篇
                papers_info.append({
                    'title': paper.title,
                    'summary': paper.summary or paper.abstract[:500],
                    'categories': paper.categories
                })

            prompt = f"""
基于最近{days}天的以下研究论文，请分析当前的研究趋势和重要发现：

{papers_info}

请从以下几个方面进行分析：
1. 主要研究趋势和热点
2. 重要的技术突破或创新点
3. 研究方向的未来展望
4. 值得关注的研究团队或作者

请用中文回答，控制在500字以内。
"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的研究趋势分析师，擅长从学术论文中提取有价值的洞察。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.5
            )

            insights = response.choices[0].message.content.strip()
            logger.info("成功生成研究洞察")
            return insights

        except Exception as e:
            logger.error(f"生成研究洞察失败: {e}")
            return "生成研究洞察时出现错误。"

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