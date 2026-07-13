"""从已有 newsletter.json 生成封面并刷新 md/html。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: F401
from app.models.daily_report import WeeklyNewsletter
from app.services.cover_generator import generate_cover
from app.services.export_builder import build_export_html, build_export_markdown
from app.services.issue_paths import NEWSLETTER_HTML, NEWSLETTER_JSON, NEWSLETTER_MD


def main() -> None:
    issue_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if issue_dir is None:
        from app.services.issue_paths import find_latest_newsletter_json

        json_path = find_latest_newsletter_json()
        if not json_path:
            raise SystemExit("未找到 newsletter.json")
        issue_dir = json_path.parent
    else:
        issue_dir = Path(issue_dir)
        json_path = issue_dir / NEWSLETTER_JSON

    with open(json_path, encoding="utf-8") as f:
        newsletter = WeeklyNewsletter.from_dict(json.load(f))

    cover = generate_cover(newsletter, issue_dir)
    if cover:
        newsletter.overview.cover_image = cover

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(newsletter.to_dict(), f, ensure_ascii=False, indent=2)

    (issue_dir / NEWSLETTER_MD).write_text(
        build_export_markdown(newsletter), encoding="utf-8"
    )
    (issue_dir / NEWSLETTER_HTML).write_text(
        build_export_html(newsletter), encoding="utf-8"
    )
    print(f"封面已写入 {issue_dir / 'images' / 'cover.png'}")


if __name__ == "__main__":
    main()
