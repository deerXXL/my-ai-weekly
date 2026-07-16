#!/bin/bash
# 闪联AI周刊 — 双周自动发送 + 自包含清理（方案 A，完全独立于网页）
# 由 cron 每周一 09:00 触发（建议从「下周一」启用）；
#   - 清理：每次触发都执行，保留最近 N 个「不重复周期」的期，删除更旧目录
#           （直接调用 app.services.retention，不依赖网页 /api/collect，单线运行）；
#   - 发送：脚本内部判断距上次发送是否满 14 天，未满则跳过发送；
#   - 发送环节复用 send_md_email.py 的轮流单发逻辑。
cd /home/jinqi/my-ai-weekly
STATE=scripts/.last_send
NOW=$(date +%s)

# —— 自包含清理（每周一执行，不依赖网页）——
# 保留期数取 config.REPORT_RETAIN_ISSUES（默认 5，可用环境变量 AI_WEEKLY_RETAIN_ISSUES 覆盖）。
/home/jinqi/my-ai-weekly/venv/bin/python -c \
  "from app.services.retention import cleanup_old_issues; import json; print('cleanup:', json.dumps(cleanup_old_issues(), ensure_ascii=False))"

if [ -f "$STATE" ]; then
  LAST=$(cat "$STATE")
  DIFF=$(( (NOW - LAST) / 86400 ))
  if [ "$DIFF" -lt 14 ]; then
    echo "$(date) 距上次发送 ${DIFF} 天，未到双周，跳过发送（清理已执行）"
    exit 0
  fi
fi

/home/jinqi/my-ai-weekly/venv/bin/python generate_weekly.py --days 14
/home/jinqi/my-ai-weekly/venv/bin/python send_md_email.py
echo "$NOW" > "$STATE"
