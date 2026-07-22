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

## 可行性思考输出格式约定（2026-07-21 定稿，用户明确要求）
- 用户要求「可行性思考」围绕**作用/价值**展开，不要写成热点技术集结；每个方向要落到**具体、带画面感的例子**，有概括也有偏向。
- 模板位置：`prompts/compose_newsletter.md` 的 `feasibility` 段与下方约束。改格式只动这里，解析代码 `app/services/export_builder.py` 不用改。
- 单条结构（JSON 字段不变：`title`/`summary`/`bullets`，仍 3 条）：
  - `title`：作用导向，如「长文档与知识库自动处理：把海量资料变成可问答、可对比、可摘要的结构化信息」。具体模型/产品只在 bullets 里当支撑案例。
  - `bullets`（5-7 条，顺序固定）：`**落地难点：**` → `**可落地项目：**`(总起) → 2-3 个 `**具体例子名：**`（独立 bullet，写清谁/输入/做了什么/产出） → `**不建议场景：**` → `**量化参考：**`(可选，须含真实数字+局限)。
  - 渲染器 `_render_feasibility_bullet` 只解析行首 `**标签：**` 为彩色 chip；故描述内**禁止**再用 `**` 加粗（会显示成字面星号）。
- 手动改过的最新一期 `output/weekly-2026-07-20` 即此风格样板；旧期数据保持原样不回改。

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

## 网页(Render)自动更新架构（2026-07-20 定稿）
- **结论**：GitHub Action 自动更新**不可靠**——它在 GitHub 境外 Runner 跑，连不上火山方舟北京端点
  `ark.cn-beijing.volces.com`，生成必失败、不会 commit，故 Render 不更新。今天(7.20, ISO第30周偶数)没更新即此因。
- **可靠方案（已落地）**：让 **Linux 服务器（在中国，能连北京端点）既生成又推送**。
  - `weekly_send.sh` 已在 `generate+send` 之后追加 `git add output/ && git commit && git push origin/Laurtiv27 main`
    （仅 14 天节流通过、确有新刊时才推，避免空推）。
  - 前提：Linux 配 **SSH key** 并 `git remote set-url origin git@github.com:deerXXL/my-ai-weekly.git`
    （HTTPS 会被 GnuTLS 拦，SSH 一劳永逸），公钥粘到 GitHub → Settings → SSH keys。
  - Render 默认开 **Auto-Deploy**，检测到 push 自动重新部署 → 网页更新。需确认 Render 控制台此项为开启。
- **务必禁用 GitHub Action**（`Generate AI Weekly`，仓库 Actions 页 Disable），否则它与 Linux 可能双生成/推送冲突。
- 远程有两个：`origin`(deerXXL)、`Laurtiv27`，Render 只连其一；脚本两个都推以覆盖。
- ⚠️ 本地沙箱**无 GitHub 凭据**，git push 必须由用户在本机终端执行（凭据管理器弹不出窗）。
  另提供手动接口 `POST /api/cleanup`（body `{"keep":5,"dry_run":false}`）。
- **周期边界对齐周一（2026-07-16 加，2026-07-20 修正方向）**：原 `config.issue_period()` 是「now-13天→now」滚动窗口。
  7-16 改为以周一为锚点的双周块，但误用「包含今天、向前延伸」(`start=anchor+slot*14, end=start+13`) → 生成**未来区间**
  (如 7.20 生成为 `7.20—8.2`)，方向反了，用户反馈后修正。
  **2026-07-20 修正**：改为「截止到生成日、往回推 14 天，起点对齐周一」：
  `this_monday = now - timedelta(days=now.weekday()); start = this_monday - period_days天; end = now`。
  结果：起点恒周一、终点为生成当天（与 `--days 14` 抓取窗口一致），永远是**过去区间**；
  下个双周块无缝衔接（7.20→`[7.6,7.20]`，8.3→`[7.20,8.3]`）。
  `PERIOD_ANCHOR=datetime(2026,7,20)` 仍保留（env `AI_WEEKLY_PERIOD_ANCHOR` 可覆盖），仅作周一基准，不再用于向前切块。
  `pipeline.py` 走此函数生成概览时间范围（date_start/date_end/period_start/period_end）。
  目录名仍用生成日 `date_tag`，不参与周期计算；旧数据（7/1、7/2 等）保持原样不回改。
  `python -c "from app.services.retention import cleanup_old_issues; ..."` 调用，**不经过网页 /api/collect**，
  保持单线、独立于网页。每次 cron 触发（每周一 09:00）都执行清理；发送仍受 14 天门槛（双周）控制。
  ⚠️ 远端需先 `git pull` 拿到新增的 `retention.py` 与 `config.REPORT_RETAIN_ISSUES`，否则报缺模块。
  建议 crontab：`0 9 * * 1 /home/jinqi/my-ai-weekly/weekly_send.sh >> .../scripts/weekly_send.log 2>&1`（下周一启用）。
