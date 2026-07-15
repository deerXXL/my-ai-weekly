# 项目长期记忆（闪联AI周刊）

## 路径约定（重要！）
- 项目根 = `D:\AI2.0`。`config.py` 在项目根，故 `BASE_DIR` 应用 `parents[0]`（不是 parents[1]）。
- `config.OUTPUT_DIR` 被读路径（`issue_paths` → `export_builder.load_latest_report_dict`、
  `/api/report`、`/api/meta`、`/api/export`、sources 配置）共用，必须指向 `D:\AI2.0\output`。
- 写路径（`report_builder.py`、`web_server.py`）各自用「文件所在层级的 parents[N]」算 OUTPUT_DIR，
  与 `config.OUTPUT_DIR` 应保持一致，改路径类代码时务必同步核对。
- Flask 静态文件路由是 `/output/<path:filename>`，前端/API 拼图片/封面地址必须带 `/output/` 前缀，
  且 issue 目录前缀（`weekly-YYYY-MM-DD/`）只出现一次。

## 启动方式
- 入口：`web_app.py`（`use_reloader=False`）；`web_server.py` 内 `app.run(debug=True)`。
- 依赖隔离：在 managed venv（`python -m venv .../envs/default`）装 `python-dotenv`、`flask` 后可直接跑。

## 运行环境要求（部署网页服务时极易踩坑）
- `/api/collect`（新增本期资讯）会跑完整流水线，必须能访问火山方舟端点
  `https://ark.cn-beijing.volces.com`，且环境变量 `ARK_API_KEY` / `ARK_BASE_URL` / `ARK_MODEL`
  与本地 `.env` 一致（本地用 `api/coding/v3` + `ark-code-latest`）。
  若部署到 CloudStudio/沙箱等无外网或未注入 Secret 的环境，LLM 分析会全挂 → 报
  "没有成功分析的资讯条目"。`pipeline.py` 现已把真实异常原因带进该报错，便于定位。
- 导出（`/api/export`）返回自包含 ZIP（md+html+images），解压即可看图。

## 邮件发送（send_md_email.py）
- 附件路径格式：`output/weekly-YYYY-MM-DD/newsletter.md`（不是 `output/weekly-YYYY-MM-DD.md`）。
- QQ邮箱 SMTP 需要 `port=465, smtp_ssl=True`。
- yagmail 依赖链：`yagmail` → `premailer` → `cssutils` → `more-itertools`，缺 `more-itertools` 会报 `ModuleNotFoundError`。
