#!/usr/bin/env python3
"""
简单的Web界面来管理arXiv爬虫
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
import markdown
from datetime import datetime, timedelta
from pathlib import Path
import schedule

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logger import setup_logger, get_logger
from src.core.scheduler import PaperScheduler
from src.core.scraper import ArxivScraper
from src.core.analyzer import DeepSeekAnalyzer
from src.utils.utils import ConfigManager, PaperExporter, format_paper_summary
from src.data.keyword_manager import keyword_manager
from config.settings import settings

# 设置模板和静态文件路径
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
config_manager = ConfigManager()

# 全局变量跟踪后台任务状态
background_tasks = {
    'ai_analysis_running': False,
    'ai_analysis_progress': 0,
    'ai_analysis_total': 0,
    'ai_analysis_start_time': None
}

# 函数：获取当前关键词的组件
def get_current_components():
    """获取当前关键词的scraper、analyzer等组件"""
    current_keyword = keyword_manager.get_current_keyword()
    scraper = ArxivScraper(current_keyword)
    analyzer = DeepSeekAnalyzer(current_keyword)
    exporter = PaperExporter(scraper.db)
    return scraper, analyzer, exporter

# 默认组件（用于初始化）
scraper, analyzer, exporter = get_current_components()

# 设置日志
setup_logger()
logger = get_logger(__name__)

# 上下文处理器，确保所有模板都能访问关键词信息
@app.context_processor
def inject_keywords():
    """向所有模板注入关键词信息"""
    current_config = keyword_manager.get_current_config()
    all_keywords = keyword_manager.get_all_keywords()
    return dict(
        current_keyword=current_config,
        all_keywords=all_keywords
    )

# 洞察缓存现在使用数据库永久缓存，无需内存缓存

@app.route('/refresh_insights', methods=['GET', 'POST'])
def refresh_insights():
    """强制刷新洞察缓存"""
    if request.method == 'POST':
        days = int(request.form.get('days', 7))
    else:
        days = int(request.args.get('days', 7))

    try:
        # 清除数据库缓存
        import sqlite3
        with sqlite3.connect(scraper.db.db_path) as conn:
            conn.execute("DELETE FROM insights_cache WHERE cache_key = ?", (f'insights_{days}',))
            conn.commit()
        logger.info(f"已清除 {days} 天的数据库洞察缓存")

        flash(f'正在重新生成 {days} 天洞察...', 'info')

        # 同步生成新的洞察，确保用户能看到最新的洞察
        try:
            logger.info(f"重新生成洞察开始: insights_{days}")
            new_insights = analyzer.get_research_insights(days)
            logger.info(f"洞察重新生成完成: insights_{days}")
            flash('洞察已成功更新！', 'success')
        except Exception as e:
            logger.error(f"洞察重新生成失败: {e}")
            flash(f"生成洞察失败: {str(e)}", 'error')

    except Exception as e:
        logger.error(f"清除洞察缓存失败: {e}")
        flash(f"操作失败: {str(e)}", 'error')

    return redirect(url_for('insights', days=days))

@app.route('/set_keyword', methods=['POST'])
def set_keyword():
    """切换当前关键词"""
    keyword = request.form.get('keyword', '').strip()
    if keyword and keyword_manager.set_current_keyword(keyword):
        flash(f'已切换到关键词: {keyword_manager.get_current_config().display_name}', 'success')
        logger.info(f"关键词切换到: {keyword}")
    else:
        flash('切换关键词失败', 'error')
        logger.error(f"切换关键词失败: {keyword}")

    # 返回到之前的页面
    return redirect(request.referrer or url_for('index'))

@app.route('/add_keyword_auto', methods=['POST'])
def add_keyword_auto():
    """使用自动查询生成添加新关键词"""
    name = request.form.get('name', '').strip().replace(' ', '_').lower()
    display_name = request.form.get('display_name', '').strip()
    user_keywords = request.form.get('user_keywords', '').strip()

    # 获取搜索字段选项
    search_fields = request.form.getlist('search_fields')
    use_synonyms = request.form.get('use_synonyms') == 'on'
    use_categories = request.form.get('use_categories') == 'on'

    if not name or not display_name or not user_keywords:
        flash('请填写完整的关键词信息', 'error')
        return redirect(url_for('keywords'))

    # 使用自动查询生成
    success, generated_query = keyword_manager.add_keyword_auto(
        name=name,
        display_name=display_name,
        user_keywords=user_keywords,
        search_fields=search_fields or ['all'],
        use_categories=use_categories
    )

    if success:
        flash(f'已添加关键词: {display_name} (查询: {generated_query})', 'success')
        logger.info(f"自动添加关键词: {name} ({display_name}) - 查询: {generated_query}")
    else:
        flash(f'关键词已存在或添加失败: {display_name}', 'error')

    return redirect(url_for('keywords'))

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    """添加新关键词（手动模式）"""
    name = request.form.get('name', '').strip().replace(' ', '_').lower()
    display_name = request.form.get('display_name', '').strip()
    search_query = request.form.get('search_query', '').strip()

    if not name or not display_name or not search_query:
        flash('请填写完整的关键词信息', 'error')
        return redirect(url_for('keywords'))

    if keyword_manager.add_keyword(name, display_name, search_query):
        flash(f'已添加关键词: {display_name}', 'success')
        logger.info(f"添加关键词: {name} ({display_name})")
    else:
        flash(f'关键词已存在或添加失败: {display_name}', 'error')

    return redirect(url_for('keywords'))

@app.route('/remove_keyword', methods=['POST'])
def remove_keyword():
    """删除关键词"""
    keyword = request.form.get('keyword', '').strip()
    current_keyword = keyword_manager.get_current_keyword()

    if keyword == current_keyword:
        flash('不能删除当前使用的关键词', 'error')
        return redirect(url_for('keywords'))

    config = keyword_manager.get_keyword_config(keyword)
    display_name = config.display_name if config else keyword

    if keyword_manager.remove_keyword(keyword):
        flash(f'已删除关键词: {display_name}', 'success')
        logger.info(f"删除关键词: {keyword}")
    else:
        flash(f'删除关键词失败: {display_name}', 'error')

    return redirect(url_for('keywords'))

@app.route('/')
def index():
    """主页"""
    # 获取当前组件
    current_scraper, current_analyzer, current_exporter = get_current_components()

    # 获取当前关键词信息
    current_config = keyword_manager.get_current_config()
    all_keywords = keyword_manager.get_all_keywords()

    # 获取当前关键词的实时状态（替代调度器的固定状态）
    current_papers_7d = current_scraper.db.get_recent_papers(7)
    current_papers_count = len(current_papers_7d)

    # 构建动态状态信息
    status = {
        'is_running': scheduler.is_running,
        'next_run': schedule.next_run() if hasattr(schedule, 'next_run') else None,
        'recent_papers_count': current_papers_count,  # 当前关键词的7天论文数
        'keywords': [current_config.display_name],  # 当前关键词
        'schedule_time': settings.SCHEDULE_TIME,
        'max_papers_per_day': settings.MAX_PAPERS_PER_DAY
    }

    # 获取最新10篇论文（不限制时间范围，显示最新的研究成果）
    recent_papers = current_scraper.db.get_recent_papers(30)  # 获取更多论文用于筛选
    # 按发表时间排序并取最新的10篇
    recent_papers.sort(key=lambda p: p.published_date, reverse=True)
    recent_papers = recent_papers[:10]

    return render_template('index.html',
                         status=status,
                         recent_papers=recent_papers,
                         current_keyword=current_config,
                         all_keywords=all_keywords)

@app.route('/keywords', methods=['GET'])
def keywords():
    """关键词管理页面"""
    all_keywords = keyword_manager.get_all_keywords()
    current_config = keyword_manager.get_current_config()

    return render_template('keywords_simple.html',
                         keywords=all_keywords,
                         current_keyword=keyword_manager.get_current_keyword(),
                         current_keyword_config=current_config)

@app.route('/keywords_simple', methods=['GET'])
def keywords_simple():
    """简化关键词管理页面"""
    all_keywords = keyword_manager.get_all_keywords()
    current_config = keyword_manager.get_current_config()

    return render_template('keywords_simple.html',
                         keywords=all_keywords,
                         current_keyword=keyword_manager.get_current_keyword(),
                         current_keyword_config=current_config)

@app.route('/add_keyword_multi', methods=['POST'])
def add_keyword_multi():
    """添加多关键词"""
    try:
        name = request.form.get('name', '').strip()
        display_name = request.form.get('display_name', '').strip()
        keywords_str = request.form.get('keywords', '').strip()
        logic = request.form.get('logic', 'AND').strip()

        if not name or not display_name or not keywords_str:
            flash('请填写所有必填字段', 'error')
            return redirect(url_for('keywords'))

        # 解析关键词列表
        keywords_list = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]

        if len(keywords_list) == 0:
            flash('请至少添加一个关键词', 'error')
            return redirect(url_for('keywords'))

        # 添加多关键词
        success, generated_query = keyword_manager.add_keyword_multi(
            name=name,
            display_name=display_name,
            keywords=keywords_list,
            logic=logic,
            use_categories='use_categories' in request.form
        )

        if success:
            flash(f'关键词 "{display_name}" 添加成功！', 'success')
            flash(f'生成的查询: {generated_query}', 'info')
        else:
            flash('关键词名称已存在', 'error')

    except Exception as e:
        app.logger.error(f"添加关键词失败: {e}")
        flash(f'添加关键词失败: {str(e)}', 'error')

    return redirect(url_for('keywords'))

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

    # 添加总论文数
    try:
        current_scraper, _, _ = get_current_components()
        status['total_papers'] = current_scraper.db.get_total_papers_count()
    except Exception as e:
        print(f"Error getting total papers count: {e}")
        status['total_papers'] = 0

    return render_template('settings.html', config=config, status=status)

@app.route('/papers')
def papers():
    """论文列表"""
    # 获取当前关键词的组件
    current_scraper, current_analyzer, current_exporter = get_current_components()

    page = int(request.args.get('page', 1))
    per_page = 20
    search = request.args.get('search', '').strip()
    days = int(request.args.get('days', 30))

    if search:
        papers = current_scraper.db.search_papers(search)
    elif days == 0:  # 0 表示所有时间
        papers = current_scraper.db.get_all_papers()
    else:
        papers = current_scraper.db.get_recent_papers(days)

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
    # 获取当前关键词的组件
    current_scraper, current_analyzer, current_exporter = get_current_components()
    paper = current_scraper.db.get_paper_by_arxiv_id(arxiv_id)
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

        # 验证用户输入的数量
        try:
            additional_count = int(request.form.get('additional_count', 10))
        except (ValueError, TypeError):
            additional_count = 10

        # 限制在合理范围内
        if additional_count < 1:
            additional_count = 1
        elif additional_count > 200:
            additional_count = 200
            flash('请求数量超过最大限制，已调整为200篇', 'warning')

        logger.info(f"用户请求爬取 {additional_count} 篇论文")

        # 获取当前关键词的组件和配置
        current_scraper, current_analyzer, current_exporter = get_current_components()
        current_config = keyword_manager.get_current_config()

        # 使用当前关键词的搜索查询
        search_query = current_config.search_query
        keywords = [search_query]  # 转换为列表格式以兼容现有接口

        logger.info(f"使用当前关键词进行爬取: {current_config.display_name} ({search_query})")
        saved_count = current_scraper.scrape_more_papers(keywords, additional_count)
        flash(f'增量爬取完成，额外保存了 {saved_count} 篇新论文', 'success')

        # 如果保存了新论文，自动生成摘要
        if saved_count > 0:
            logger.info(f"开始为没有摘要的论文生成AI摘要...")

            # 获取所有没有摘要的论文
            papers_needing_summary = current_scraper.db.get_papers_without_summary()
            logger.info(f"找到 {len(papers_needing_summary)} 篇论文需要生成AI摘要（总共保存了 {saved_count} 篇新论文）")

            
            if papers_needing_summary:
                # 设置后台任务状态
                background_tasks['ai_analysis_running'] = True
                background_tasks['ai_analysis_progress'] = 0
                background_tasks['ai_analysis_total'] = len(papers_needing_summary)
                background_tasks['ai_analysis_start_time'] = datetime.now()

                # 获取当前关键词配置和组件，传递给后台线程
                current_keyword = keyword_manager.get_current_keyword()
                current_config = keyword_manager.get_current_config()
                papers_to_process = papers_needing_summary.copy()  # 创建副本避免闭包问题

                # 启动后台任务处理AI摘要生成
                def background_ai_analysis():
                    try:
                        # 在后台线程中重新初始化组件
                        from src.core.scraper import ArxivScraper
                        from src.core.analyzer import DeepSeekAnalyzer

                        # 使用当前关键词初始化scraper和analyzer，确保数据库路径正确
                        scraper = ArxivScraper(keyword=current_keyword)
                        analyzer = DeepSeekAnalyzer(keyword=current_keyword)
                        global_analyzer = analyzer  # 使用本地实例

                        logger.info(f"🔗 Background thread DB paths:")
                        logger.info(f"  Scraper: {scraper.db.db_path}")
                        logger.info(f"  Analyzer: {analyzer.db.db_path}")
                        logger.info(f"  Config: {current_config.db_path}")

                        analyzed_count = 0
                        total_count = len(papers_to_process)

                        logger.info(f"🔄 后台线程已启动，需要处理 {total_count} 篇论文")

                        for i, paper in enumerate(papers_to_process):
                            logger.info(f"正在生成论文摘要 ({i+1}/{total_count}): {paper.title[:50]}...")
                            try:
                                summary = analyzer.generate_summary(paper)
                                if summary:
                                    analyzer._update_paper_summary(paper.arxiv_id, summary)
                                    analyzed_count += 1
                                    logger.info(f"✅ 完成第 {i+1}/{total_count} 篇论文摘要")
                                else:
                                    logger.warning(f"❌ 第 {i+1}/{total_count} 篇论文摘要生成失败")
                            except Exception as paper_error:
                                logger.error(f"❌ 第 {i+1}/{total_count} 篇论文处理异常: {paper_error}")

                            # 更新进度
                            background_tasks['ai_analysis_progress'] = i + 1

                            # 添加延迟避免API限制
                            import time
                            time.sleep(1)

                        logger.info(f"🎉 后台AI摘要生成完成，成功处理 {analyzed_count}/{total_count} 篇论文")

                        # 数据库更新后，自动更新洞察缓存
                        logger.info("数据库已更新，开始自动更新洞察缓存...")

                        # 更新不同时间范围的洞察
                        for days in [1, 7, 30]:
                            try:
                                updated = global_analyzer.auto_update_insights_if_needed(days)
                                if updated:
                                    logger.info(f"成功更新 {days} 天洞察缓存")
                                else:
                                    logger.info(f"{days} 天洞察缓存已是最新，无需更新")
                            except Exception as e:
                                logger.error(f"更新 {days} 天洞察缓存失败: {e}")

                    except Exception as e:
                        logger.error(f"后台AI摘要生成失败: {e}")
                        import traceback
                        logger.error(f"错误详情: {traceback.format_exc()}")
                    finally:
                        # 重置任务状态
                        background_tasks['ai_analysis_running'] = False
                        logger.info("🔄 后台任务状态已重置")

                # 启动后台线程
                import threading
                logger.info("🚀 准备启动后台线程...")
                background_thread = threading.Thread(target=background_ai_analysis, daemon=True)
                background_thread.start()

                paper_count = len(papers_to_process)
                logger.info(f"🚀 已启动后台AI分析任务，处理 {paper_count} 篇论文")
                flash(f'已启动后台AI分析，正在处理 {paper_count} 篇论文，请稍后查看结果', 'info')

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

                        # 洞察已通过analyzer自动缓存到数据库
                        logger.info("后台洞察更新完成")
                    except Exception as e:
                        logger.error(f"后台洞察更新失败: {e}")

                # 启动后台线程
                insights_thread = threading.Thread(target=auto_update_insights, daemon=True)
                insights_thread.start()
                logger.info("已启动后台洞察更新任务")

            except Exception as e:
                logger.error(f"启动后台洞察更新失败: {e}")

            # 洞察缓存现在通过数据库管理，无需手动清除
            logger.info("洞察缓存通过数据库自动管理")

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

    cached_insights = analyzer.db.get_insights_cache(cache_key)

    status = {
        'cache_key': cache_key,
        'has_cache': cached_insights is not None,
        'last_updated': cached_insights.get('updated_at') if cached_insights else None,
        'is_generating': cache_key in analyzer._generating_insights
    }

    return jsonify(status)

@app.route('/insights')
def insights():
    """研究洞察 - 基于数据库更新状态的智能缓存"""
    days = int(request.args.get('days', 7))

    # 获取当前关键词的组件
    current_scraper, current_analyzer, current_exporter = get_current_components()

    # 为当前关键词创建缓存键
    current_keyword = keyword_manager.get_current_keyword()
    cache_key = f'{current_keyword}_insights_{days}'

    try:
        # 直接使用数据库缓存，无需等待
        logger.info(f"获取洞察数据: {cache_key}")

        # 检查缓存是否存在且有效
        cached_data = current_analyzer.db.get_insights_cache(cache_key)

        if cached_data:
            # 获取当前数据的哈希值
            current_hash = current_analyzer.db.get_data_hash(days)
            logger.debug(f"缓存数据哈希: {cached_data.get('data_hash', 'None')[:8]}..., 当前哈希: {current_hash[:8]}...")

            if cached_data.get('data_hash') == current_hash:
                logger.info(f"数据未更新，使用缓存洞察: {cache_key}")
                insights = cached_data['insights']
                trending = cached_data.get('trending', [])
            else:
                # 数据哈希不匹配，可能需要重新生成
                logger.info(f"数据哈希不匹配，尝试重新生成洞察: {cache_key}")

                # 尝试获取最新的缓存（可能在其他请求中已经更新）
                latest_cached_data = current_analyzer.db.get_insights_cache(cache_key)

                if latest_cached_data and latest_cached_data.get('data_hash') == current_hash:
                    logger.info(f"发现更新的缓存，使用新洞察: {cache_key}")
                    insights = latest_cached_data['insights']
                    trending = latest_cached_data.get('trending', [])
                else:
                    # 确实需要重新生成
                    logger.info(f"需要重新生成洞察: {cache_key}")

                    # 同步生成新洞察
                    try:
                        insights = current_analyzer.get_research_insights(days)
                        if insights and not insights.startswith("生成洞察失败"):
                            trending = current_analyzer.get_trending_topics(days)
                        else:
                            trending = []
                    except Exception as e:
                        logger.error(f"生成洞察失败: {e}")
                        insights = f"生成洞察失败: {str(e)}"
                        trending = []
        else:
            # 没有缓存数据，同步生成（首次访问）
            logger.info(f"首次访问，生成洞察: {cache_key}")
            try:
                insights = current_analyzer.get_research_insights(days)
                if insights and not insights.startswith("生成洞察失败"):
                    trending = current_analyzer.get_trending_topics(days)
                else:
                    trending = []
            except Exception as e:
                logger.error(f"生成洞察失败: {e}")
                insights = f"生成洞察失败: {str(e)}"
                trending = []

    except Exception as e:
        logger.error(f"获取洞察失败: {e}")
        insights = f"获取洞察失败: {str(e)}"
        trending = []

    # 计算实际的数据范围（在try-except块之外，确保总是执行）
    try:
        actual_papers = current_analyzer.db.get_recent_papers(days)
        actual_papers_count = len(actual_papers)

        if actual_papers_count > 0:
            earliest_date = min(paper.published_date.date() for paper in actual_papers)
            latest_date = max(paper.published_date.date() for paper in actual_papers)
            actual_range = f"{earliest_date} 到 {latest_date}"
        else:
            actual_range = "无数据"
    except Exception as e:
        logger.error(f"获取实际数据范围失败: {e}")
        actual_papers_count = 0
        actual_range = "数据获取失败"

    # 将洞察内容转换为HTML格式以支持Markdown
    try:
        if insights and not insights.startswith("生成洞察失败") and not insights.startswith("获取洞察失败"):
            # 清理AI生成内容中的markdown代码块标记
            cleaned_insights = insights.strip()
            if cleaned_insights.startswith('```markdown'):
                # 移除开头的```markdown
                cleaned_insights = cleaned_insights[11:].strip()
                # 移除结尾的```
                if cleaned_insights.endswith('```'):
                    cleaned_insights = cleaned_insights[:-3].strip()
            elif cleaned_insights.startswith('```'):
                # 处理其他代码块标记
                cleaned_insights = cleaned_insights[3:].strip()
                if cleaned_insights.endswith('```'):
                    cleaned_insights = cleaned_insights[:-3].strip()

            # 使用markdown库转换内容
            insights_html = markdown.markdown(
                cleaned_insights,
                extensions=['tables', 'fenced_code', 'toc', 'nl2br'],
                extension_configs={
                    'tables': {},
                    'fenced_code': {},
                    'toc': {},
                    'nl2br': {}
                }
            )
        else:
            insights_html = insights
    except Exception as e:
        logger.warning(f"Markdown转换失败，使用原始内容: {e}")
        insights_html = insights

    # 获取当前关键词信息用于模板显示
    current_config = keyword_manager.get_current_config()
    all_keywords = keyword_manager.get_all_keywords()

    return render_template('insights.html',
                     insights=insights_html,
                     trending=trending,
                     days=days,
                     actual_papers_count=actual_papers_count,
                     actual_range=actual_range,
                     current_keyword=current_config,
                     all_keywords=all_keywords)

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

    # 获取当前关键词的组件
    current_scraper, current_analyzer, current_exporter = get_current_components()

    # 如果days为-1，获取所有数据
    if days == -1:
        # 获取所有论文（需要修改数据库方法来支持获取所有数据）
        papers = current_scraper.db.get_all_papers() if hasattr(current_scraper.db, 'get_all_papers') else current_scraper.db.get_recent_papers(3650)  # 10年作为"全部"
    else:
        papers = current_scraper.db.get_recent_papers(days)

    if not papers:
        flash('没有数据可导出', 'warning')
        return redirect(url_for('papers'))

    try:
        if export_format == 'json':
            filepath = current_exporter.export_to_json(papers)
        elif export_format == 'markdown':
            filepath = current_exporter.export_to_markdown(papers)
        elif export_format == 'bibtex':
            filepath = current_exporter.export_to_bibtex(papers)
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
    # 获取当前关键词的组件
    current_scraper, current_analyzer, current_exporter = get_current_components()

    search = request.args.get('search', '').strip()
    days = int(request.args.get('days', 30))

    if search:
        papers = current_scraper.db.search_papers(search)
    else:
        papers = current_scraper.db.get_recent_papers(days)

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
    # 获取当前关键词的组件
    current_scraper, current_analyzer, current_exporter = get_current_components()

    days = int(request.args.get('days', 7))
    try:
        insights = current_analyzer.get_research_insights(days)
        trending = current_analyzer.get_trending_topics(days)
        return jsonify({
            'insights': insights,
            'trending': trending
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/paper/<arxiv_id>/bibtex')
def api_paper_bibtex(arxiv_id):
    """API: 获取单个论文的BibTeX格式"""
    # 获取当前关键词的组件
    current_scraper, current_analyzer, current_exporter = get_current_components()

    try:
        paper = current_scraper.db.get_paper_by_arxiv_id(arxiv_id)
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