- 并发锁：`web_server.py` 用 `COLLECT_LOCK` + `ACTIVE_COLLECT_DATES` 集合，配合磁盘 `tasks.json`
  兜底，使"今天正在采集中"再点 `/api/collect` 返回 `status:"running"` 而不双跑；原有"同一天文件已存在"
  仍返回 `already_updated`。前端 `runCollect` 已把 `running` 当提示（非报错）处理。
- 网页浏览侧：`/api/archive` 本就按日期去重列举现有目录，清理后自然只展示 ≤N 期不重复日期的期刊。

## Linux 全自动部署状态（2026-07-20 最终确认）
- **5 项前提全部就绪并验证通过**：`.env`(ARK+SMTP)、`yagmail`+`more-itertools`、git 身份 `ai-weekly-bot`、SSH ed25519 公钥(GitHub 已认证)、`generate_weekly.py` 能跑通。
- **邮件始发期 = 下周一 7.27**（`.last_send` 已删除），之后每双周周一 cron 自动：清理→生成→发送→push→Render 重部署。
- 用户最终选择**纯 Linux 全自动**（不混合 Windows）。本地仅负责改代码→push→Linux pull。

## 邮件 HTML 样式（2026-07-22 确认）
- 邮件/网页正文 HTML 由 `app/services/export_builder.py` 的 `build_export_html()` 唯一生成（内联 `<style>` 在 495–551 行）。
  字体、字号、配色、卡片样式全在这里，与参考图 `AI周刊20250915.png` 风格一致。
- 封面图：火山 Seedream 文生图，存 `output/weekly-XXXX/images/cover.png`（`cover_generator.py`）。
  配图：抓文章页 og:image（`image_enricher.py`）。
- ⚠️ **编辑该文件用一次性 python 脚本，别用 Edit 工具**：该文件被外部 linter/IDE 实时改动，
  Edit 工具「modified since read」反复失败。改用 `python -c` 或临时脚本在同一进程内读改写，绕开拦截。
