import json
from pathlib import Path

from app.models.daily_report import WeeklyNewsletter

from app.services.export_builder import (
    build_export_html,
    build_export_markdown,
)

from app.services.issue_paths import (
    NEWSLETTER_HTML,
    NEWSLETTER_JSON,
    NEWSLETTER_MD,
    ensure_issue_dir,
    set_latest_issue,
)



def _target_dir(newsletter: WeeklyNewsletter) -> Path:
    """
    获取当前报告保存目录
    """
    date_tag = newsletter.date or newsletter.generated_at[:10]

    return ensure_issue_dir(date_tag)



def write_html(newsletter: WeeklyNewsletter) -> Path:
    """
    输出 HTML 文件
    """

    folder = _target_dir(newsletter)

    path = folder / NEWSLETTER_HTML


    path.write_text(
        build_export_html(newsletter),
        encoding="utf-8"
    )


    set_latest_issue(
        newsletter.date or newsletter.generated_at[:10]
    )


    print(
        f"HTML generated: {path}"
    )

    return path



def write_markdown(newsletter: WeeklyNewsletter) -> Path:
    """
    输出 Markdown 文件
    """

    folder = _target_dir(newsletter)

    path = folder / NEWSLETTER_MD


    path.write_text(
        build_export_markdown(newsletter),
        encoding="utf-8"
    )


    print(
        f"Markdown generated: {path}"
    )

    return path



def write_json(newsletter: WeeklyNewsletter) -> Path:
    """
    输出 JSON 文件
    """

    folder = _target_dir(newsletter)

    path = folder / NEWSLETTER_JSON


    payload = newsletter.to_dict()

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )

    # 同步写入 output/latest.json（旧入口 /api/summarize 等仍依赖它），
    # 保证前端始终能读到最新一期数据，而不是停留在旧的 latest.json。
    legacy_latest = folder.parent / "latest.json"
    with open(
        legacy_latest,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"JSON generated: {path}"
    )

    return path

    return path