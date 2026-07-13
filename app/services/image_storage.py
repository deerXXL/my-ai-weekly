"""下载配图到本期周刊目录 images/ 子文件夹。"""
from pathlib import Path
from urllib.parse import urlparse

from app.crawlers._http_utils import get_http_session

MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 超过 2MB 的图片跳过（避免巨型 GIF 拖慢）
DOWNLOAD_TIMEOUT = (5, 15)  # (connect, read) 秒


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

    headers = {}
    if referer:
        headers["Referer"] = referer

    session = get_http_session()
    try:
        response = session.get(
            remote_url,
            headers=headers,
            timeout=DOWNLOAD_TIMEOUT,
            stream=True,
        )
        response.raise_for_status()
        content_type = (response.headers.get("Content-Type") or "").lower()
        content_length = int(response.headers.get("Content-Length") or 0)
        if content_length > MAX_IMAGE_BYTES:
            print(f"  [image-save] 文件过大 ({content_length // 1024}KB)，跳过")
            return ""
        if "image" not in content_type and not content_type.startswith(
            "application/octet"
        ):
            print(f"  [image-save] 非图片类型 {content_type[:30]}")
            return ""

        ext = _guess_extension(remote_url, content_type)
        filename = f"img-{index}{ext}"
        dest_path = dest_dir / filename
        written = 0
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                written += len(chunk)
                if written > MAX_IMAGE_BYTES:
                    print(f"  [image-save] 下载超过 {MAX_IMAGE_BYTES // 1024 // 1024}MB，中止")
                    dest_path.unlink(missing_ok=True)
                    return ""
                f.write(chunk)

        if dest_path.stat().st_size < 512:
            dest_path.unlink(missing_ok=True)
            print("  [image-save] 文件过小，跳过")
            return ""

        rel = f"images/{filename}"
        kb = dest_path.stat().st_size // 1024
        print(f"  [image-save] {issue_dir.name}/{rel} ({kb}KB)")
        return rel
    except Exception as exc:
        print(f"  [image-save] 下载失败 — {exc}")
        return ""
