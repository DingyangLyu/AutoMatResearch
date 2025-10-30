# arXiv论文自动爬取Agent

基于DeepSeek的智能论文自动爬取和分析系统，可以每天自动爬取指定关键词的arXiv论文，并使用DeepSeek进行智能分析和摘要生成。

## 功能特性

- 🔍 **自动爬取**: 根据设定的关键词自动爬取arXiv最新论文
- 🤖 **智能分析**: 使用DeepSeek生成论文摘要和研究洞察
- ⏰ **定时任务**: 支持每日自动执行和周度分析报告
- 💾 **数据存储**: 本地SQLite数据库存储，支持去重
- 🔎 **搜索功能**: 支持在已爬取的论文中搜索
- 📊 **趋势分析**: 自动识别热门研究主题和趋势
- 🔄 **论文比较**: 支持多篇论文的智能比较分析

## 安装和配置

### 1. 环境要求

- Python 3.8+
- pip包管理器

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的DeepSeek API密钥：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 数据库配置
DATABASE_URL=sqlite:///arxiv_papers.db

# 爬取配置
MAX_PAPERS_PER_DAY=10
SEARCH_KEYWORDS=["materials science", "machine learning"]

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=arxiv_scraper.log

# 调度配置 (每天执行时间，格式：HH:MM)
SCHEDULE_TIME=09:00
```

## 使用方法

### 启动定时服务

```bash
python main.py --start
```

这会在每天早上9点自动执行爬取任务。

### 手动执行一次爬取

```bash
python main.py --run-once
```

### 更新搜索关键词

```bash
python main.py --keywords "transformer" "attention mechanism" "large language models"
```

### 搜索论文

```bash
python main.py --search "transformer"
```

### 获取研究洞察

```bash
python main.py --insights 7  # 获取最近7天的研究洞察
```

### 比较论文

```bash
python main.py --compare 2301.00001 2301.00002
```

### 查看热门主题

```bash
python main.py --trending 7  # 获取最近7天的热门主题
```

### 查看系统状态

```bash
python main.py --status
```

## 项目结构

```
AutoMatResearch/
├── main.py              # 主程序入口
├── config.py            # 配置管理
├── database.py          # 数据库操作
├── arxiv_scraper.py     # arXiv爬虫
├── deepseek_analyzer.py # DeepSeek分析器
├── scheduler.py         # 任务调度器
├── logger.py           # 日志配置
├── requirements.txt     # 依赖包列表
├── .env.example        # 环境变量模板
├── README.md           # 项目文档
├── logs/               # 日志文件目录
├── insights/           # 每日洞察目录
├── reports/            # 周度报告目录
├── trends/             # 热门主题目录
└── arxiv_papers.db     # SQLite数据库文件
```

## 配置说明

### 关键词配置

支持多个关键词，系统会搜索包含任一关键词的论文：

```env
SEARCH_KEYWORDS=["materials science", "machine learning"]
```

### 调度时间配置

设置每日执行时间（24小时制）：

```env
SCHEDULE_TIME=09:00  # 早上9点执行
```

### DeepSeek API配置

需要有效的DeepSeek API密钥：

```env
DEEPSEEK_API_KEY=your_api_key_here
```

## 输出文件

### 日志文件
- `logs/arxiv_scraper.log`: 主日志文件
- `logs/error_YYYYMM.log`: 错误日志文件

### 分析报告
- `insights/daily_insights_YYYYMMDD.txt`: 每日研究洞察
- `reports/weekly_report_YYYYMMDD.txt`: 周度研究报告
- `trends/trending_topics_YYYYMMDD.txt`: 热门主题分析

## 常见问题

### 1. DeepSeek API调用失败
- 检查API密钥是否正确
- 确认网络连接正常
- 检查API调用限制

### 2. arXiv爬取失败
- 检查网络连接
- 确认arXiv服务可访问
- 检查关键词格式

### 3. 数据库错误
- 确保有足够的磁盘空间
- 检查文件权限
- 重新初始化数据库

## 高级用法

### 自定义分析提示词

可以修改 `deepseek_analyzer.py` 中的提示词来自定义分析风格和内容。

### 扩展数据源

可以扩展 `arxiv_scraper.py` 来支持其他学术数据库。

### 自定义调度逻辑

可以修改 `scheduler.py` 来实现更复杂的调度策略。

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目！