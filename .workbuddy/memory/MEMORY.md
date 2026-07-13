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
