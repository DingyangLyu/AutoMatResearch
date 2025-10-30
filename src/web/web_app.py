#!/usr/bin/env python3
"""
简单的Web界面来管理arXiv爬虫
"""

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
from datetime import datetime, timedelta
from pathlib import Path
from src.utils.logger import setup_logger, get_logger
from src.core.scheduler import PaperScheduler
from src.core.scraper import ArxivScraper
from src.core.analyzer import DeepSeekAnalyzer
from src.utils.utils import ConfigManager, PaperExporter, format_paper_summary
from config.settings import settings

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
template_folder = PROJECT_ROOT / "web" / "templates"
static_folder = PROJECT_ROOT / "web" / "static"

app = Flask(__name__, template_folder=str(template_folder), static_folder=str(static_folder))
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'arxiv-scraper-secret-key-change-in-production')

# 添加自定义过滤器
@app.template_filter('nl2br')
def nl2br_filter(text):
    """将换行符转换为HTML的<br>标签"""
    if text is None:
        return ''
    import re
    return re.sub(r'\r?\n', '<br>', text)

# 初始化组件
scheduler = PaperScheduler()
scraper = ArxivScraper()
analyzer = DeepSeekAnalyzer()
config_manager = ConfigManager()
exporter = PaperExporter(scraper.db)

# 设置日志
setup_logger()
logger = get_logger(__name__)

# 洞察缓存
_insights_cache = {}

def _get_cached_insights(cache_key):
    """获取缓存的洞察数据"""
    if cache_key in _insights_cache:
        cached_data = _insights_cache[cache_key]
        import time
        if time.time() - cached_data['timestamp'] < 3600:
            return cached_data
        else:
            # 删除过期缓存
            del _insights_cache[cache_key]
    return None

def _cache_insights(cache_key, insights, trending):
    """缓存洞察数据"""
    import time
    _insights_cache[cache_key] = {
        'insights': insights,
        'trending': trending,
        'timestamp': time.time()
    }
    logger.info(f"已缓存洞察数据: {cache_key}")

@app.route('/refresh_insights')
def refresh_insights():

    days = int(request.args.get('days', 7))
    cache_key = f'insights_{days}'

    # 删除缓存
    if cache_key in _insights_cache:
        del _insights_cache[cache_key]
        flash(f'已清除 {days} 天的洞察缓存', 'success')
    else:
        flash('没有找到缓存数据', 'info')

    # 启动后台生成新的洞察
    try:
        import threading

        def background_regenerate():
            """后台重新生成洞察"""
            try:
                logger.info(f"后台重新生成洞察开始: {cache_key}")
                insights_data = analyzer.get_research_insights(days)
                trending_data = scraper.get_trending_topics(days)
                _cache_insights(cache_key, insights_data, trending_data)
                logger.info(f"后台洞察重新生成完成: {cache_key}")
            except Exception as e:
                logger.error(f"后台洞察重新生成失败: {e}")
                _cache_insights(cache_key, f"重新生成失败: {str(e)}", [])

        thread = threading.Thread(target=background_regenerate, daemon=True)
        thread.start()
        logger.info(f"已启动后台洞察重新生成: {cache_key}")
        flash('正在后台重新生成洞察，请稍后刷新页面', 'info')

    except Exception as e:
        logger.error(f"启动后台洞察重新生成失败: {e}")

    return redirect(url_for('insights', days=days))

@app.route('/')
def index():
    """主页"""
    # 获取系统状态
    status = scheduler.get_status()
    recent_papers = scraper.db.get_recent_papers(7)

    return render_template('index.html',
                         status=status,
                         recent_papers=recent_papers[:5],
                         keywords=config_manager.get_keywords())

@app.route('/keywords', methods=['GET', 'POST'])
def keywords():
    """关键词管理"""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            keyword = request.form.get('keyword', '').strip()
            if keyword:
                keywords = config_manager.get_keywords()
                if keyword not in keywords:
                    keywords.append(keyword)
                    config_manager.update_keywords(keywords)
                    flash(f'已添加关键词: {keyword}', 'success')
                else:
                    flash(f'关键词已存在: {keyword}', 'warning')

        elif action == 'remove':
            keyword = request.form.get('keyword', '').strip()
            keywords = config_manager.get_keywords()
            if keyword in keywords:
                keywords.remove(keyword)
                config_manager.update_keywords(keywords)
                flash(f'已删除关键词: {keyword}', 'success')

        elif action == 'set':
            keywords_text = request.form.get('keywords', '').strip()
            if keywords_text:
                keywords = [k.strip() for k in keywords_text.split(',')]
                config_manager.update_keywords(keywords)
                flash(f'关键词已更新', 'success')

        return redirect(url_for('keywords'))

    keywords = config_manager.get_keywords()
    return render_template('keywords.html', keywords=keywords)

