import json
from pathlib import Path

from app.models.daily_report import WeeklyNewsletter
from app.services.export_builder import build_export_html, build_export_markdown
from app.services.issue_paths import (
    NEWSLETTER_HTML,
    NEWSLETTER_JSON,
    NEWSLETTER_MD,
    ensure_issue_dir,
    set_latest_issue,
)


def _target_dir(newsletter: WeeklyNewsletter) -> Path:
    date_tag = newsletter.date or newsletter.generated_at[:10]
    return ensure_issue_dir(date_tag)


def write_html(newsletter: WeeklyNewsletter) -> Path:
    folder = _target_dir(newsletter)
    path = folder / NEWSLETTER_HTML
    path.write_text(build_export_html(newsletter), encoding="utf-8")
    set_latest_issue(newsletter.date or newsletter.generated_at[:10])
    print(f"HTML generated: {path}")
    return path


def write_markdown(newsletter: WeeklyNewsletter) -> Path:
    folder = _target_dir(newsletter)
    path = folder / NEWSLETTER_MD
    path.write_text(build_export_markdown(newsletter), encoding="utf-8")
    print(f"Markdown generated: {path}")
    return path


def write_json(newsletter: WeeklyNewsletter) -> Path:
    folder = _target_dir(newsletter)
    path = folder / NEWSLETTER_JSON
    with open(path, "w", encoding="utf-8") as f:
        json.dump(newsletter.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"JSON generated: {path}")
    return path
