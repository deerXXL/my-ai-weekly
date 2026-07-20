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

# —— 推送到 GitHub，触发 Render 自动重新部署网页（自动更新核心）——
# 前提：本机已配置 SSH 公钥到 GitHub（见下方部署说明），且 remote 为 SSH 地址。
# 仅在新一期已生成时执行（上方已通过 14 天节流判断），避免空推。
cd /home/jinqi/my-ai-weekly
# cron 非交互环境：跳过首次 SSH host 确认，避免卡死
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
git config user.email "bot@ai-weekly.local"
git config user.name "ai-weekly-bot"
git add output/ latest.json .latest 2>/dev/null
git commit -m "Auto update weekly $(date +%Y-%m-%d)" || echo "（无新内容，跳过 commit）"
# 推送到两个 remote（Render 只连其中一个，两个都推以覆盖）；用 ; 保证都尝试
git push origin main 2>&1; git push Laurtiv27 main 2>&1
echo "$(date) 推送完成，等待 Render 自动部署"