@app.route('/settings', methods=['GET', 'POST'])
def system_settings():
    """系统配置管理"""
    if request.method == 'POST':
        action = request.form.get('action')

        try:
            if action == 'api_config':
                # 更新API配置
                deepseek_api_key = request.form.get('deepseek_api_key', '').strip()
                deepseek_base_url = request.form.get('deepseek_base_url', '').strip()

                # 更新环境变量
                if deepseek_api_key:
                    os.environ['DEEPSEEK_API_KEY'] = deepseek_api_key
                    config_manager.update_config('DEEPSEEK_API_KEY', deepseek_api_key)

                if deepseek_base_url:
                    os.environ['DEEPSEEK_BASE_URL'] = deepseek_base_url
                    config_manager.update_config('DEEPSEEK_BASE_URL', deepseek_base_url)

                # 重新初始化分析器以使用新的API配置
                global analyzer
                analyzer = DeepSeekAnalyzer()

                flash('API配置已更新', 'success')

            elif action == 'scraping_config':
                # 更新爬取配置
                max_papers = request.form.get('max_papers_per_day', '').strip()
                schedule_time = request.form.get('schedule_time', '').strip()

                if max_papers:
                    os.environ['MAX_PAPERS_PER_DAY'] = max_papers
                    config_manager.update_config('MAX_PAPERS_PER_DAY', max_papers)

                if schedule_time:
                    os.environ['SCHEDULE_TIME'] = schedule_time
                    config_manager.update_config('SCHEDULE_TIME', schedule_time)

                flash('爬取配置已更新', 'success')

        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            flash(f'更新配置失败: {str(e)}', 'error')

        return redirect(url_for('system_settings'))

    # 获取当前配置
    config = {
        'deepseek_api_key': os.getenv('DEEPSEEK_API_KEY', ''),
        'deepseek_base_url': os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'),
        'max_papers_per_day': os.getenv('MAX_PAPERS_PER_DAY', '10'),
        'schedule_time': os.getenv('SCHEDULE_TIME', '09:00'),
        'database_path': settings.database_path
    }

    # 获取系统状态
    status = scheduler.get_status()
    status['keywords_count'] = len(config_manager.get_keywords())

    return render_template('settings.html', config=config, status=status)

@app.route('/papers')
def papers():
    """论文列表"""
    page = int(request.args.get('page', 1))
    per_page = 20
    search = request.args.get('search', '').strip()
    days = int(request.args.get('days', 30))

    if search:
        papers = scraper.db.search_papers(search)
    else:
        papers = scraper.db.get_recent_papers(days)

    # 分页
    total = len(papers)
    start = (page - 1) * per_page
    end = start + per_page
    papers_page = papers[start:end]

    return render_template('papers.html',
                         papers=papers_page,
                         page=page,
                         per_page=per_page,
                         total=total,
                         search=search,
                         days=days)

@app.route('/paper/<arxiv_id>')
def paper_detail(arxiv_id):
    """论文详情"""
    paper = scraper.db.get_paper_by_arxiv_id(arxiv_id)
    if paper:
        return render_template('paper_detail.html', paper=paper)
    else:
        flash(f'论文未找到: {arxiv_id}', 'error')
        return redirect(url_for('papers'))

@app.route('/scrape', methods=['POST'])
def scrape():
    """手动爬取"""
    try:
        logger.info("Web界面触发手动爬取")
        saved_count = scheduler.run_once()
        flash(f'爬取完成，保存了 {saved_count} 篇新论文', 'success')
    except Exception as e:
        logger.error(f"Web界面爬取失败: {e}")
        flash(f'爬取失败: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/scrape_more', methods=['POST'])
