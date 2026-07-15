# 部署到自托管 Linux 服务器

本文说明如何把「闪联AI周刊」网页系统部署到一台你自己的 Linux 服务器（Ubuntu / Debian / CentOS 均可）。
你已经在 VSCode 里用 Remote-SSH 连上了这台服务器，下面的命令都在**远程服务器的终端**里执行。

---

## 一、把代码放到服务器上

两种方式任选其一：

**方式 A — 通过 VSCode 远程直接同步（你已连上远程）**
VSCode 打开的就是远程上的项目目录，文件已经在服务器上了，跳过这步。
记下远程项目路径（终端里 `pwd` 看一下，假设是 `/opt/ai-weekly`）。

**方式 B — 从 GitHub 克隆**
```bash
sudo apt update && sudo apt install -y git python3 python3-venv   # Debian/Ubuntu
git clone <你的仓库地址> /opt/ai-weekly
cd /opt/ai-weekly
```

> ⚠️ `.env` 被 `.gitignore` 忽略，**不会**随 clone 下来。需要手动创建（见第三步）。

---

## 二、准备环境变量（关键！）

在项目根目录创建 `.env`（参照 `.env.example`）：

```bash
cp .env.example .env
nano .env          # 填入 ARK_API_KEY 等真实值
```

**必填**：`ARK_API_KEY`、`ARK_BASE_URL`（`https://ark.cn-beijing.volces.com/api/coding/v3`）、`ARK_MODEL`（`ark-code-latest`）。
**端点写错会 401**（之前在 Render 上踩过的坑）。

---

## 三、安装依赖并启动

### 快速启动（调试/临时）
```bash
bash deploy/start.sh
# 或后台常驻：
nohup bash deploy/start.sh > run.log 2>&1 &
```
启动后访问 `http://<服务器IP>:5000/` 即可看到网页。

### 用 systemd 守护（生产推荐）
```bash
# 把单元文件放到系统目录（按实际路径修改 User / WorkingDirectory / EnvironmentFile）
sudo cp deploy/ai-weekly.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-weekly
sudo systemctl status ai-weekly    # 确认 active (running)

# 查看日志
journalctl -u ai-weekly -f
```
单元文件里 `WorkingDirectory` 和 `EnvironmentFile` 指向你的真实路径；若不用 `.env` 注入，可改成逐条 `Environment=ARK_API_KEY=xxx`。

---

## 四、（可选）用 nginx 做反向代理 + 域名

gunicorn 只监听 `127.0.0.1:5000`，由 nginx 对外：

```nginx
server {
    listen 80;
    server_name weekly.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 静态图片走 /output 和 /issues，可加缓存
    location /output/ {
        alias /opt/ai-weekly/output/;
        expires 7d;
    }
}
```
启用后记得在云厂商安全组 / 防火墙开放 80/443 端口，并用 certbot 申请 HTTPS。

---

## 五、关于「周报数据从哪来」——两种模式

网页展示的是 `output/weekly-*/` 里的报告。数据来源有两种模式：

**模式 A：服务器只做展示，周报由 GitHub Actions 自动生成**
- `.github/workflows/weekly.yml` 已配置定时生成并 `git commit` 回仓库。
- 服务器要拿到新一期，需 `git pull`（可加 cron：`0 8 * * * cd /opt/ai-weekly && git pull`）。
- 优点：服务器无需 ARK Key，最省心。

**模式 B：服务器自己生成（网页点「新增本期资讯」）**
- 服务器需配好 `ARK_API_KEY` 等（第三步已完成）。
- 浏览器打开网页 → 点「新增本期资讯」，流水线在服务器本地跑，写进 `output/`。
- 注意：免费/低配机器跑 LLM 分析可能较慢，建议 gunicorn `-w` 调小。

> 两种可并存：GitHub Action 生成、服务器定时 pull；临时想加一期就在网页上点。

---

## 六、部署后自检

1. 打开 `http://<服务器IP>:5000/`，应显示最新一期周报且图片正常。
2. 点「新增本期资讯」测试生成（模式 B 需 ARK Key 配对；之前 Render 上遇到的
   「任务已失效」已通过 `output/tasks.json` 持久化修复，重启服务不丢任务）。
3. 生成后点「导出完整周报」会下载自包含 ZIP（md + html + images）。

---

## 七、排错

| 现象 | 原因 / 处理 |
|---|---|
| 401 API key format is incorrect | `ARK_BASE_URL` 不是 `/api/coding/v3`，或 `ARK_API_KEY` 值错/过期。核对 `.env` |
| 网页能开但图片裂图 | 检查 nginx 的 `/output/` alias 路径是否指向项目 `output/`；或导出 ZIP 解压看 |
| 重启服务器后任务查不到 | 已修复（tasks.json 持久化）；确认 `output/` 目录可写 |
| `ModuleNotFoundError: gunicorn` | `pip install -r requirements.txt` 没装成功，确认在 venv 内执行 |
| 端口被占用 | 改 `deploy/start.sh` 或单元文件里的 `5000` 为其他端口 |
