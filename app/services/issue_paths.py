"""周刊输出目录路径管理。"""
from pathlib import Path

from config import OUTPUT_DIR

LATEST_POINTER = OUTPUT_DIR / ".latest"
NEWSLETTER_JSON = "newsletter.json"
NEWSLETTER_MD = "newsletter.md"
NEWSLETTER_HTML = "newsletter.html"


def issue_name(date_tag: str) -> str:
    return f"weekly-{date_tag}"


def issue_dir(date_tag: str) -> Path:
    return OUTPUT_DIR / issue_name(date_tag)


def ensure_issue_dir(date_tag: str) -> Path:
    path = issue_dir(date_tag)
    path.mkdir(parents=True, exist_ok=True)
    (path / "images").mkdir(exist_ok=True)
    return path


def set_latest_issue(date_tag: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    LATEST_POINTER.write_text(issue_name(date_tag) + "\n", encoding="utf-8")


def find_latest_issue_dir() -> Path | None:
    if LATEST_POINTER.exists():
        name = LATEST_POINTER.read_text(encoding="utf-8").strip()
        candidate = OUTPUT_DIR / name
        if candidate.is_dir():
            return candidate

    dirs = sorted(
        (p for p in OUTPUT_DIR.glob("weekly-*") if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    if dirs:
        return dirs[0]

    return None


def find_latest_newsletter_json() -> Path | None:
    issue = find_latest_issue_dir()
    if issue:
        path = issue / NEWSLETTER_JSON
        if path.exists():
            return path
    return None


def find_latest_newsletter_html() -> Path | None:
    issue = find_latest_issue_dir()
    if issue:
        path = issue / NEWSLETTER_HTML
        if path.exists():
            return path
    return None


def iter_issue_dirs() -> list[Path]:
    dirs = [p for p in OUTPUT_DIR.glob("weekly-*") if p.is_dir()]
    return sorted(dirs, key=lambda p: p.name, reverse=True)


def newsletter_json_in(issue: Path) -> Path:
    return issue / NEWSLETTER_JSON
