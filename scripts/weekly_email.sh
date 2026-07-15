#!/bin/bash
# 闪联AI周刊 - 每两周自动发送最新一期到 .env 中配置的邮箱
# 由 crontab 调用（每两周周一 09:00），也可手动测试：bash scripts/weekly_email.sh
#
# 行为：
#   1. 找到 output/ 下最新一期 weekly-* 目录
#   2. 若这一期已经发送过（记录在上次发送状态文件），则跳过，避免重复群发
#   3. 否则调用 send_md_email.py 群发邮件，并记录本期已发送

set -u

# 自动定位项目根目录（本脚本应位于 <项目>/scripts/ 下）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

LOG_FILE="$PROJECT_DIR/weekly_email.log"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"
LAST_SENT_FILE="$SCRIPT_DIR/.last_sent_issue"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 开始双周邮件任务 =====" >> "$LOG_FILE"

if [ ! -f "$VENV_ACTIVATE" ]; then
  echo "[ERROR] 虚拟环境不存在: $VENV_ACTIVATE" >> "$LOG_FILE"
  exit 1
fi

cd "$PROJECT_DIR" || { echo "[ERROR] 无法进入项目目录: $PROJECT_DIR" >> "$LOG_FILE"; exit 1; }
# shellcheck disable=SC1091
source "$VENV_ACTIVATE"

# 同步 GitHub Actions 自动生成的最新报告（工作流把 output/ 提交回仓库，
# 但服务器本地 output/ 是独立副本，必须先拉取才能拿到 GitHub 生成的那一期）
echo "[$(date '+%H:%M:%S')] 同步 GitHub 最新报告..." >> "$LOG_FILE"
git -C "$PROJECT_DIR" fetch origin main >> "$LOG_FILE" 2>&1 \
  || echo "[WARN] git fetch 失败，将使用服务器本地已有报告" >> "$LOG_FILE"
git -C "$PROJECT_DIR" checkout origin/main -- output >> "$LOG_FILE" 2>&1 \
  || echo "[WARN] 同步 output 失败，将使用服务器本地已有报告" >> "$LOG_FILE"

# 找到最新一期（与 send_md_email.py 的选取逻辑一致：按目录名排序取最后一个）
LATEST_DIR=$(ls -1d "$PROJECT_DIR"/output/weekly-* 2>/dev/null | sort | tail -1)
if [ -z "$LATEST_DIR" ]; then
  echo "[ERROR] 未找到任何 output/weekly-* 目录，请先生成周报" >> "$LOG_FILE"
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') 结束（无报告） =====" >> "$LOG_FILE"
  exit 1
fi
LATEST_NAME="$(basename "$LATEST_DIR")"

# 跳过已发送过的最新一期，避免重复群发同一封邮件
if [ -f "$LAST_SENT_FILE" ] && [ "$(cat "$LAST_SENT_FILE")" = "$LATEST_NAME" ]; then
  echo "[$(date '+%H:%M:%S')] 最新一期 ($LATEST_NAME) 已发送过，本次跳过" >> "$LOG_FILE"
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') 结束（无新报告） =====" >> "$LOG_FILE"
  exit 0
fi

echo "[$(date '+%H:%M:%S')] 发送最新一期: $LATEST_NAME" >> "$LOG_FILE"
python send_md_email.py >> "$LOG_FILE" 2>&1
RC=$?

if [ $RC -eq 0 ]; then
  echo "$LATEST_NAME" > "$LAST_SENT_FILE"
  echo "[$(date '+%H:%M:%S')] ✅ 邮件发送成功" >> "$LOG_FILE"
else
  echo "[$(date '+%H:%M:%S')] ❌ 邮件发送失败 (exit=$RC)" >> "$LOG_FILE"
fi

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 双周邮件任务结束 =====" >> "$LOG_FILE"
