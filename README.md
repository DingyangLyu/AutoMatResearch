# AutoMatResearch - arXiv论文自动爬取和分析系统

基于DeepSeek的智能论文自动爬取和分析系统，可以每天自动爬取指定关键词的arXiv论文，并使用DeepSeek进行智能分析和摘要生成。

## 🌟 项目亮点

- **🤖 AI驱动分析**: 集成DeepSeek大模型，提供深度论文分析和研究洞察
- **⚡ 高效爬取**: 智能去重和增量更新，避免重复处理
- **🔧 灵活配置**: 支持自定义关键词、爬取频率和分析策略
- **📊 数据可视化**: Web界面展示论文趋势和统计信息

> **注意**: 项目已进行代码清理，删除了所有缓存文件和重复内容，提升了运行效率和代码可维护性。

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip包管理器

### 方式一：克隆仓库并可编辑安装

```bash
# 克隆仓库
git clone https://github.com/DingyangLyu/AutoMatResearch.git
cd AutoMatResearch

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 可编辑安装
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填入你的DeepSeek API密钥
```

### 方式二：传统安装方式

```bash
# 克隆仓库
git clone https://github.com/DingyangLyu/AutoMatResearch.git
cd AutoMatResearch

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件，填入你的DeepSeek API密钥
```

### 🎯 首次运行

```bash
# 1. 创建必要目录
mkdir -p data/{database,exports,logs,insights}

# 2. 运行Web应用
python run.py --mode web --port 5000

# 3. 访问Web界面
# 浏览器打开: http://localhost:5000
```

### 运行项目
```bash
# 启动命令行界面
python run.py --mode cli

# 启动Web界面
python run.py --mode web --port 5000

# 启动定时调度器
python run.py --mode scheduler

# 运行安装脚本
python run.py --mode setup
```

## 📁 项目结构

```
AutoMatResearch/
├── src/                     # 源代码主目录
│   ├── main.py             # 主程序入口
│   ├── cli/                # 命令行界面
│   │   ├── __init__.py
│   │   └── cli.py
│   ├── web/                # Web应用
│   │   ├── __init__.py
│   │   └── web_app.py
│   ├── core/               # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── scraper.py      # arXiv爬虫
│   │   ├── analyzer.py     # DeepSeek分析器
│   │   └── scheduler.py    # 任务调度器
│   ├── data/               # 数据访问层
│   │   ├── __init__.py
│   │   └── database.py
│   └── utils/              # 工具模块
│       ├── __init__.py
│       ├── config.py       # 配置管理（兼容层）
│       ├── logger.py       # 日志工具
│       └── utils.py        # 通用工具
├── config/                 # 配置文件
│   ├── .env.example        # 环境变量模板
│   ├── settings.py         # 统一配置管理
│   └── user_config.json    # 用户配置
├── data/                   # 运行时数据
│   ├── database/           # 数据库文件
│   ├── exports/            # 导出文件
│   └── insights/           # 分析洞察
├── web/                    # Web资源
│   ├── static/             # 静态文件
│   └── templates/          # HTML模板
├── scripts/                # 脚本文件
│   └── setup.py
├── docs/                   # 文档
├── logs/                   # 日志文件
├── run.py                  # 主启动脚本
├── requirements.txt        # 依赖包列表
├── .env.example           # 环境变量模板
├── .gitignore             # Git忽略文件
└── .claude/               # Claude配置
```

## 🔧 配置说明

### 环境变量配置 (.env)
```env
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# 数据库配置
DATABASE_URL=sqlite:///data/database/arxiv_papers.db

# 爬取配置
MAX_PAPERS_PER_DAY=10
SEARCH_KEYWORDS=["materials science", "machine learning"]

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=arxiv_scraper.log

# 调度配置
SCHEDULE_TIME=09:00
```

### 用户配置 (config/user_config.json)
用户可以通过此文件覆盖默认配置。

## 📋 功能特性

