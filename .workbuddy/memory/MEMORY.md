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

## 期刊保留策略与并发锁（2026-07-16 新增，同日修正为「按周期」）
- 保留期数：`config.REPORT_RETAIN_ISSUES`（默认 5，环境变量 `AI_WEEKLY_RETAIN_ISSUES` 可覆盖）。
  含义 = 仅保留最近 **N 个不重复周期** 的期，更旧的自动删除。
- ⚠️ 去重/排序单位是「周期」不是单天：`date` 只是单天（如 2026-07-14），每期真正覆盖是
  `period_start`→`period_end`（如 2026年7月1日—2026年7月14日，双周窗口）。两期 `date` 不同但
  周期重叠时，旧的按 `date` 去重会误留，故 `retention.py` 用 **period_start 去重、period_end 排序**。
- 实现：`app/services/retention.py` 的 `cleanup_old_issues(keep, dry_run)`，解析中文「YYYY年M月D日」
  与 ISO「YYYY-MM-DD」两种日期；`sort_key=period_end`（回退 date/目录名），`dedup_key=period_start`
  （回退 sort_key）。按 sort_key 降序，保留前 N 个不重复 dedup_key，同周期旧副本一并删。
  **绝不删** `latest.json` / `.latest` 指针 / `tasks.json`。
- **永不删空（2026-07-16 末次加固）**：`cleanup_old_issues` 内 `keep = max(1, keep or REPORT_RETAIN_ISSUES)`，
  先判 `None` 再取下限 1，保证网页永远至少留 1 期内容（满足用户「网页有内容」诉求）。
- 触发时机：每次 `/api/collect` 成功跑完后在 `_run_collect` 末尾自动调用（"从现在开始"生效，不回删历史）。
  另提供手动接口 `POST /api/cleanup`（body `{"keep":5,"dry_run":false}`）。
- **周期边界对齐周一（2026-07-16 修正）**：原 `config.issue_period()` 是「now-13天→now」滚动窗口，起点落任意星期。
  改为**以周一为锚点的双周块**：`PERIOD_ANCHOR=datetime(2026,7,20)`（用户指定下周一，须为周一，可用 env
  `AI_WEEKLY_PERIOD_ANCHOR=YYYY-MM-DD` 覆盖）；`slot=(now-anchor).days//period_days`，
  `start=anchor+slot*period_days`，`end=start+period_days-1`。结果：起点恒周一、块长14天、相邻块相隔14天无重叠，
  任意触发日落在对应块内。`pipeline.py` 与 `report_builder.py` 都走此函数，两条生成路径同步生效。
  目录名仍用生成日 `date_tag`，不参与周期计算；旧数据（7/1、7/2 等）保持原样不回改。
  `python -c "from app.services.retention import cleanup_old_issues; ..."` 调用，**不经过网页 /api/collect**，
  保持单线、独立于网页。每次 cron 触发（每周一 09:00）都执行清理；发送仍受 14 天门槛（双周）控制。
  ⚠️ 远端需先 `git pull` 拿到新增的 `retention.py` 与 `config.REPORT_RETAIN_ISSUES`，否则报缺模块。
  建议 crontab：`0 9 * * 1 /home/jinqi/my-ai-weekly/weekly_send.sh >> .../scripts/weekly_send.log 2>&1`（下周一启用）。
- 并发锁：`web_server.py` 用 `COLLECT_LOCK` + `ACTIVE_COLLECT_DATES` 集合，配合磁盘 `tasks.json`
  兜底，使"今天正在采集中"再点 `/api/collect` 返回 `status:"running"` 而不双跑；原有"同一天文件已存在"
  仍返回 `already_updated`。前端 `runCollect` 已把 `running` 当提示（非报错）处理。
- 网页浏览侧：`/api/archive` 本就按日期去重列举现有目录，清理后自然只展示 ≤N 期不重复日期的期刊。