def scrape_more():
    """增量爬取更多论文"""
    try:
        logger.info("Web界面触发增量爬取")
        additional_count = int(request.form.get('additional_count', 10))
        keywords = config_manager.get_keywords()

        saved_count = scraper.scrape_more_papers(keywords, additional_count)
        flash(f'增量爬取完成，额外保存了 {saved_count} 篇新论文', 'success')

        # 如果保存了新论文，自动生成摘要
        if saved_count > 0:
            logger.info(f"开始为 {saved_count} 篇新论文生成AI摘要...")

            # 获取今天的论文（刚爬取的）
            recent_papers = scraper.db.get_recent_papers(1)

            # 只分析没有摘要的论文
            papers_needing_summary = [p for p in recent_papers if not p.summary]

            if papers_needing_summary:
                try:
                    analyzed_count = 0
                    for paper in papers_needing_summary:
                        logger.info(f"正在生成论文摘要: {paper.title[:50]}...")
                        summary = analyzer.generate_summary(paper)
                        if summary:
                            analyzer._update_paper_summary(paper.arxiv_id, summary)
                            analyzed_count += 1
                        # 添加延迟避免API限制
                        import time
                        time.sleep(1)

                    logger.info(f"成功为 {analyzed_count} 篇论文生成AI摘要")
                    flash(f'已为 {analyzed_count} 篇新论文生成AI摘要', 'info')

                except Exception as e:
                    logger.error(f"生成AI摘要失败: {e}")
                    flash(f'AI摘要生成失败: {str(e)}', 'warning')

            # 自动更新洞察（异步后台执行）
            try:
                import threading
                import time

                def auto_update_insights():
                    """后台自动更新洞察"""
                    logger.info("开始后台自动更新研究洞察...")
                    try:
                        # 等待一小段时间确保数据库操作完成
                        time.sleep(2)

                        # 生成新洞察
                        insights_data = analyzer.get_research_insights(7)
                        trending_data = analyzer.get_trending_topics(7)

                        # 缓存新洞察
                        cache_key = 'insights_7'
                        _cache_insights(cache_key, insights_data, trending_data)

                        logger.info("后台洞察更新完成")
                    except Exception as e:
                        logger.error(f"后台洞察更新失败: {e}")

                # 启动后台线程
                insights_thread = threading.Thread(target=auto_update_insights, daemon=True)
                insights_thread.start()
                logger.info("已启动后台洞察更新任务")

            except Exception as e:
                logger.error(f"启动后台洞察更新失败: {e}")

            # 清除旧的洞察缓存
            global _insights_cache
            _insights_cache.clear()
            logger.info("已清除洞察缓存")

    except Exception as e:
        logger.error(f"增量爬取失败: {e}")
        flash(f'增量爬取失败: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/scrape', methods=['GET'])
def scrape_get():
    """处理GET请求的scrape（重定向到首页）"""
    flash('请使用表单提交来执行爬取操作', 'warning')
    return redirect(url_for('index'))

@app.route('/api/insights_status')
def api_insights_status():
    """获取洞察状态API"""
    days = int(request.args.get('days', 7))
    cache_key = f'insights_{days}'

    cached_insights = _get_cached_insights(cache_key)

    status = {
        'cache_key': cache_key,
        'has_cache': cached_insights is not None,
        'last_updated': cached_insights.get('timestamp') if cached_insights else None,
        'is_generating': cache_key in _insights_cache and cached_insights is None
    }

    return jsonify(status)

@app.route('/insights')
def insights():
    """研究洞察"""
    days = int(request.args.get('days', 7))

    # 检查是否有缓存的洞察
    cache_key = f'insights_{days}'
    cached_insights = _get_cached_insights(cache_key)

    if cached_insights:
        logger.info(f"使用缓存的洞察数据: {cache_key}")
        insights = cached_insights['insights']
        trending = cached_insights['trending']
    else:
        # 异步生成洞察，避免页面卡住
        try:
            logger.info(f"生成新的洞察数据: {cache_key}")

            # 使用线程来处理可能耗时的操作
            import threading
            import queue

            result_queue = queue.Queue()

            def generate_insights():
                try:
                    insights_data = analyzer.get_research_insights(days)
                    trending_data = scraper.get_trending_topics(days)
                    result_queue.put(('success', insights_data, trending_data))
                except Exception as e:
                    result_queue.put(('error', str(e), []))

            # 启动线程
            thread = threading.Thread(target=generate_insights)
            thread.daemon = True
            thread.start()

            # 等待结果，最多等待30秒
            thread.join(timeout=30)

            if thread.is_alive():
                logger.warning("洞察生成超时，使用默认内容")
                insights = "洞察生成超时，请稍后重试。"
                trending = []
            else:
                try:
                    status, insights_data, trending_data = result_queue.get_nowait()
                    if status == 'success':
                        insights = insights_data
                        trending = trending_data
                        # 缓存结果
                        _cache_insights(cache_key, insights, trending)
                    else:
                        insights = f"生成洞察失败: {insights_data}"
                        trending = []
                except queue.Empty:
                    logger.warning("洞察生成队列为空，使用默认内容")
                    insights = "洞察生成异常，请稍后重试。"
                    trending = []

        except Exception as e:
            logger.error(f"生成洞察失败: {e}")
            insights = f"生成洞察失败: {str(e)}"
            trending = []

    return render_template('insights.html',
                         insights=insights,
                         trending=trending,
                         days=days)

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    """论文比较"""
    if request.method == 'POST':
        paper_ids = request.form.get('paper_ids', '').strip().split()
        paper_ids = [pid.strip() for pid in paper_ids if pid.strip()]

        if len(paper_ids) < 2:
            flash('请提供至少两个论文ID', 'error')
        else:
            try:
                comparison = analyzer.compare_papers(paper_ids)
                return render_template('compare_result.html',
                                     comparison=comparison,
                                     paper_ids=paper_ids)
            except Exception as e:
                flash(f'比较失败: {str(e)}', 'error')

    return render_template('compare.html')