- 🔍 **自动爬取**: 根据设定的关键词自动爬取arXiv最新论文
- 🤖 **智能分析**: 使用DeepSeek生成论文摘要和研究洞察
- ⏰ **定时任务**: 支持每日自动执行和周度分析报告
- 💾 **数据存储**: 本地SQLite数据库存储，支持去重
- 🔎 **搜索功能**: 支持在已爬取的论文中搜索
- 📊 **趋势分析**: 自动识别热门研究主题和趋势
- 🔄 **论文比较**: 支持多篇论文的智能比较分析
- 🌐 **Web界面**: 提供友好的Web管理界面
- 💻 **CLI工具**: 功能完整的命令行界面

## 🎯 使用方式

### 命令行模式
```bash
python run.py --mode cli
```

CLI提供以下命令：
- `status` - 查看系统状态
- `run` - 手动执行一次爬取
- `keywords` - 管理搜索关键词
- `search <关键词>` - 搜索论文
- `insights [天数]` - 获取研究洞察
- `compare <论文ID1> <论文ID2>` - 比较论文
- `trending [天数]` - 查看热门主题
- `export [格式]` - 导出数据

### Web界面模式
```bash
python run.py --mode web --port 5000
```

访问 http://localhost:5000 使用Web界面。

### 定时调度模式
```bash
python run.py --mode scheduler
```

启动定时任务，每天自动执行爬取和分析。

## 📊 输出文件

### 日志文件
- `logs/arxiv_scraper.log`: 主日志文件
- `logs/error_YYYYMM.log`: 错误日志文件

### 分析报告
- `data/insights/daily_insights_YYYYMMDD.txt`: 每日研究洞察
- `data/exports/papers_export_YYYYMMDD_HHMMSS.json`: 论文数据导出

### 数据库
- `data/database/arxiv_papers.db`: SQLite数据库

## 🧪 开发指南

### 添加新功能
1. 在相应的模块目录下添加新文件
2. 更新配置（如需要）
3. 添加测试
4. 更新文档

### 代码规范
- 使用类型提示
- 遵循PEP 8规范
- 编写docstring文档
- 添加单元测试

## 📝 项目维护说明

### 最近更新 (2025-10-30)
- **🎉 项目初始化**: 完成项目初始化和基础架构搭建
- **🔧 SSH配置**: 配置Git SSH密钥，实现无密码推送
- **📝 文档完善**: 更新README文档，修正仓库链接和项目信息
- **🧹 代码清理**: 删除了所有 Python 缓存文件 (`__pycache__` 和 `.pyc`)
- **📁 结构优化**: 移除重复内容，清理日志目录和空目录

### 重构说明
本项目经过重构，采用了模块化的项目结构：

#### 主要改进
1. **清晰的分层架构**: src/包含所有源代码，按功能模块组织
2. **职责分离**: 核心逻辑、数据层、工具模块分开管理
3. **配置集中**: 统一的配置管理系统
4. **数据统一管理**: 运行时数据都在data/目录下
5. **便于维护和扩展**: 模块化设计便于添加新功能

#### 迁移指南
- 旧的启动方式 `python start.py` 现在改为 `python run.py`
- 所有Python模块现在位于src/目录下
- 配置文件移动到config/目录
- 数据文件移动到data/目录
- 日志文件统一放在logs/目录

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📞 联系方式

- **项目维护者**: DingyangLyu
- **GitHub**: [@DingyangLyu](https://github.com/DingyangLyu)
- **邮箱**: s-ldy25@bjzgca.edu.cn

## 📈 项目状态

![GitHub stars](https://img.shields.io/github/stars/DingyangLyu/AutoMatResearch)
![GitHub forks](https://img.shields.io/github/forks/DingyangLyu/AutoMatResearch)
![GitHub issues](https://img.shields.io/github/issues/DingyangLyu/AutoMatResearch)
![GitHub license](https://img.shields.io/github/license/DingyangLyu/AutoMatResearch)

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/DingyangLyu/AutoMatResearch.git
cd AutoMatResearch

# 创建开发环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 可编辑安装（包含开发依赖）
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black src/ tests/

# 类型检查
mypy src/
```

### 提交规范

- 使用清晰的提交信息
- 确保代码通过测试
- 遵循PEP 8代码规范
- 更新相关文档

## 📄 许可证

MIT License