import openai
import os
from typing import List, Optional
import logging
from src.data.database import Paper, DatabaseManager
from config.settings import settings
from pathlib import Path

logger = logging.getLogger(__name__)

class DeepSeekAnalyzer:
    def __init__(self, keyword: str = None):
        self.client = openai.OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.keyword = keyword
        # 根据关键词获取数据库管理器
        if keyword:
            from src.data.keyword_manager import keyword_manager
            db_manager = keyword_manager.get_database_manager(keyword)
            self.db = db_manager
        else:
            # 使用绝对路径确保数据库连接一致性
            db_path = settings.DATABASE_URL.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                # 如果是相对路径，转换为基于项目根目录的绝对路径
                project_root = Path(__file__).parent.parent.parent
                db_path = project_root / db_path
            self.db = DatabaseManager(str(db_path))
        # 确保insights_cache表存在
        self._init_insights_cache_table()

        # 添加锁机制防止并发生成洞察
        self._generating_insights = set()  # 存储正在生成的洞察键

    def _init_insights_cache_table(self):
        """初始化洞察缓存表"""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
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
        except Exception as e:
            logger.error(f"初始化insights_cache表失败: {e}")

    def generate_summary(self, paper: Paper) -> Optional[str]:
        """
        使用DeepSeek生成论文摘要 - 改进版本，确保翻译完整性

        Args:
            paper: 论文对象

        Returns:
            生成的摘要文本
        """
        try:
            # 根据摘要长度动态调整token限制
            abstract_length = len(paper.abstract)
            if abstract_length < 500:
                max_tokens = 800  # 短摘要使用较多token
            elif abstract_length < 1000:
                max_tokens = 1200  # 中等长度摘要
            else:
                max_tokens = 2000  # 长摘要使用最大token限制

            # 改进的提示词，明确要求完整性
            prompt = f"""
请为以下论文生成一个完整、准确的中文摘要，确保覆盖原文所有关键信息：

标题：{paper.title}

作者：{', '.join(paper.authors)}

英文摘要：{paper.abstract}

分类：{', '.join(paper.categories)}

要求：
1. 必须完整翻译和概括原文所有重要信息，不能遗漏关键内容
2. 突出研究背景、主要贡献、方法创新、实验结果和结论
3. 使用专业的学术中文表达，术语准确
4. 根据原文长度，中文摘要应在300-800字之间
5. 确保技术细节和方法描述的完整性
6. 如果原文很长，请适当增加摘要长度以确保信息完整性
7. 不要使用markdown格式的文本,自然语言即可

请提供完整的中文摘要：
"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是专业的学术论文翻译和分析师，擅长将英文科技论文准确、完整地翻译成中文，并确保所有技术细节和专业术语的正确性。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.5,  # 稍微提高温度以增加表达的丰富性
                top_p=0.9,  # 添加top_p参数控制输出的多样性
                frequency_penalty=0.1,  # 避免重复
                presence_penalty=0.1  # 鼓励引入新概念
            )

            summary = response.choices[0].message.content.strip()

            # 检查翻译完整性 - 如果摘要过短，尝试重新生成
            if len(summary) < 100 and abstract_length > 500:
                logger.warning(f"论文 {paper.arxiv_id} 的摘要可能不完整，尝试重新生成")
                return self._regenerate_summary(paper, max_tokens)

            logger.info(f"成功生成论文 {paper.arxiv_id} 的摘要，长度：{len(summary)}字符")
            return summary

        except Exception as e:
            logger.error(f"生成论文摘要失败 {paper.arxiv_id}: {e}")
            return None

    def analyze_papers_batch(self, papers: List[Paper]) -> List[Paper]:
        """
        批量分析论文并生成摘要 - 改进版本，确保翻译质量

        Args:
            papers: 论文列表

        Returns:
            已分析的论文列表
        """
        analyzed_papers = []
        incomplete_count = 0
        retry_count = 0

        for i, paper in enumerate(papers):
            logger.info(f"分析论文进度: {i+1}/{len(papers)} - {paper.title[:50]}...")

            # 检查是否已有摘要
            if not paper.summary:
                summary = self.generate_summary(paper)
                if summary:
                    # 检查摘要完整性
                    if len(summary) < 150 and len(paper.abstract) > 600:
                        logger.warning(f"论文 {paper.arxiv_id} 摘要可能不完整，尝试重新生成")
                        retry_summary = self._regenerate_summary(paper, 1500)
                        if retry_summary and len(retry_summary) > len(summary):
                            summary = retry_summary
                            retry_count += 1

                    paper.summary = summary
                    # 更新数据库
                    self._update_paper_summary(paper.arxiv_id, summary)

                    # 记录摘要质量统计
                    summary_length = len(summary)
                    abstract_length = len(paper.abstract)
                    ratio = summary_length / abstract_length if abstract_length > 0 else 0

                    if ratio < 0.2 and abstract_length > 500:
                        logger.warning(f"论文 {paper.arxiv_id} 摘要比例偏低：{ratio:.2f} ({summary_length}/{abstract_length})")
                        incomplete_count += 1
                    else:
                        logger.info(f"论文 {paper.arxiv_id} 摘要生成成功，长度比例：{ratio:.2f}")
                else:
                    logger.error(f"论文 {paper.arxiv_id} 摘要生成失败")

            analyzed_papers.append(paper)

            # 添加延迟以避免API限制 - 根据摘要长度调整延迟
            import time
            delay = min(2, 1 + len(paper.abstract) / 5000)  # 长摘要增加延迟
            time.sleep(delay)

        # 报告批量分析结果
        total_analyzed = len([p for p in analyzed_papers if p.summary])
        logger.info(f"批量分析完成：共{len(papers)}篇，成功{total_analyzed}篇，重新生成{retry_count}篇，可能不完整{incomplete_count}篇")

        return analyzed_papers

    def _update_paper_summary(self, arxiv_id: str, summary: str):
        """更新数据库中的论文摘要"""
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.execute(
                    "UPDATE papers SET summary = ? WHERE arxiv_id = ?",
                    (summary, arxiv_id)
                )
                conn.commit()

                # 检查是否真正更新了记录
                if cursor.rowcount > 0:
                    logger.info(f"成功更新论文摘要: {arxiv_id}")
                    return True
                else:
                    logger.warning(f"未找到要更新的论文: {arxiv_id}")
                    return False

        except Exception as e:
            logger.error(f"更新论文摘要失败 {arxiv_id}: {e}")
            return False

    def _regenerate_summary(self, paper: Paper, max_tokens: int) -> Optional[str]:
        """
        重新生成摘要 - 用于处理不完整的翻译

        Args:
            paper: 论文对象
            max_tokens: token限制

        Returns:
            重新生成的摘要
        """
        try:
            # 使用更详细的提示词重新生成
            prompt = f"""
