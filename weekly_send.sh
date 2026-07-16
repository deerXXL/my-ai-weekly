#!/bin/bash
# 闪联AI周刊 — 双周自动发送（方案 A）
# 由 cron 每周一 09:00 触发；脚本内部判断距上次发送是否满 14 天，未满则跳过。
# 发送环节复用 send_md_email.py 的轮流单发逻辑。
cd /home/jinqi/my-ai-weekly
STATE=scripts/.last_send
NOW=$(date +%s)

if [ -f "$STATE" ]; then
  LAST=$(cat "$STATE")
  DIFF=$(( (NOW - LAST) / 86400 ))
  if [ "$DIFF" -lt 14 ]; then
    echo "$(date) 距上次发送 ${DIFF} 天，未到双周，跳过"
    exit 0
  fi
fi

/home/jinqi/my-ai-weekly/venv/bin/python generate_weekly.py --days 14
/home/jinqi/my-ai-weekly/venv/bin/python send_md_email.py
echo "$NOW" > "$STATE"
