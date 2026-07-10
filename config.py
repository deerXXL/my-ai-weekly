import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
NEWSLETTER_CONFIG_PATH = BASE_DIR / "config" / "newsletter.json"

ARK_API_KEY = os.getenv("ARK_API_KEY")
ARK_BASE_URL = os.getenv("ARK_BASE_URL")
ARK_MODEL = os.getenv("ARK_MODEL")

WEEKDAY_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


@dataclass(frozen=True)
class SectionStyle:
    icon: str
    label: str = ""


@dataclass(frozen=True)
class NewsletterConfig:
    brand_name: str
    default_editor: str
    period_days: int
    overview: SectionStyle
    industry: SectionStyle
    tech_summary_icon: str
    tech_summary_label_prefix: str


def load_newsletter_config(path: Path | None = None) -> NewsletterConfig:
    config_path = path or NEWSLETTER_CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    sections = raw["sections"]
    return NewsletterConfig(
        brand_name=raw["brand_name"],
        default_editor=raw["default_editor"],
        period_days=int(raw["period_days"]),
        overview=SectionStyle(
            icon=sections["overview"]["icon"],
            label=sections["overview"]["label"],
        ),
        industry=SectionStyle(
            icon=sections["industry"]["icon"],
            label=sections["industry"]["label"],
        ),
        tech_summary_icon=sections["tech_summary"]["icon"],
        tech_summary_label_prefix=sections["tech_summary"]["label_prefix"],
    )


def format_chinese_date(value: datetime) -> str:
    return f"{value.year}年{value.month}月{value.day}日"


def format_date_label(value: datetime) -> str:
    return f"{value.month}月{value.day}·{WEEKDAY_CN[value.weekday()]}"


def issue_period(
    period_days: int = 14,
    today: datetime | None = None,
) -> tuple[str, str]:
    """返回本期时间范围（滚动窗口，起止始终正确）。"""
    now = today or datetime.now()
    start = now - timedelta(days=max(period_days - 1, 0))
    if start > now:
        start = now
    return format_chinese_date(start), format_chinese_date(now)


# 兼容旧调用
def next_issue_period(
    period_days: int = 14,
    today: datetime | None = None,
) -> tuple[str, str]:
    return issue_period(period_days, today)