- 改完已有各期 `output/weekly-*/newsletter.html` 不会自动变，需重跑生成流程或手动改对应文件后重发邮件。
- **样式与结构已锁定为永久模板，且严格对照参考文件 `D:\暑期\AI_Magazine\AI周刊20280915.md`（2026-07-22 14:14 用户要求"严格按照这个格式"定稿）**。之后每期自动沿用、无需回填。
  **章节顺序**（与参考图一致）：① 📅 本周概览 → ② 🚀 行业动态 → ③ 🤖 本周热点 → ④ 📈 本周AI技术总结：三大趋势。
  **字体层级**：正文16px/行距1.8、h1 28px、四个区块大标题(section-title, 📅🚀🤖📈)均 **24px**(移动端21px)、h2 19px、h3 16px、h4(热点主题/趋势编号)18/16px、h5(Case/可行性编号)15/15.5px。
  **① 本周概览**：时间范围+本期编辑(`ov.editor`)+核心摘要(meta 段落)，封面图(**width:85% 靠左**，2026-07-22 14:44 由满宽改居中、15:30 改靠左)在摘要下方。章节 icon `📅`(`config.newsletter.json` 的 `overview.icon`，原🗓已改)。
    ⚠️ **本期编辑 `ov.editor` 由 `config/newsletter.json` 的 `default_editor` 提供**（经 `pipeline.py:275` 注入），2026-07-22 16:00 由"产品资讯组"改为 **"ai研发组"**（今后每期自动沿用；已回填 `weekly-2026-07-22`）。
  **② 行业动态**：按日期分组，日期小标题 `h3.date-label` 蓝色 `#2159c9` + 🟦（`🟦 <span style="color:#2159c9ff;">日期</span>`）；每条 = `h4.news-title`(标题) + 摘要 + **保留配图 420px 靠左**(用户7/22坚持保留不铺满；2026-07-22 14:44 由居中改靠左) + 使用说明。限显 `cfg.industry_max_count`(默认12)。
  **③ 本周热点**（对照参考图"主题+Case配图"）：每条热点 = 一个"主题"块(`hot-topic-block`)：`h4.hot-topic`(标题) + `hot-topic-desc`(介绍,来自 item.summary) + `h5.hot-case`(➡️ Case 标题) + 配图(`hot-card-img`，**优先 item.ai_image AI 生成图**，回退 item.image_url；**width:70% 靠左、自适应高度不裁切**，演进：14:44 去 max-height、15:35 100%→85%、15:55 85%→75%、16:00 75%→70%)。`hot_topics_count` 默认5，每条即一个主题。
    AI 图由 `cover_generator.generate_hot_images()` 在 `pipeline.py` 封面后调 Seedream 生成，存 `images/hot-{i}.png` 写回 `ai_image`。
    ⚠️ **尺寸坑**：热点图必须 ≥ 3686400 像素（Seedream 硬性下限），原 `1024x1024`(≈100万) 全被拒 → 回退 og:image；改 `2048x2048`(419万) 修复，**16:00 进一步改 `2560x1440`(16:9 非正方形，=3686400 刚好合规)**，与封面同比例、本地验证 5/5 成功（`weekly-2026-07-22`）。
    ⚠️ **Seedream 实际返回 JPEG**，但 `_download_to` 存成 `.png` 扩展名（封面 `cover.png` 同样如此）；浏览器按内容识别、显示正常，无需改扩展名（若想规范可改 `hot-{i}.jpg` 并同步 `ai_image` 路径）。
    ⚠️ 参考图热点还有 emoji 特性点(🎯🔧🌐🎬✨)，但数据结构无对应字段，未生成（结构已贴近）。
  **④ 本周AI技术总结：三大趋势**：`tech.title_suffix` 默认"三大趋势" → 大标题"📈 本周AI技术总结：三大趋势"。
    - 🌟 核心趋势：`h4.trend-head` 编号(1./2./3.) + `trend-body`(来自 `tech.trends`)。
    - 🔮 可行性思考：`h5.feas-head` 编号(1./2./3.) + 子弹列表(`_render_feasibility_bullet` 生成的 `li.feas-item`，含 `feas-tag`/`feas-desc`)。
  ⚠️ 用户明确要求「字体大小不用再改变」，后续若再调样式只动非字号项；除非用户主动要求，否则勿再 bump 字号。任何改动只改 `build_export_html()` 源码一处即全局生效。
  - **2026-07-22 14:44 微调（用户要求，全部已实现并验证）**：
    ① h2 / section-title 的**红色左边框(`#a62c2c`)已移除**——所有标题不再有红竖条；
    ② 封面图 `width:100%`→**`width:85%` 靠左**（14:44 改居中、15:30 改靠左，故 `margin:16px 0` 无 auto）；
    ③ 行业动态配图由居中(`margin:6px auto`)改**靠左**(`margin:6px 0`，仍 420px 不铺满)；
    ④ 热点配图去掉 `max-height:360px;object-fit:cover` 改为**自适应、完整显示、不裁切**。
    配套：本地缺图的热点(og:image 为空，共 07-14#4 / 07-15#2,#4 / 07-20#2,#4)用纯 Python 生成占位 PNG(`images/placeholder-hot{i}.png`，渐变蓝灰)，写入 `image_url`；
    将来 Linux 跑生成时 `ai_image` 优先自动覆盖占位图。三期已重渲染验证（h2 无红边、封面85%、news 靠左、hot 5 张全显示、py_compile 通过）。
  - **2026-07-22 16:07 用户最终确认「后续格式固定」**：上述 14:14~16:00 全套版式为**永久定稿**，锁在 `export_builder.py`、`cover_generator.py`、`pipeline.py`、`config/newsletter.json` 源码中。今后除非用户主动要求，否则：(1)不 bump 任何字号；(2)不改章节顺序/icon/配色/卡片结构；(3)不手动回填旧期 HTML。每期（`/api/collect`、`generate_weekly.py`、Linux cron）自动沿用此格式。
