# 🚀 快速开始指南

## 1. 环境准备

确保你的系统已安装Python 3.8+：

```bash
python --version
```

## 2. 安装系统

```bash
# 克隆或下载项目到本地
cd AutoMatResearch

# 运行自动安装脚本
python setup.py
```

## 3. 配置API密钥

编辑 `.env` 文件，设置你的DeepSeek API密钥：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

## 4. 启动系统

### 方式1: 交互式命令行界面 (推荐新手)

```bash
python start.py --mode cli
```

### 方式2: Web界面 (推荐图形用户)

```bash
python start.py --mode web
# 然后访问 http://localhost:5000
```

### 方式3: 命令行工具 (适合自动化)

```bash
# 手动执行一次爬取
python main.py --run-once

# 启动定时服务 (每天自动爬取)
python main.py --start

# 更新关键词
python main.py --keywords "transformer" "attention mechanism"

# 搜索论文
python main.py --search "machine learning"

# 查看最近7天的研究洞察
python main.py --insights 7
```

### 方式4: Docker部署 (推荐服务器)

```bash
# 配置环境变量
cp .env.example .env
# 编辑.env文件设置DEEPSEEK_API_KEY

# 使用Docker Compose启动
docker-compose up -d
```

## 5. 首次使用

1. **设置关键词**：
   ```bash
   python main.py --keywords "machine learning" "deep learning" "transformer"
   ```

2. **测试爬取**：
   ```bash
   python main.py --run-once
   ```

3. **查看结果**：
   ```bash
   python main.py --recent 7
   ```

## 6. 常用命令速查

| 命令 | 功能 |
|------|------|
| `python start.py --mode cli` | 启动交互式界面 |
| `python start.py --mode web` | 启动Web界面 |
| `python main.py --run-once` | 手动爬取一次 |
| `python main.py --start` | 启动定时服务 |
| `python main.py --keywords "新关键词"` | 更新关键词 |
| `python main.py --search "关键词"` | 搜索论文 |
| `python main.py --insights 7` | 获取研究洞察 |
| `python main.py --trending 7` | 查看热门主题 |

## 7. 文件说明

- `arxiv_papers.db` - 论文数据库
- `logs/` - 日志文件
- `insights/` - 每日研究洞察
- `reports/` - 周度研究报告
- `trends/` - 热门主题分析
- `exports/` - 导出的数据文件

## 8. 故障排除

### 常见问题

**Q: DeepSeek API调用失败**
A: 检查 `.env` 文件中的 `DEEPSEEK_API_KEY` 是否正确设置

**Q: 没有找到论文**
A: 尝试使用更通用的关键词，如 "machine learning" 而不是 "very specific niche term"

**Q: 程序启动失败**
A: 确保所有依赖已正确安装：
```bash
pip install -r requirements.txt
```

### 获取帮助

- 查看详细文档：`README.md`
- 交互式帮助：`python start.py --mode cli` 然后输入 `help`
- 命令行帮助：`python main.py --help`

## 9. 进阶用法

### 自定义分析提示词

编辑 `deepseek_analyzer.py` 中的 `generate_summary` 方法来自定义摘要生成风格。

### 添加通知功能

使用 `utils.py` 中的 `NotificationManager` 设置邮件通知。

### 扩展数据源

修改 `arxiv_scraper.py` 来支持其他学术数据库。

---

🎉 **恭喜！你已经成功设置了arXiv论文自动爬取系统！**