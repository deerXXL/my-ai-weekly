#!/usr/bin/env bash
# 闪联AI周刊 — Linux 启动脚本
# 用法：
#   bash deploy/start.sh            # 前台运行（调试用）
#   nohup bash deploy/start.sh &    # 后台运行
set -e
cd "$(dirname "$0")/.."   # 切到项目根目录

PYTHON=${PYTHON:-python3}

# 1. 虚拟环境
if [ ! -d venv ]; then
    echo "[setup] 创建虚拟环境 venv/"
    "$PYTHON" -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

# 2. 安装依赖
echo "[setup] 安装依赖..."
pip install -r requirements.txt -q

# 3. 检查 .env
if [ ! -f .env ]; then
    echo "[warn] 未找到 .env，请先执行: cp .env.example .env 并填入密钥"
fi

# 4. 启动 gunicorn
# 前置 nginx 时建议改为 -b 127.0.0.1:5000；直接暴露则用 -b 0.0.0.0:5000
echo "[run] 启动 gunicorn on 0.0.0.0:5000"
exec gunicorn -w 2 -b 0.0.0.0:5000 web_server:app