以下论文的英文摘要较长，请确保完整翻译和概括所有重要信息：

标题：{paper.title}

英文摘要：{paper.abstract}

要求：
1. 必须完整覆盖原文所有关键信息点
2. 详细描述研究背景、问题、方法、实验和结论
3. 不能遗漏任何重要的技术细节
4. 使用准确的专业术语和学术表达
5. 摘要长度应充分反映原文内容的丰富程度

请提供完整详细的中文摘要：
"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是专业的学术论文翻译专家，确保将英文论文内容完整、准确地翻译成中文，不遗漏任何重要信息。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7,  # 提高温度以增加详细程度
                top_p=0.95
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"重新生成论文 {paper.arxiv_id} 的摘要，长度：{len(summary)}字符")
            return summary

        except Exception as e:
            logger.error(f"重新生成摘要失败 {paper.arxiv_id}: {e}")
            return None

    def get_research_insights(self, days: int = 7) -> str:
        """
        基于最近的论文生成研究洞察（智能缓存版本）
        如果数据库未更新，使用永久缓存；如果数据库更新了，重新生成并缓存

        Args:
            days: 分析的天数

        Returns:
            研究洞察文本
        """
        cache_key = f"insights_{days}"

        try:
            # 检查是否正在生成洞察，避免重复生成
            if cache_key in self._generating_insights:
                logger.info(f"洞察 {cache_key} 正在生成中，返回现有缓存")
                cached_data = self.db.get_insights_cache(cache_key)
                if cached_data:
                    return cached_data['insights']
                else:
                    return "洞察正在生成中，请稍后刷新..."

            # 获取当前数据的哈希值
            current_hash = self.db.get_data_hash(days)

            # 检查是否有缓存的洞察且数据未变化
            cached_data = self.db.get_insights_cache(cache_key)

            if cached_data and cached_data.get('data_hash') == current_hash:
                logger.info(f"数据库未更新，使用永久缓存的洞察数据: {cache_key}")
                return cached_data['insights']

            logger.info(f"检测到数据库更新，重新生成洞察: {cache_key} (hash: {current_hash[:8]}...)")

            # 添加到生成中集合
            self._generating_insights.add(cache_key)

            # 数据变化了，需要重新生成洞察
            papers = self.db.get_recent_papers(days)
            if not papers:
                return "没有找到最近的论文数据。"

            # 准备论文信息用于分析
            papers_info = []
            # 根据时间范围和论文数量动态调整分析数量
            total_papers = len(papers)

            # 动态确定要分析的论文数量
            if total_papers == 0:
                return "没有找到最近的论文数据。"
            elif total_papers <= 10:
                # 论文很少时，分析所有论文
                papers_to_analyze = papers
            elif total_papers <= 30:
                # 论文适中时，分析大部分论文
                papers_to_analyze = papers[:min(25, total_papers)]
            else:
                # 论文很多时，分析固定数量以保证效率和质量
                papers_to_analyze = papers[:30]  # 增加到30篇以获得更好的洞察
            for i, paper in enumerate(papers_to_analyze):
                papers_info.append({
                    'index': i + 1,
                    'title': paper.title,
                    'summary': paper.summary or paper.abstract[:400],  # 稍微缩短摘要
                    'categories': paper.categories,
                    'authors': paper.authors[:3] if paper.authors else []  # 只取前3个作者
                })

            prompt = f"""
你是一个专业的学术分析师。请基于最近{days}天的研究论文进行分析：

**数据概况：**
- 时间范围：最近{days}天
- 总论文数：{total_papers}篇
- 深度分析：{len(papers_to_analyze)}篇（{len(papers_to_analyze)/total_papers*100:.1f}%）

分析论文：
{papers_info}

请提供深入的研究洞察分析，使用优美的Markdown格式，包括：

## 🔬 研究趋势分析
识别当前最主要的研究热点和趋势方向

## ⚡ 技术突破点
找出重要的技术创新和方法突破

## 🔗 跨学科融合
识别不同研究领域之间的交叉融合趋势

## 🔮 未来展望
基于当前研究趋势预测未来发展方向

## 👥 关键研究团队
识别活跃的研究机构和作者群体

格式要求：
- 用中文回答，使用优雅的Markdown格式
- 每个主要部分使用合适的emoji图标
- 重要概念和关键词使用**加粗**强调
- 技术术语和方法使用`代码格式`标注
- 适当使用引用块>突出重点观点
- 确保内容结构清晰，层次分明
- 字数控制在800-1200字之间
- 基于实际论文内容进行分析，不要泛泛而谈
"""

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的研究趋势分析师，擅长从学术论文中提取有价值的洞察。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,  # 增加token限制以支持更长的分析
                temperature=0.3,   # 降低随机性，提高稳定性
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
                # 保存到数据库缓存（不包含热门主题）
                try:
                    self.db.save_insights_cache(cache_key, current_hash, insights, [])
                except Exception as cache_e:
                    logger.error(f"保存缓存失败: {cache_e}")

            return insights

        except Exception as e:
            logger.error(f"生成研究洞察失败: {e}")
            return f"生成洞察失败: {str(e)}"
        finally:
            # 确保从生成中集合中移除，即使出现异常
            if cache_key in self._generating_insights:
                self._generating_insights.remove(cache_key)

    def auto_update_insights_if_needed(self, days: int = 7) -> bool:
        """
        检查数据库是否更新，如果更新了则自动生成新的洞察（后台任务用）

        Args:
            days: 分析的天数

        Returns:
            是否更新了洞察
        """
        cache_key = f"insights_{days}"

        try:
            # 获取当前数据的哈希值
            current_hash = self.db.get_data_hash(days)

            # 检查缓存的数据哈希
            cached_data = self.db.get_insights_cache(cache_key)

            if not cached_data or cached_data.get('data_hash') != current_hash:
                logger.info(f"检测到数据库更新，后台自动生成洞察: {cache_key}")

                # 异步生成洞察
                insights = self.get_research_insights(days)

                if insights and not insights.startswith("生成洞察失败"):
                    logger.info(f"后台洞察生成成功: {cache_key}")
                    return True
                else:
                    logger.error(f"后台洞察生成失败: {cache_key}")
                    return False
            else:
                logger.debug(f"数据库未更新，跳过洞察生成: {cache_key}")
                return False

        except Exception as e:
            logger.error(f"自动更新洞察检查失败: {e}")
            return False

    def get_trending_topics(self, days: int = 7) -> List[str]:
        """
        获取热门研究主题
        基于最近论文的标题和摘要分析出高频关键词

        Args:
            days: 分析的天数

        Returns:
            热门主题列表
        """
        try:
            papers = self.db.get_recent_papers(days)
            if not papers:
                return []

            # 收集所有标题和摘要中的关键词
            all_text = []
            for paper in papers:
                # 使用标题和摘要（如果有生成摘要则用摘要，否则用原摘要）
                text = paper.title.lower()
                summary_text = paper.summary if paper.summary else paper.abstract
                text += " " + summary_text.lower()
                all_text.append(text)

            # 常见的技术词汇过滤
            common_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
                'by', 'from', 'we', 'our', 'this', 'that', 'these', 'those', 'is', 'are', 'was',
                'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                'can', 'could', 'may', 'might', 'should', 'shall', 'must', 'paper', 'study',
                'research', 'analysis', 'approach', 'method', 'model', 'system', 'algorithm',
                'propose', 'present', 'show', 'demonstrate', 'evaluate', 'performance', 'result'
            }

            # 简单的关键词提取
            import re
            word_count = {}

            for text in all_text:
                # 提取单词（保留技术术语）
                words = re.findall(r'\b[a-zA-Z-]{3,}\b', text)
                for word in words:
                    if word not in common_words and len(word) > 3:
                        word_count[word] = word_count.get(word, 0) + 1

            # 获取出现频率最高的关键词
            sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)

            # 返回前10个热门关键词
            trending_topics = [word for word, count in sorted_words[:10] if count >= 2]

            logger.info(f"提取到{len(trending_topics)}个热门主题")
            return trending_topics

        except Exception as e:
            logger.error(f"获取热门主题失败: {e}")
            return []

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
            found_ids = []
            missing_ids = []

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
                        found_ids.append(paper_id)
                    else:
                        missing_ids.append(paper_id)

            # 如果有缺失的论文，提供详细错误信息
            if missing_ids:
                error_msg = f"以下论文在数据库中未找到：{', '.join(missing_ids)}\n\n"
                if found_ids:
                    error_msg += f"找到的论文：{', '.join(found_ids)}"
                else:
                    error_msg += "请检查论文ID是否正确，或先爬取这些论文。\n\n提示：\n"
                    error_msg += "1. 访问论文列表页面查看可用的论文ID\n"
                    error_msg += "2. 使用爬虫功能获取新论文\n"
                    error_msg += "3. 确保论文ID格式正确（如：2510.25767）"
                return error_msg

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