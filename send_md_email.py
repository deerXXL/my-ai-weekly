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

from bs4 import BeautifulSoup

# ─── 配置 ────────────────────────────────────────────────────────────
os.chdir(os.path.dirname(os.path.abspath(__file__)))

SENDER = "3540737632@qq.com"
PASSWORD = "gsdpvpretuedchcf"
RECEIVER = "3664250038@qq.com"
SUBJECT = "闪联AI周刊"

# HTML 文件路径
HTML_FILE = "output/weekly-2026-07-13/newsletter.html"
IMAGES_DIR = Path("output/weekly-2026-07-13/images")


# ─── 工具函数 ──────────────────────────────────────────────────────────
def _mime_type_for(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def _src_to_filename(src: str) -> str:
    """从 src 属性中提取图片文件名。"""
    src = src.lstrip("/")
    return Path(src).name


def prepare_html_and_images(html: str) -> tuple[str, list[tuple[str, Path]]]:
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
        full_path = IMAGES_DIR / filename
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
    # 读取 HTML
    html_path = Path(HTML_FILE)
    if not html_path.exists():
        print(f"[ERROR] HTML 文件不存在: {html_path}")
        return

    html_content = html_path.read_text(encoding="utf-8")

    # 替换图片 src 为 CID 引用，收集图片列表
    html_content, image_list = prepare_html_and_images(html_content)
    print(f"[INFO] 共 {len(image_list)} 张图片需要内嵌")

    # 构建 MIME 邮件
    msg = MIMEMultipart("related")
    msg["Subject"] = SUBJECT
    msg["From"] = SENDER
    msg["To"] = RECEIVER
    msg["Content-Transfer-Encoding"] = "8bit"

    # HTML 正文
    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(html_part)

    # 内嵌图片（CID 附件）
    for cid, img_path in image_list:
        mime = _mime_type_for(str(img_path))
        with open(img_path, "rb") as f:
            img_data = f.read()
        img_part = MIMEImage(img_data, _subtype=mime.split("/")[1])
        img_part.add_header("Content-ID", f"<{cid}>")
        img_part.add_header("Content-Disposition", "inline", filename=img_path.name)
        msg.attach(img_part)

    # 通过 QQ 邮箱 SMTP 发送
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, RECEIVER, msg.as_string())

    print(f"[INFO] 邮件已发送至 {RECEIVER}")


if __name__ == "__main__":
    main()
