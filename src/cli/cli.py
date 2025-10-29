#!/usr/bin/env python3
"""
命令行界面工具
提供交互式的关键词管理和系统控制
"""

import cmd
import sys
import os
from pathlib import Path
from typing import List

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logger import get_logger, setup_logger
from src.core.scheduler import PaperScheduler
from src.core.scraper import ArxivScraper
from src.core.analyzer import DeepSeekAnalyzer
from src.utils.utils import ConfigManager, PaperExporter, format_paper_summary
from src.utils.config import settings

logger = get_logger(__name__)

class ArxivCLI(cmd.Cmd):
    """arXiv爬虫命令行界面"""

    intro = """
    ╔══════════════════════════════════════════════════════════════╗
    ║           arXiv论文自动爬取Agent - 交互式控制台             ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  输入 'help' 查看可用命令                                      ║
    ║  输入 'quit' 退出程序                                          ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    prompt = "arXiv> "

    def __init__(self):
        super().__init__()
        self.scheduler = PaperScheduler()
        self.scraper = ArxivScraper()
        self.analyzer = DeepSeekAnalyzer()
        self.config_manager = ConfigManager()
        self.exporter = PaperExporter(self.scraper.db)

    def do_status(self, arg):
        """查看系统状态"""
        print("\n📊 系统状态:")
        print("-" * 40)
        status = self.scheduler.get_status()
        for key, value in status.items():
            if key == 'is_running':
                value = "运行中" if value else "已停止"
            elif key == 'next_run':
                value = str(value) if value else "未设置"
            print(f"  {key}: {value}")

        # 数据库统计
        recent_papers = self.scraper.db.get_recent_papers(30)
        print(f"\n📚 最近30天论文数量: {len(recent_papers)}")

    def do_keywords(self, arg):
        """管理搜索关键词"""
        if not arg:
            # 显示当前关键词
            keywords = self.config_manager.get_keywords()
            print(f"\n🔍 当前搜索关键词: {keywords}")
            return

        parts = arg.split()
        if parts[0] == "add":
            if len(parts) < 2:
                print("❌ 请提供要添加的关键词")
                return
            new_keyword = " ".join(parts[1:])
            keywords = self.config_manager.get_keywords()
            if new_keyword not in keywords:
                keywords.append(new_keyword)
                self.config_manager.update_keywords(keywords)
                print(f"✅ 已添加关键词: {new_keyword}")
            else:
                print(f"⚠️ 关键词已存在: {new_keyword}")

        elif parts[0] == "remove":
            if len(parts) < 2:
                print("❌ 请提供要删除的关键词")
                return
            keyword_to_remove = " ".join(parts[1:])
            keywords = self.config_manager.get_keywords()
            if keyword_to_remove in keywords:
                keywords.remove(keyword_to_remove)
                self.config_manager.update_keywords(keywords)
                print(f"✅ 已删除关键词: {keyword_to_remove}")
            else:
                print(f"⚠️ 关键词不存在: {keyword_to_remove}")

        elif parts[0] == "set":
            if len(parts) < 2:
                print("❌ 请提供新的关键词列表")
                return
            new_keywords = " ".join(parts[1:]).split(",")
            new_keywords = [k.strip() for k in new_keywords]
            self.config_manager.update_keywords(new_keywords)
            print(f"✅ 关键词已更新为: {new_keywords}")

        else:
            print("❌ 未知命令。可用命令: add, remove, set")

    def do_scrape(self, arg):
        """手动执行爬取任务"""
        print("🚀 开始执行爬取任务...")
        try:
            saved_count = self.scheduler.run_once()
            print(f"✅ 爬取完成，保存了 {saved_count} 篇新论文")
        except Exception as e:
            print(f"❌ 爬取失败: {e}")

    def do_search(self, arg):
        """搜索论文"""
        if not arg:
            print("❌ 请提供搜索关键词")
            return

        print(f"🔍 搜索关键词: {arg}")
        papers = self.scraper.db.search_papers(arg)

        if not papers:
            print("❌ 未找到相关论文")
            return

        print(f"📚 找到 {len(papers)} 篇相关论文:")
        print("=" * 60)

        for i, paper in enumerate(papers[:10], 1):  # 最多显示10篇
            print(f"\n{i}. {format_paper_summary(paper)}")

        if len(papers) > 10:
            print(f"\n... 还有 {len(papers) - 10} 篇论文未显示")

    def do_recent(self, arg):
        """查看最近的论文"""
        try:
            days = int(arg) if arg else 7
        except ValueError:
            print("❌ 请输入有效的天数")
            return

        papers = self.scraper.db.get_recent_papers(days)

        if not papers:
            print(f"❌ 最近{days}天没有论文")
            return

        print(f"📚 最近{days}天的论文 ({len(papers)}篇):")
        print("=" * 60)

        for i, paper in enumerate(papers[:10], 1):
            print(f"\n{i}. {format_paper_summary(paper)}")

        if len(papers) > 10:
            print(f"\n... 还有 {len(papers) - 10} 篇论文未显示")

    def do_insights(self, arg):
        """获取研究洞察"""
        try:
            days = int(arg) if arg else 7
        except ValueError:
            print("❌ 请输入有效的天数")
            return

        print(f"🧠 正在分析最近{days}天的研究趋势...")
        try:
            insights = self.analyzer.get_research_insights(days)
            print("\n📊 研究洞察:")
            print("=" * 60)
            print(insights)
        except Exception as e:
            print(f"❌ 生成洞察失败: {e}")

    def do_export(self, arg):
        """导出论文数据"""
        if not arg:
            print("❌ 请指定导出格式 (json/markdown)")
            return

        parts = arg.split()
        export_format = parts[0].lower()
        days = int(parts[1]) if len(parts) > 1 else 7

        papers = self.scraper.db.get_recent_papers(days)
        if not papers:
            print(f"❌ 最近{days}天没有论文可导出")
            return

        try:
            if export_format == "json":
                filepath = self.exporter.export_to_json(papers)
            elif export_format == "markdown" or export_format == "md":
                filepath = self.exporter.export_to_markdown(papers)
            else:
                print("❌ 不支持的格式，请使用 json 或 markdown")
                return

            if filepath:
                print(f"✅ 数据已导出到: {filepath}")
            else:
                print("❌ 导出失败")

        except Exception as e:
            print(f"❌ 导出失败: {e}")

    def do_trending(self, arg):
        """查看热门主题"""
        try:
            days = int(arg) if arg else 7
        except ValueError:
            print("❌ 请输入有效的天数")
            return

        print(f"🔥 正在分析最近{days}天的热门主题...")
        try:
            topics = self.scraper.get_trending_topics(days)
            if topics:
                print(f"\n📈 热门主题 (最近{days}天):")
                print("=" * 40)
                for i, topic in enumerate(topics, 1):
                    print(f"{i:2d}. {topic}")
            else:
                print("❌ 未找到热门主题数据")
        except Exception as e:
            print(f"❌ 获取热门主题失败: {e}")

    def do_compare(self, arg):
        """比较论文"""
        if not arg:
            print("❌ 请提供要比较的论文ID (用空格分隔)")
            return

        paper_ids = arg.split()
        if len(paper_ids) < 2:
            print("❌ 至少需要两篇论文进行比较")
            return

        print(f"🔍 正在比较论文: {', '.join(paper_ids)}")
        try:
            comparison = self.analyzer.compare_papers(paper_ids)
            print("\n📊 论文比较分析:")
            print("=" * 60)
            print(comparison)
        except Exception as e:
            print(f"❌ 比较分析失败: {e}")

    def do_start_scheduler(self, arg):
        """启动定时调度器"""
        print("⏰ 启动定时调度器...")
        print("💡 按 Ctrl+C 停止调度器")
        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            print("\n⏹️ 调度器已停止")

    def do_help(self, arg):
        """显示帮助信息"""
        if not arg:
            print("\n📖 可用命令:")
            print("=" * 50)
            commands = [
                ("status", "查看系统状态"),
                ("keywords", "管理搜索关键词 (add/remove/set)"),
                ("scrape", "手动执行爬取任务"),
                ("search [关键词]", "搜索论文"),
                ("recent [天数]", "查看最近论文 (默认7天)"),
                ("insights [天数]", "获取研究洞察 (默认7天)"),
                ("trending [天数]", "查看热门主题 (默认7天)"),
                ("compare [id1 id2 ...]", "比较多篇论文"),
                ("export [格式] [天数]", "导出数据 (json/markdown)"),
                ("start_scheduler", "启动定时调度器"),
                ("quit", "退出程序")
            ]

            for cmd, desc in commands:
                print(f"  {cmd:<20} - {desc}")

            print("\n💡 示例:")
            print("  keywords add transformer")
            print("  search attention mechanism")
            print("  recent 3")
            print("  export json 30")
            print("=" * 50)
        else:
            super().do_help(arg)

    def do_quit(self, arg):
        """退出程序"""
        print("👋 再见！")
        return True

def main():
    """主函数"""
    setup_logger()
    cli = ArxivCLI()
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
        sys.exit(0)

if __name__ == "__main__":
    main()