@app.route('/export')
def export():
    """导出数据"""
    export_format = request.args.get('format', 'json')
    days = int(request.args.get('days', 30))

    # 如果days为-1，获取所有数据
    if days == -1:
        # 获取所有论文（需要修改数据库方法来支持获取所有数据）
        papers = scraper.db.get_all_papers() if hasattr(scraper.db, 'get_all_papers') else scraper.db.get_recent_papers(3650)  # 10年作为"全部"
    else:
        papers = scraper.db.get_recent_papers(days)

    if not papers:
        flash('没有数据可导出', 'warning')
        return redirect(url_for('papers'))

    try:
        if export_format == 'json':
            filepath = exporter.export_to_json(papers)
        elif export_format == 'markdown':
            filepath = exporter.export_to_markdown(papers)
        elif export_format == 'bibtex':
            filepath = exporter.export_to_bibtex(papers)
        else:
            flash('不支持的导出格式', 'error')
            return redirect(url_for('papers'))

        if filepath:
            flash(f'数据已导出到: {filepath}', 'success')
        else:
            flash('导出失败', 'error')

    except Exception as e:
        flash(f'导出失败: {str(e)}', 'error')

    return redirect(url_for('papers'))

@app.route('/export_page')
def export_page():
    """导出页面"""
    return render_template('export.html')

@app.route('/api/status')
def api_status():
    """API: 获取系统状态"""
    return jsonify(scheduler.get_status())

@app.route('/api/papers')
def api_papers():
    """API: 获取论文列表"""
    search = request.args.get('search', '').strip()
    days = int(request.args.get('days', 30))

    if search:
        papers = scraper.db.search_papers(search)
    else:
        papers = scraper.db.get_recent_papers(days)

    # 转换为字典格式
    papers_data = []
    for paper in papers:
        papers_data.append({
            'title': paper.title,
            'authors': paper.authors,
            'abstract': paper.abstract[:200] + '...',
            'arxiv_id': paper.arxiv_id,
            'published_date': paper.published_date.isoformat() if paper.published_date else None,
            'categories': paper.categories,
            'summary': paper.summary[:200] + '...' if paper.summary else None
        })

    return jsonify(papers_data)

@app.route('/api/insights')
def api_insights():
    """API: 获取研究洞察"""
    days = int(request.args.get('days', 7))
    try:
        insights = analyzer.get_research_insights(days)
        trending = scraper.get_trending_topics(days)
        return jsonify({
            'insights': insights,
            'trending': trending
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/paper/<arxiv_id>/bibtex')
def api_paper_bibtex(arxiv_id):
    """API: 获取单个论文的BibTeX格式"""
    try:
        paper = scraper.db.get_paper_by_arxiv_id(arxiv_id)
        if not paper:
            return jsonify({'error': '论文未找到'}), 404

        # 生成BibTeX key
        first_author_lastname = paper.authors[0].split()[-1] if paper.authors else "Unknown"
        year = paper.published_date.year if paper.published_date else datetime.now().year
        title_words = paper.title.split()[:3]
        title_key = ''.join([word.strip('.,!?;:') for word in title_words])
        bibtex_key = f"{first_author_lastname}{year}{title_key}"

        # 清理并格式化数据
        title = paper.title.replace('{', '\\{').replace('}', '\\}').replace('&', '\\&')
        authors = ' and '.join(paper.authors)
        abstract = paper.abstract.replace('{', '\\{').replace('}', '\\}').replace('\n', ' ')

        # 生成BibTeX条目
        bibtex_entry = f"""@misc{{{bibtex_key},
  title = {{{title}}},
  author = {{{authors}}},
  year = {{{year}}},
  eprint = {{{paper.arxiv_id}}},
  archivePrefix = {{arXiv}},
  primaryClass = {{{paper.categories[0] if paper.categories else 'cs.AI'}}},"""

        if abstract:
            bibtex_entry += f"""
  abstract = {{{abstract}}},"""

        bibtex_entry += f"""
  url = {{{paper.pdf_url}}},
  howpublished = {{arXiv:{paper.arxiv_id}}}
}}"""

        return bibtex_entry

    except Exception as e:
        logger.error(f"生成BibTeX失败: {e}")
        return jsonify({'error': f'生成BibTeX失败: {str(e)}'}), 500

if __name__ == '__main__':
    # 创建模板目录
    import os
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("🌐 启动Web界面...")
    print("📱 访问地址: http://localhost:5000")
    print("💡 使用 Ctrl+C 停止服务")

    app.run(host='0.0.0.0', port=5000, debug=True)