"""下载配图到本期周刊目录 images/ 子文件夹。"""
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.crawlers._http_utils import DEFAULT_HEADERS


def _guess_extension(url: str, content_type: str) -> str:
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if path.endswith(ext):
            return ext
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "gif" in content_type:
        return ".gif"
    return ".jpg"


def download_image(
    remote_url: str,
    issue_dir: Path,
    index: int,
    *,
    referer: str = "",
) -> str:
    """
    下载到 {issue_dir}/images/img-{index}.ext
    返回相对本期目录的路径，如 images/img-0.jpg
    """
    if not remote_url or not remote_url.startswith("http"):
        return ""

    dest_dir = issue_dir / "images"
    dest_dir.mkdir(parents=True, exist_ok=True)

    headers = dict(DEFAULT_HEADERS)
    if referer:
        headers["Referer"] = referer

    try:
        response = requests.get(remote_url, headers=headers, timeout=20, stream=True)
        response.raise_for_status()
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "image" not in content_type and not content_type.startswith(
            "application/octet"
        ):
            print(f"  [image-save] 非图片类型 {content_type[:30]}")
            return ""

        ext = _guess_extension(remote_url, content_type)
        filename = f"img-{index}{ext}"
        dest_path = dest_dir / filename
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if dest_path.stat().st_size < 512:
            dest_path.unlink(missing_ok=True)
            print("  [image-save] 文件过小，跳过")
            return ""

        rel = f"images/{filename}"
        print(f"  [image-save] {issue_dir.name}/{rel}")
        return rel
    except Exception as exc:
        print(f"  [image-save] 下载失败 — {exc}")
        return ""
