# 变更记录

> 2026-07-07 · 相对 `0ba335c` 的未提交改动

## 功能

1. **Web 服务重构**：删除 `app.py`，新增 `web_server.py`，启动命令改为 `python web_server.py`
2. **报告读取服务**：新增 `app/services/report_reader.py`，自动读取 `output/` 下最新 `weekly-YYYY-MM-DD.json`
3. **API 调整**：`/api/report` 返回前端文章列表；新增 `/api/meta` 返回日期、摘要等元数据
4. **数据格式适配**：signals 转为前端 `render.js` 所需字段（title / tags / hot / link 等）

## 文档

5. **README 重写**：补充安装、`.env` 配置、使用命令、项目结构及 Mermaid 时序图

## 仓库

6. **`.gitignore` 完善**：忽略 `.venv`、`__pycache__`、`output/`、`.env` 等不应提交的文件

## 说明

- 流水线输出文件名已统一为 `weekly-日期.md` / `.json`（`file_writer.py` 逻辑）
- 若历史中已跟踪 `__pycache__` 或 `output/`，需执行 `git rm -r --cached __pycache__ output/` 后提交，`.gitignore` 才会生效
