# ai-weekly

AI 资讯采集 → LLM 分析 → 周报生成 → Web 展示。

## 安装

```powershell
git clone https://github.com/deerXXL/my-ai-weekly.git
cd my-ai-weekly
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install flask python-dotenv openai requests beautifulsoup4 feedparser
```

> `requirements.txt` 为 Conda 全量导出，勿直接 `pip install -r`。

## 配置

根目录创建 `.env`：

```env
ARK_API_KEY=你的火山方舟Coding_Plan_API_Key
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
ARK_MODEL=ark-code-latest
```

API Key 在 [火山方舟控制台](https://console.volcengine.com/ark) 获取。

## 使用

```powershell
# 生成日报 → output/weekly-日期.md / .json
python run_test.py

# 启动前端 → http://127.0.0.1:5000
python web_server.py

# 定时任务（每天 9:00，可选）
python scheduler.py
```

Windows 若 emoji 乱码：`$env:PYTHONIOENCODING='utf-8'`

## 项目结构

```
app/crawlers/    爬虫        run_test.py      生成日报
app/services/    LLM/输出    web_server.py    Web 展示
app/pipeline.py  主流程      scheduler.py     定时任务
templates/ + static/         前端页面
output/                      输出文件
```

## 使用时序

```mermaid
sequenceDiagram
    actor U as 用户
    participant R as run_test.py
    participant P as pipeline
    participant C as crawlers
    participant L as 火山 LLM
    participant O as output/

    U->>R: python run_test.py
    R->>P: run_pipeline()
    P->>C: 爬取 GitHub / OpenAI / HuggingFace
    C-->>P: 原始资讯列表
    P->>L: 逐条分析 signal
    L-->>P: signal / insight / impact
    P-->>R: DailyReport
    R->>O: weekly-日期.md + .json

    U->>W: python web_server.py
    participant W as web_server
    participant B as 浏览器

    W-->>B: 返回 index.html
    B->>W: GET /api/report
    W->>O: 读取最新 weekly-日期.json
    O-->>W: signals → 前端格式
    W-->>B: 渲染列表 / 热榜
```
