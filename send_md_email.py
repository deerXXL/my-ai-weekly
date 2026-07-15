"""
以 HTML 邮件正文形式发送 AI 周刊。
使用 CID（Content-ID）内联附件嵌入图片，兼容所有主流邮箱客户端。
"""

import os
import re
import smtplib
import base64
import mimetypes
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
import sys
from dotenv import load_dotenv

from bs4 import BeautifulSoup

# ─── 配置 ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
load_dotenv()  # 读取项目根目录 .env 中的环境变量（如 QQ_MAIL_PASSWORD、WEEKLY_SITE_URL）
OUTPUT_DIR = BASE_DIR / "output"

SENDER = "3540737632@qq.com"
SUBJECT = "闪联AI周刊"

# 收件人：在 .env 中用 QQ_MAIL_RECEIVERS 配置，多个邮箱用英文逗号分隔
#   例：QQ_MAIL_RECEIVERS=aaa@qq.com,bbb@163.com
RECEIVER_RAW = os.getenv("QQ_MAIL_RECEIVERS", "lijq@igrslab.com")
RECEIVERS = [r.strip() for r in RECEIVER_RAW.split(",") if r.strip()]
if not RECEIVERS:
    raise SystemExit(
        "[ERROR] 未配置收件人。请在项目根目录 .env 中添加一行：\n"
        "        QQ_MAIL_RECEIVERS=邮箱1,邮箱2"
    )

# QQ 邮箱授权码：在 .env 中配置 QQ_MAIL_PASSWORD（.env 已被 .gitignore 忽略，不会提交）
PASSWORD = os.getenv("QQ_MAIL_PASSWORD", "")
if not PASSWORD:
    raise SystemExit(
        "[ERROR] 未配置 QQ 邮箱授权码。请在项目根目录 .env 中添加一行：\n"
        "        QQ_MAIL_PASSWORD=你的QQ邮箱授权码"
    )

# 周报网页地址（收信人可点开在线查看完整页面）
SITE_URL = os.getenv("WEEKLY_SITE_URL", "https://ai-weekly-report.onrender.com/")

# 周刊目录：默认发送最新一期；可在命令行指定日期：
#   python send_md_email.py              # 发送最新的 output/weekly-*
#   python send_md_email.py 2026-07-15   # 发送指定日期那一期
def _resolve_weekly_dir(date_str=None) -> Path:
    if date_str:
        d = OUTPUT_DIR / f"weekly-{date_str}"
        if not d.is_dir():
            raise SystemExit(f"[ERROR] 指定目录不存在: {d}")
        return d
    dirs = sorted([p for p in OUTPUT_DIR.glob("weekly-*") if p.is_dir()])
    if not dirs:
        raise SystemExit("[ERROR] 未找到任何 output/weekly-* 目录，请先生成周报")
    return dirs[-1]


# ─── 工具函数 ──────────────────────────────────────────────────────────
def _mime_type_for(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def _src_to_filename(src: str) -> str:
    """从 src 属性中提取图片文件名。"""
    src = src.lstrip("/")
    return Path(src).name


def prepare_html_and_images(html: str, images_dir: Path) -> tuple[str, list[tuple[str, Path]]]:
    """解析 HTML，收集需要嵌入的图片，并将 src 替换为 CID 引用。

    返回:
        (替换后的 HTML, [(cid_id, 图片文件路径), ...])
    """
    soup = BeautifulSoup(html, "html.parser")
    attachments: list[tuple[str, Path]] = []
    cid_counter = 0

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src or src.startswith(("http://", "https://", "data:")):
            continue

        filename = _src_to_filename(src)
        full_path = images_dir / filename
        if not full_path.exists():
            print(f"[WARN] 图片不存在，跳过: {full_path}")
            continue

        cid = f"img{cid_counter}"
        cid_counter += 1
        img["src"] = f"cid:{cid}"
        attachments.append((cid, full_path))

    return str(soup), attachments


# ─── 主流程 ────────────────────────────────────────────────────────────
def main():
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    weekly_dir = _resolve_weekly_dir(date_arg)
    print(f"[INFO] 发送周刊目录: {weekly_dir}")

    html_path = weekly_dir / "newsletter.html"
    images_dir = weekly_dir / "images"
    md_path = weekly_dir / "newsletter.md"

    # 读取 HTML
    if not html_path.exists():
        print(f"[ERROR] HTML 文件不存在: {html_path}")
        return

    html_content = html_path.read_text(encoding="utf-8")

    # 替换图片 src 为 CID 引用，收集图片列表
    html_content, image_list = prepare_html_and_images(html_content, images_dir)
    print(f"[INFO] 共 {len(image_list)} 张图片需要内嵌")

    # 在邮件正文末尾追加“在线查看”链接，让收信人能打开网页完整页面
    footer = (
        '<hr style="margin-top:24px;border:none;border-top:1px solid #eee">'
        f'<p style="color:#666;font-size:13px">'
        f'📄 <a href="{SITE_URL}" style="color:#2b6cb0">'
        f'在网页查看完整周报（含交互与最新内容）</a></p>'
    )
    html_content = html_content + footer

    # 构建 MIME 邮件（mixed 外层：HTML 正文 + 内嵌图 + md 附件）
    msg = MIMEMultipart("mixed")
    msg["Subject"] = SUBJECT
    msg["From"] = SENDER
    msg["To"] = ", ".join(RECEIVERS)
    msg["Content-Transfer-Encoding"] = "8bit"

    # 相关部分：HTML 正文 + 内嵌图片
    related = MIMEMultipart("related")
    html_part = MIMEText(html_content, "html", "utf-8")
    related.attach(html_part)
    for cid, img_path in image_list:
        mime = _mime_type_for(str(img_path))
        with open(img_path, "rb") as f:
            img_data = f.read()
        img_part = MIMEImage(img_data, _subtype=mime.split("/")[1])
        img_part.add_header("Content-ID", f"<{cid}>")
        img_part.add_header("Content-Disposition", "inline", filename=img_path.name)
        related.attach(img_part)
    msg.attach(related)

    # md 文件作为附件
    if md_path.exists():
        md_part = MIMEApplication(md_path.read_bytes())
        md_part.add_header("Content-Disposition", "attachment", filename="newsletter.md")
        msg.attach(md_part)
        print(f"[INFO] 已附上 md 文件: {md_path.name}")
    else:
        print(f"[WARN] 未找到 md 文件，跳过附件: {md_path}")

    # 通过 QQ 邮箱 SMTP 群发给所有收件人
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, RECEIVERS, msg.as_string())

    print(f"[INFO] 邮件已发送至 {len(RECEIVERS)} 个收件人: {', '.join(RECEIVERS)}")


if __name__ == "__main__":
    main()
