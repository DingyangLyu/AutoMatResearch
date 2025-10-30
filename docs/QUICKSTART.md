# 🚀 快速开始指南

## 1. 环境准备

确保你的系统已安装Python 3.8+：

```bash
python --version
```

## 2. 安装系统

### 方式1: 快速安装 (推荐)

```bash
# 克隆项目
git clone https://github.com/DingyangLyu/AutoMatResearch.git
cd AutoMatResearch

# Windows环境
install.bat

# Linux环境
bash install.sh
```

### 方式2: 手动安装

```bash
# 克隆项目
git clone https://github.com/DingyangLyu/AutoMatResearch.git
cd AutoMatResearch

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
```

## 3. 配置API密钥

编辑 `.env` 文件，设置你的DeepSeek API密钥：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

## 4. 启动系统

### 方式1: Web界面 (推荐)

```bash
# 启动Web界面
python run.py --mode web --port 5000

# 访问 http://localhost:5000
```

### 方式2: 命令行界面

```bash
# 启动交互式CLI
python run.py --mode cli
```

### 方式3: 定时调度模式

```bash
# 启动定时任务服务
python run.py --mode scheduler
```

### 方式4: 系统设置

```bash
# 运行系统初始化设置
python run.py --mode setup
```

## 5. 首次使用

1. **启动Web界面**：
   ```bash
   python run.py --mode web --port 5000
   ```

2. **访问Web界面**：打开浏览器访问 http://localhost:5000

3. **配置关键词**：在Web界面的"关键词管理"页面添加研究关键词

4. **手动爬取**：在"系统配置"页面点击"立即爬取"测试功能

5. **查看论文**：在"论文列表"页面查看爬取的论文和分析结果

## 6. 常用命令速查

| 命令 | 功能 |
|------|------|
| `python run.py --mode web --port 5000` | 启动Web界面 |
| `python run.py --mode cli` | 启动命令行界面 |
| `python run.py --mode scheduler` | 启动定时调度服务 |
| `python run.py --mode setup` | 系统初始化设置 |

## 7. 文件说明

### 数据文件 (位于 `data/` 目录)
- `database/` - 数据库文件目录 (按关键词分类的SQLite数据库)
- `logs/` - 系统日志文件
- `exports/` - 导出的数据文件
- `insights/` - 研究洞察缓存文件

### 配置文件
- `.env` - 环境变量配置 (包含API密钥)
- `pyproject.toml` - 项目配置文件
- `requirements.txt` - Python依赖包列表

## 8. Web界面功能

### 主要页面
- **仪表板** (`/`) - 系统状态概览和统计信息
- **论文列表** (`/papers`) - 查看和搜索所有论文
- **论文详情** (`/paper/<id>`) - 单篇论文的详细信息和AI分析
- **关键词管理** (`/keywords`) - 管理搜索关键词
- **论文比较** (`/compare`) - 多篇论文智能比较分析
- **研究洞察** (`/insights`) - AI生成的热门趋势分析
- **系统配置** (`/settings`) - API配置和系统参数设置
- **数据导出** (`/export`) - 多格式数据导出功能

### 特色功能
- **现代化设计**: Bootstrap 5响应式界面
- **实时搜索**: 支持标题、作者、摘要全文搜索
- **智能比较**: AI驱动的论文深度比较分析
- **数据可视化**: 论文统计图表和趋势展示
- **批量操作**: 支持批量导出和处理

## 9. 故障排除

### 常见问题

**Q: DeepSeek API调用失败**
A: 在Web界面的"系统配置"页面检查API密钥是否正确设置，并测试连接。

**Q: 没有找到论文**
A: 尝试使用更通用的关键词，如 "machine learning" "deep learning"

**Q: 程序启动失败**
A: 确保所有依赖已正确安装并激活虚拟环境：
```bash
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

**Q: Web界面无法访问**
A: 检查端口是否被占用，可以尝试其他端口：
```bash
python run.py --mode web --port 5001
```

### 获取帮助

- 查看详细文档：`README.md`
- 查看使用指南：`docs/USAGE_GUIDE.md`
- 项目地址：https://github.com/DingyangLyu/AutoMatResearch

---

🎉 **恭喜！你已经成功设置了arXiv论文自动爬取系统！**