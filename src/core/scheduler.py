import schedule
import time
import logging
from datetime import datetime
from typing import List
from src.core.scraper import ArxivScraper
from src.core.analyzer import DeepSeekAnalyzer
from config.settings import settings

logger = logging.getLogger(__name__)

class PaperScheduler:
    def __init__(self):
        self.scraper = ArxivScraper()
        self.analyzer = DeepSeekAnalyzer()
        self.is_running = False

    def daily_scrape_task(self):
        """每日爬取任务"""
        try:
            logger.info("开始执行每日论文爬取任务")
            start_time = datetime.now()

            # 爬取新论文（启用增量爬取）
            keywords = settings.SEARCH_KEYWORDS
            saved_count = self.scraper.scrape_and_save(keywords, incremental=True)

            if saved_count > 0:
                logger.info(f"成功爬取并保存了 {saved_count} 篇新论文")

                # 获取今天的论文并生成摘要
                recent_papers = self.scraper.db.get_recent_papers(1)
                if recent_papers:
                    logger.info("开始生成论文摘要...")
                    analyzed_papers = self.analyzer.analyze_papers_batch(recent_papers)

                # 数据库更新后，自动更新洞察缓存（不同时间范围的）
                logger.info("数据库已更新，开始自动更新洞察缓存...")

                # 更新不同时间范围的洞察
                for days in [1, 7, 30]:
                    try:
                        updated = self.analyzer.auto_update_insights_if_needed(days)
                        if updated:
                            logger.info(f"成功更新 {days} 天洞察缓存")
                        else:
                            logger.info(f"{days} 天洞察缓存已是最新，无需更新")
                    except Exception as e:
                        logger.error(f"更新 {days} 天洞察缓存失败: {e}")

                # 生成今日洞察用于文件保存
                insights = self.analyzer.get_research_insights(1)
                if insights and not insights.startswith("生成洞察失败"):
                    logger.info(f"今日研究洞察：\n{insights}")
                    # 保存洞察到文件
                    self._save_daily_insights(insights, start_time)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"每日任务完成，耗时: {duration:.2f} 秒")

            return saved_count

        except Exception as e:
            logger.error(f"每日爬取任务执行失败: {e}")
            return 0

    def _save_daily_insights(self, insights: str, date: datetime):
        """保存每日研究洞察到文件"""
        try:
            filename = f"daily_insights_{date.strftime('%Y%m%d')}.txt"
            filepath = f"insights/{filename}"

            import os
            os.makedirs("insights", exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"日期: {date.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"关键词: {', '.join(settings.SEARCH_KEYWORDS)}\n")
                f.write("=" * 50 + "\n\n")
                f.write(insights)

            logger.info(f"研究洞察已保存到: {filepath}")

        except Exception as e:
            logger.error(f"保存研究洞察失败: {e}")

    def weekly_analysis_task(self):
        """每周分析任务"""
        try:
            logger.info("开始执行每周分析任务")

            # 生成周度研究趋势报告
            insights = self.analyzer.get_research_insights(7)
            if insights:
                logger.info(f"本周研究趋势：\n{insights}")
                self._save_weekly_report(insights)

            # 获取热门主题
            trending_topics = self.scraper.get_trending_topics(7)
            if trending_topics:
                logger.info(f"本周热门主题: {', '.join(trending_topics)}")
                self._save_trending_topics(trending_topics)

        except Exception as e:
            logger.error(f"每周分析任务执行失败: {e}")

    def _save_weekly_report(self, insights: str):
        """保存周度报告"""
        try:
            from datetime import timedelta
            week_start = datetime.now() - timedelta(days=datetime.now().weekday())
            filename = f"weekly_report_{week_start.strftime('%Y%m%d')}.txt"
            filepath = f"reports/{filename}"

            import os
            os.makedirs("reports", exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"周度报告: {week_start.strftime('%Y-%m-%d')} 至 {datetime.now().strftime('%Y-%m-%d')}\n")
                f.write("=" * 50 + "\n\n")
                f.write(insights)

            logger.info(f"周度报告已保存到: {filepath}")

        except Exception as e:
            logger.error(f"保存周度报告失败: {e}")

    def _save_trending_topics(self, topics: List[str]):
        """保存热门主题"""
        try:
            from datetime import timedelta
            week_start = datetime.now() - timedelta(days=datetime.now().weekday())
            filename = f"trending_topics_{week_start.strftime('%Y%m%d')}.txt"
            filepath = f"trends/{filename}"

            import os
            os.makedirs("trends", exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"热门主题: {week_start.strftime('%Y-%m-%d')} 至 {datetime.now().strftime('%Y-%m-%d')}\n")
                f.write("=" * 30 + "\n\n")
                for i, topic in enumerate(topics, 1):
                    f.write(f"{i}. {topic}\n")

            logger.info(f"热门主题已保存到: {filepath}")

        except Exception as e:
            logger.error(f"保存热门主题失败: {e}")

    def setup_schedule(self):
        """设置定时任务"""
        try:
            # 每日爬取任务
            schedule.every().day.at(settings.SCHEDULE_TIME).do(self.daily_scrape_task)
            logger.info(f"已设置每日爬取任务，执行时间: {settings.SCHEDULE_TIME}")

            # 每周一早上生成周度报告
            schedule.every().monday.at("10:00").do(self.weekly_analysis_task)
            logger.info("已设置每周分析任务，执行时间: 每周一 10:00")

        except Exception as e:
            logger.error(f"设置定时任务失败: {e}")

    def start(self):
        """启动调度器"""
        try:
            self.is_running = True
            logger.info("论文爬取调度器启动")

            # 设置定时任务
            self.setup_schedule()

            # 立即执行一次任务（可选）
            # self.daily_scrape_task()

            # 主循环
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次

        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在停止调度器...")
            self.stop()
        except Exception as e:
            logger.error(f"调度器运行出错: {e}")
            self.stop()

    def stop(self):
        """停止调度器"""
        self.is_running = False
        logger.info("论文爬取调度器已停止")

    def run_once(self):
        """手动运行一次爬取任务"""
        logger.info("手动执行爬取任务")
        return self.daily_scrape_task()

    def update_keywords(self, new_keywords: List[str]):
        """更新搜索关键词"""
        try:
            # 这里可以添加配置更新的逻辑
            # 暂时直接更新配置
            settings.SEARCH_KEYWORDS = new_keywords
            logger.info(f"搜索关键词已更新为: {new_keywords}")

            # 可以选择立即运行一次任务
            # self.run_once()

        except Exception as e:
            logger.error(f"更新关键词失败: {e}")

    def get_status(self) -> dict:
        """获取调度器状态"""
        recent_papers = self.scraper.db.get_recent_papers(7)
        return {
            'is_running': self.is_running,
            'next_run': schedule.next_run(),
            'recent_papers_count': len(recent_papers),
            'keywords': settings.SEARCH_KEYWORDS,
            'schedule_time': settings.SCHEDULE_TIME,
            'max_papers_per_day': settings.MAX_PAPERS_PER_DAY
        }