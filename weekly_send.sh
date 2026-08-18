#!/bin/bash
# 闪联AI周刊 — 双周自动发送（混合方案）
# 分工：
#   - GitHub Action：负责「生成 + 推送 GitHub + 触发网页更新」（偶数 ISO 周周一 09:00 北京时间）；
#   - 本脚本：只负责「拉取最新刊 + 发邮件」（建议周一 12:00 北京时间，晚于 Action 的生成）。
#
# 发信门槛（防重发 + 防发旧刊），优先级从高到低：
#   1) ISSUE_DATE 为空                        → 报错退出；
#   2) ISSUE_DATE == 上次已发日期(.last_send) → 跳过（本期已发过，防重复发送）；
#   3) ISSUE_DATE 距今天 > 3 天               → 跳过（最新期太旧，疑似旧数据 / 奇数周未生成，不发旧刊）；
#      阈值取 3 天：双周节奏下两次发送间隔约 14 天，中间奇数周的最新期必为 7 天前，
#      故 >3 即可拦住奇数周误发；同时允许「周一之后的 1~3 天内手动补发」。
#   4) 否则 → 发送，并把 ISSUE_DATE 写入 .last_send。
#
# 发送环节复用 send_md_email.py 的轮流单发逻辑（A→B→C 循环，进度存 scripts/.last_receiver）。
cd /home/jinqi/my-ai-weekly

PROJECT_DIR=/home/jinqi/my-ai-weekly
LAST_SEND_FILE="$PROJECT_DIR/scripts/.last_send"

# —— 自包含清理（每周一执行，仅清理本机磁盘，不影响 GitHub）——
"$PROJECT_DIR/venv/bin/python" -c \
  "from app.services.retention import cleanup_old_issues; import json; print('cleanup:', json.dumps(cleanup_old_issues(), ensure_ascii=False))"

# —— 拉取 GitHub Action 生成并推送的最新刊 ——
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
git config user.email "bot@ai-weekly.local"
git config user.name "ai-weekly-bot"
git pull origin main 2>&1

# —— 解析最新一期日期 ——
LATEST=$(ls -d output/weekly-* 2>/dev/null | sort | tail -1 | xargs basename 2>/dev/null)
ISSUE_DATE=${LATEST#weekly-}
TODAY=$(date +%Y-%m-%d)

if [ -z "$ISSUE_DATE" ]; then
  echo "$(date) ⚠️ 未找到任何期目录，跳过发信"
  exit 1
fi

# —— 门槛1：本期是否已发过（防重发）——
LAST_SEND=""
if [ -f "$LAST_SEND_FILE" ]; then
  LAST_SEND=$(cat "$LAST_SEND_FILE" | tr -d '[:space:]')
fi
if [ -n "$LAST_SEND" ] && [ "$ISSUE_DATE" = "$LAST_SEND" ]; then
  echo "$(date) 本期 $ISSUE_DATE 已发送过（.last_send=$LAST_SEND），跳过发信"
  exit 0
fi

# —— 门槛2：最新期是否过旧（防发旧刊 / 奇数周误发）——
DAYS_OLD=$(( ( $(date -d "$TODAY" +%s) - $(date -d "$ISSUE_DATE" +%s) ) / 86400 ))
if [ "$DAYS_OLD" -gt 3 ]; then
  echo "$(date) 最新期 $ISSUE_DATE 距今天已 $DAYS_OLD 天（>3），疑似旧数据或奇数周未生成，跳过发信"
  exit 0
fi

# —— 发送（轮流单发，复用 send_md_email.py）——
if "$PROJECT_DIR/venv/bin/python" send_md_email.py; then
  echo "$ISSUE_DATE" > "$LAST_SEND_FILE"
  echo "$(date) ✅ 邮件已发送（本期 $ISSUE_DATE），已记录 .last_send=$ISSUE_DATE"
else
  echo "$(date) ⚠️ 发信失败（SMTP/网络异常），下周一将自动重试"
  exit 1
fi
