#!/bin/bash
# 闪联AI周刊 — 双周自动发送（混合方案）
# 分工：
#   - GitHub Action：负责「生成 + 推送 GitHub + 触发网页更新」（偶数 ISO 周周一 09:00 北京时间）；
#   - 本脚本：只负责「拉取最新刊 + 发邮件」（建议周一 12:00 北京时间，晚于 Action 的生成）。
# 流程：
#   - 清理：每次触发都执行，保留最近 N 个「不重复周期」的期（仅清理本机磁盘，不影响 GitHub）；
#   - 拉取：git pull 获取 Action 生成并推送的本周新刊；
#   - 发送：仅当 output 中最新一期日期 == 今天（周一）时才发，
#           防止奇数周 / Action 未生成时把上一期旧刊重发出去；
#   - 发送环节复用 send_md_email.py 的轮流单发逻辑（A→B→C 循环）。
cd /home/jinqi/my-ai-weekly

# —— 自包含清理（每周一执行，仅清理本机磁盘）——
/home/jinqi/my-ai-weekly/venv/bin/python -c \
  "from app.services.retention import cleanup_old_issues; import json; print('cleanup:', json.dumps(cleanup_old_issues(), ensure_ascii=False))"

# —— 拉取 GitHub Action 生成并推送的最新刊 ——
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
git config user.email "bot@ai-weekly.local"
git config user.name "ai-weekly-bot"
git pull origin main 2>&1

# —— 判断本周是否有新刊（偶数周 Action 才会生成）——
LATEST=$(ls -d output/weekly-* 2>/dev/null | sort | tail -1 | xargs basename 2>/dev/null)
ISSUE_DATE=${LATEST#weekly-}
TODAY=$(date +%Y-%m-%d)

if [ -z "$ISSUE_DATE" ]; then
  echo "$(date) ⚠️ 未找到任何期目录，跳过发信"
  exit 1
fi

if [ "$ISSUE_DATE" != "$TODAY" ]; then
  echo "$(date) 本周无新刊（奇数周或 Action 未生成），最新期为 $ISSUE_DATE，跳过发信"
  exit 0
fi

# —— 发送（轮流单发，复用 send_md_email.py）——
if /home/jinqi/my-ai-weekly/venv/bin/python send_md_email.py; then
  echo "$(date) ✅ 邮件已发送（本期 $ISSUE_DATE）"
else
  echo "$(date) ⚠️ 发信失败（SMTP/网络异常），下周一将自动重试"
  exit 1
fi
