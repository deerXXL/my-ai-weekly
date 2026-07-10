import json
import re
import unittest
from datetime import datetime
from pathlib import Path
import tempfile

from app.models.daily_report import (
    IndustryNewsItem,
    NumberedBulletGroup,
    NumberedParagraph,
    OverviewBlock,
    TechSummarySection,
    WeeklyNewsletter,
)
from app.services.export_builder import (
    build_export_html,
    build_export_markdown,
    validate_markdown_structure,
)
from config import (
    format_chinese_date,
    format_date_label,
    load_newsletter_config,
    next_issue_period,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_newsletter.json"


def load_sample_newsletter() -> WeeklyNewsletter:
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return WeeklyNewsletter.from_dict(json.load(f))


class NewsletterConfigTests(unittest.TestCase):
    def test_load_config(self):
        config = load_newsletter_config()
        self.assertEqual(config.brand_name, "闪联AI周刊")
        self.assertEqual(config.overview.label, "本周概览")


class IssueManagerTests(unittest.TestCase):
    def test_chinese_date_format(self):
        self.assertEqual(format_chinese_date(datetime(2025, 9, 8)), "2025年9月8日")

    def test_date_label_format(self):
        self.assertEqual(format_date_label(datetime(2025, 9, 12)), "9月12·周五")

    def test_issue_period(self):
        start, end = next_issue_period(14, datetime(2025, 9, 12))
        self.assertIn("年", start)
        self.assertIn("日", end)
        self.assertLessEqual(start, end)


class NewsletterBuilderTests(unittest.TestCase):
    def setUp(self):
        self.newsletter = load_sample_newsletter()
        self.markdown = build_export_markdown(self.newsletter)

    def test_header_and_overview(self):
        self.assertIn("# 闪联AI周刊", self.markdown)
        self.assertIn("## 🗓 本周概览", self.markdown)
        self.assertIn("**时间范围：**", self.markdown)
        self.assertIn("**核心摘要：**", self.markdown)

    def test_industry_section(self):
        self.assertIn("## 🚀 行业动态", self.markdown)
        self.assertIn("### 9月12·周五", self.markdown)
        self.assertIn("- **阿里通义正式发布", self.markdown)

    def test_tech_summary(self):
        self.assertIn("## 📈 本周AI技术总结", self.markdown)
        self.assertIn("### ☀️ 核心趋势", self.markdown)
        self.assertIn("### 🔮 可行性思考", self.markdown)

    def test_no_old_format(self):
        self.assertNotIn("Signal:", self.markdown)
        self.assertNotIn("AI Daily Report", self.markdown)
        self.assertNotIn("> 第 ", self.markdown)
        self.assertNotIn("## 🧪 实测体验", self.markdown)

    def test_markdown_structure_valid(self):
        issues = validate_markdown_structure(self.markdown)
        self.assertEqual(issues, [], f"Markdown 结构问题: {issues}")

    def test_trend_body_indented(self):
        match = re.search(
            r"1\. \*\*AI变得更「懂行」\*\*\n\n(    .+)",
            self.markdown,
        )
        self.assertIsNotNone(match, "趋势正文应使用 4 空格缩进")

    def test_feasibility_bullets_indented(self):
        chunk = self.markdown.split("### 🔮 可行性思考", 1)[1]
        self.assertRegex(chunk, r"1\. \*\*.+\*\*\n\n    - ")

    def test_html_export(self):
        html = build_export_html(self.newsletter)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("闪联AI周刊", html)
        self.assertIn("行业动态", html)
        self.assertIn('class="date-label"', html)
        self.assertNotIn("实测体验", html)

    def test_usage_note_render(self):
        newsletter = WeeklyNewsletter(
            brand_name="闪联AI周刊",
            overview=OverviewBlock(
                date_start="2026年7月3日",
                date_end="2026年7月9日",
                editor="测试",
                core_summary="测试摘要",
            ),
            industry_news=[
                IndustryNewsItem(
                    date_label="7月9·周四",
                    title="测试资讯",
                    summary="摘要内容",
                    usage_note="适合实时语音客服场景，支持全双工插话",
                    image_url="images/img-0.png",
                )
            ],
            tech_summary=TechSummarySection(
                title_suffix="三大趋势",
                trends=[
                    NumberedParagraph(
                        index=1, title="趋势一", body="趋势说明文字"
                    )
                ],
                feasibility=[
                    NumberedBulletGroup(
                        index=1,
                        title="方向一",
                        bullets=["**场景：** 测试"],
                    )
                ],
            ),
            generated_at="2026-07-09 12:00:00",
        )
        md = build_export_markdown(newsletter)
        html = build_export_html(newsletter)
        self.assertIn("**使用说明：** 适合实时语音客服场景", md)
        self.assertIn("![测试资讯](images/img-0.png)", md)
        self.assertIn('class="news-image"', html)
        self.assertIn('src="/issues/weekly-2026-07-09/images/img-0.png"', html)
        self.assertIn("news-usage", html)
        self.assertEqual(validate_markdown_structure(md), [])


if __name__ == "__main__":
    unittest.main()
