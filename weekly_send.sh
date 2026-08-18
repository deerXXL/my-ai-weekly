#!/bin/bash
# 闪联AI周刊 — Linux 全自动（不依赖 GitHub）
# 单机完成：清理旧刊 → 仅偶数 ISO 周生成新刊 → 门槛检查 → 发邮件。
# 由 crontab 触发（建议 每周一 09:00 北京时间 = UTC 01:00）。
#
# 双周节流（与原 GitHub Action 行为一致）：
#   用 TZ='Asia/Shanghai' 取 ISO 周号（与 cron 北京时间一致），
#   偶数周执行生成；奇数周仅清理不发信（保留过往双周节奏）。
#
# 发信门槛（防重发 + 防发旧刊），优先级从高到低：
#   1) 奇数 ISO 周                  → 直接跳过；
#   2) 生成失败                     → 报错退出；
#   3) 未找到任何期目录             → 报错退出；
#   4) ISSUE_DATE == .last_send     → 跳过（防同日期重复发）；
#   5) ISSUE_DATE 距今天 > 3 天     → 跳过（最新期过旧，疑似数据异常，不发旧刊）；
#   阈值取 3 天：双周节奏下两次发送间隔约 14 天，奇数周的最新期必为 7 天前，
#   故 >3 即可拦住；同时允许「周一之后的 1~3 天内手动补发」。
#   6) 否则 → 调 send_md_email.py 发送，并把 ISSUE_DATE 写入 .last_send。
#
# 发送环节复用 send_md_email.py 的轮流单发逻辑（A→B→C 循环，进度存 scripts/.last_receiver）。

set -u

PROJECT_DIR=/home/jinqi/my-ai-weekly
cd "$PROJECT_DIR" || { echo "无法进入项目目录: $PROJECT_DIR"; exit 1; }

LAST_SEND_FILE="$PROJECT_DIR/scripts/.last_send"
LOG_FILE="$PROJECT_DIR/scripts/weekly_send.log"

mkdir -p "$(dirname "$LOG_FILE")"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') Linux 周刊双周任务开始 =====" >> "$LOG_FILE"

# —— 1. 清理过期旧刊（仅本地磁盘，不影响任何远程）——
echo "[$(date '+%H:%M:%S')] 清理过期旧刊..." >> "$LOG_FILE"
"$PROJECT_DIR/venv/bin/python" -c \
  "from app.services.retention import cleanup_old_issues; import json; print('cleanup:', json.dumps(cleanup_old_issues(), ensure_ascii=False))" \
  >> "$LOG_FILE" 2>&1

# —— 2. 仅在偶数 ISO 周生成（双周节流）——
WEEK=$(TZ='Asia/Shanghai' date +%V)
if [ $((10#$WEEK % 2)) -ne 0 ]; then
  echo "[$(date '+%H:%M:%S')] 本周为 ISO 第 $WEEK 周（奇数周），跳过生成。" >> "$LOG_FILE"
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') 任务结束（奇数周） =====" >> "$LOG_FILE"
  exit 0
fi
echo "[$(date '+%H:%M:%S')] 本周为 ISO 第 $WEEK 周（偶数周），开始生成..." >> "$LOG_FILE"

# —— 3. 生成新刊（本地独立完成，无 GitHub 依赖）——
"$PROJECT_DIR/venv/bin/python" generate_weekly.py --days 14 >> "$LOG_FILE" 2>&1
GEN_RC=$?
if [ $GEN_RC -ne 0 ]; then
  echo "[$(date '+%H:%M:%S')] ❌ 生成失败 (exit=$GEN_RC)，跳过发信" >> "$LOG_FILE"
  exit 1
fi

# —— 4. 解析最新一期日期 ——
LATEST=$(ls -d "$PROJECT_DIR"/output/weekly-* 2>/dev/null | sort | tail -1 | xargs basename 2>/dev/null)
ISSUE_DATE=${LATEST#weekly-}
TODAY=$(date +%Y-%m-%d)

if [ -z "$ISSUE_DATE" ]; then
  echo "[$(date '+%H:%M:%S')] ⚠️ 未找到任何期目录，跳过发信" >> "$LOG_FILE"
  exit 1
fi

# —— 5. 门槛1：本期是否已发过（防重发）——
LAST_SEND=""
if [ -f "$LAST_SEND_FILE" ]; then
  LAST_SEND=$(cat "$LAST_SEND_FILE" | tr -d '[:space:]')
fi
if [ -n "$LAST_SEND" ] && [ "$ISSUE_DATE" = "$LAST_SEND" ]; then
  echo "[$(date '+%H:%M:%S')] 本期 $ISSUE_DATE 已发送过（.last_send=$LAST_SEND），跳过发信" >> "$LOG_FILE"
  exit 0
fi

# —— 6. 门槛2：最新期是否过旧（防发旧刊）——
DAYS_OLD=$(( ( $(date -d "$TODAY" +%s) - $(date -d "$ISSUE_DATE" +%s) ) / 86400 ))
if [ "$DAYS_OLD" -gt 3 ]; then
  echo "[$(date '+%H:%M:%S')] 最新期 $ISSUE_DATE 距今天已 $DAYS_OLD 天（>3），疑似数据异常，跳过发信" >> "$LOG_FILE"
  exit 0
fi

# —— 7. 发送邮件（轮流单发，复用 send_md_email.py）——
echo "[$(date '+%H:%M:%S')] 发送邮件（本期 $ISSUE_DATE）..." >> "$LOG_FILE"
if "$PROJECT_DIR/venv/bin/python" send_md_email.py >> "$LOG_FILE" 2>&1; then
  echo "$ISSUE_DATE" > "$LAST_SEND_FILE"
  echo "[$(date '+%H:%M:%S')] ✅ 邮件已发送，已记录 .last_send=$ISSUE_DATE" >> "$LOG_FILE"
else
  echo "[$(date '+%H:%M:%S')] ⚠️ 发信失败（SMTP/网络异常），下周一自动重试" >> "$LOG_FILE"
  exit 1
fi

echo "===== $(date '+%Y-%m-%d %H:%M:%S') Linux 周刊双周任务结束 =====" >> "$LOG_FILE"