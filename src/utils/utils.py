import json
import os
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置文件管理器"""

    def __init__(self, config_file: str = None):
        if config_file is None:
            from pathlib import Path
            # 项目根目录
            PROJECT_ROOT = Path(__file__).parent.parent.parent
            config_file = PROJECT_ROOT / "config" / "user_config.json"
        self.config_file = str(config_file)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                return self._get_default_config()
        else:
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "keywords": ["materials science", "machine learning"],
            "max_papers_per_day": 10,
            "schedule_time": "09:00",
            "auto_summarize": True,
            "notification_enabled": False,
            "notification_email": "",
            "categories": ["cs.AI", "cs.LG", "cs.CV", "cs.CL"]
        }

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到 {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    def update_keywords(self, keywords: List[str]):
        """更新关键词"""
        self.config["keywords"] = keywords
        self.save_config()
        logger.info(f"关键词已更新为: {keywords}")

    def get_keywords(self) -> List[str]:
        """获取关键词"""
        return self.config.get("keywords", [])

    def update_setting(self, key: str, value: Any):
        """更新单个设置"""
        self.config[key] = value
        self.save_config()
        logger.info(f"设置 {key} 已更新为: {value}")

    def update_config(self, key: str, value: Any):
        """更新配置（update_setting的别名）"""
        self.update_setting(key, value)

class PaperExporter:
    """论文导出工具"""

    def __init__(self, db_manager):
        self.db = db_manager

    def export_to_json(self, papers: List, filename: str = None) -> str:
        """导出论文到JSON文件"""
        if filename is None:
            filename = f"papers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # 使用data目录下的exports文件夹
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        exports_dir = project_root / "data" / "exports"

        os.makedirs(exports_dir, exist_ok=True)
        filepath = exports_dir / filename

        papers_data = []
        for paper in papers:
            papers_data.append({
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "arxiv_id": paper.arxiv_id,
                "published_date": paper.published_date.isoformat() if paper.published_date else None,
                "categories": paper.categories,
                "pdf_url": paper.pdf_url,
                "summary": paper.summary,
                "created_at": paper.created_at.isoformat() if paper.created_at else None
            })

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(papers_data, f, indent=2, ensure_ascii=False)
            logger.info(f"论文已导出到: {str(filepath)}")
            return str(filepath)
        except Exception as e:
            logger.error(f"导出JSON文件失败: {e}")
            return None

    def export_to_markdown(self, papers: List, filename: str = None) -> str:
        """导出论文到Markdown文件"""
        if filename is None:
            filename = f"papers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        # 使用data目录下的exports文件夹
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        exports_dir = project_root / "data" / "exports"

        os.makedirs(exports_dir, exist_ok=True)
        filepath = exports_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# arXiv论文导出\n\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"论文数量: {len(papers)}\n\n")
                f.write("---\n\n")

                for i, paper in enumerate(papers, 1):
                    f.write(f"## {i}. {paper.title}\n\n")
                    f.write(f"**作者**: {', '.join(paper.authors)}\n\n")
                    f.write(f"**arXiv ID**: [{paper.arxiv_id}](https://arxiv.org/abs/{paper.arxiv_id})\n\n")
                    f.write(f"**PDF**: [下载链接]({paper.pdf_url})\n\n")
                    f.write(f"**发布日期**: {paper.published_date}\n\n")
                    f.write(f"**分类**: {', '.join(paper.categories)}\n\n")

                    if paper.summary:
                        f.write(f"**AI摘要**:\n{paper.summary}\n\n")

                    f.write(f"**原始摘要**:\n{paper.abstract}\n\n")
                    f.write("---\n\n")

            logger.info(f"论文已导出到: {str(filepath)}")
            return str(filepath)
        except Exception as e:
            logger.error(f"导出Markdown文件失败: {e}")
            return None

    def export_to_bibtex(self, papers: List, filename: str = None) -> str:
        """导出论文到BibTeX文件"""
        if filename is None:
            filename = f"papers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bib"

        # 使用data目录下的exports文件夹
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        exports_dir = project_root / "data" / "exports"

        os.makedirs(exports_dir, exist_ok=True)
        filepath = exports_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("% arXiv论文导出 - BibTeX格式\n")
                f.write(f"% 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"% 论文数量: {len(papers)}\n\n")

                for paper in papers:
                    # 生成BibTeX key (第一作者的姓氏 + 年份 + 标题关键词)
                    first_author_lastname = paper.authors[0].split()[-1] if paper.authors else "Unknown"
                    year = paper.published_date.year if paper.published_date else datetime.now().year
                    title_words = paper.title.split()[:3]  # 取标题前3个词
                    title_key = ''.join([word.strip('.,!?;:') for word in title_words])
                    bibtex_key = f"{first_author_lastname}{year}{title_key}"

                    # 清理并格式化数据
                    title = paper.title.replace('{', '\\{').replace('}', '\\}').replace('&', '\\&')
                    authors = ' and '.join(paper.authors)
                    abstract = paper.abstract.replace('{', '\\{').replace('}', '\\}').replace('\n', ' ')

                    # 写入BibTeX条目
                    f.write(f"@misc{{{bibtex_key},\n")
                    f.write(f"  title = {{{title}}},\n")
                    f.write(f"  author = {{{authors}}},\n")
                    f.write(f"  year = {{{year}}},\n")
                    f.write(f"  eprint = {{{paper.arxiv_id}}},\n")
                    f.write(f"  archivePrefix = {{arXiv}},\n")
                    f.write(f"  primaryClass = {{{paper.categories[0] if paper.categories else 'cs.AI'}}},\n")

                    # 添加摘要（如果有）
                    if abstract:
                        f.write(f"  abstract = {{{abstract}}},\n")

                    # 添加PDF URL
                    f.write(f"  url = {{{paper.pdf_url}}},\n")
                    f.write(f"  howpublished = {{arXiv:{paper.arxiv_id}}}\n")
                    f.write("}\n\n")

            logger.info(f"论文已导出到: {str(filepath)}")
            return str(filepath)
        except Exception as e:
            logger.error(f"导出BibTeX文件失败: {e}")
            return None

class NotificationManager:
    """通知管理器"""

    def __init__(self):
        self.enabled = False
        self.email_config = {}

    def setup_email_notification(self, smtp_server: str, smtp_port: int,
                                username: str, password: str, recipient: str):
        """设置邮件通知"""
        self.enabled = True
        self.email_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "recipient": recipient
        }
        logger.info("邮件通知已设置")

    def send_new_papers_notification(self, papers: List):
        """发送新论文通知"""
        if not self.enabled or not papers:
            return

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg['From'] = self.email_config["username"]
            msg['To'] = self.email_config["recipient"]
            msg['Subject'] = f"发现了 {len(papers)} 篇新的arXiv论文"

            body = f"最新发现了 {len(papers)} 篇相关论文：\n\n"
            for i, paper in enumerate(papers, 1):
                body += f"{i}. {paper.title}\n"
                body += f"   作者: {', '.join(paper.authors[:3])}...\n"
                body += f"   链接: https://arxiv.org/abs/{paper.arxiv_id}\n\n"

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])
            server.send_message(msg)
            server.quit()

            logger.info(f"已发送新论文通知邮件给 {self.email_config['recipient']}")

        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")

def validate_keywords(keywords: List[str]) -> bool:
    """验证关键词格式"""
    if not keywords:
        return False

    for keyword in keywords:
        if not isinstance(keyword, str) or len(keyword.strip()) == 0:
            return False
        if len(keyword) > 100:  # 关键词长度限制
            return False

    return True

def format_paper_summary(paper) -> str:
    """格式化论文摘要显示"""
    summary = f"📄 {paper.title}\n"
    summary += f"👥 {', '.join(paper.authors[:3])}"
    if len(paper.authors) > 3:
        summary += f" 等{len(paper.authors)}人"
    summary += f"\n🔗 https://arxiv.org/abs/{paper.arxiv_id}"
    summary += f"\n📅 {paper.published_date.strftime('%Y-%m-%d') if paper.published_date else 'Unknown'}"
    summary += f"\n🏷️ {', '.join(paper.categories[:3])}"
    if paper.summary:
        summary += f"\n💡 {paper.summary[:200]}..."
    return summary