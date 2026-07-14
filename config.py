import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROXY_ENV_KEYS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _getenv(name: str, default: str | None = None) -> str | None:
    """读取环境变量，空字符串（GitHub Secrets 缺失时展开为 ''）视为未设置并回退默认值。

    关键：os.getenv(name, default) 在 env 值为空字符串时【不会】回退默认值，
    会让 OpenAI client 拿到 base_url='' 而回退到 https://api.openai.com/v1，
    用 ARK Key 请求 OpenAI 官方端点 → 401 "Incorrect API key provided"。
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw


# 默认直连；仅当 AI_WEEKLY_USE_PROXY=1 时才保留 HTTP_PROXY/HTTPS_PROXY 等环境变量
USE_HTTP_PROXY = _env_flag("AI_WEEKLY_USE_PROXY", default=False)
if not USE_HTTP_PROXY:
    for key in _PROXY_ENV_KEYS:
        os.environ.pop(key, None)

BASE_DIR = Path(__file__).resolve().parents[0]
OUTPUT_DIR = BASE_DIR / "output"
NEWSLETTER_CONFIG_PATH = BASE_DIR / "config" / "newsletter.json"

ARK_API_KEY = _getenv("ARK_API_KEY")
ARK_BASE_URL = _getenv(
    "ARK_BASE_URL",
    "https://ark.cn-beijing.volces.com/api/v3"
)
ARK_MODEL = _getenv("ARK_MODEL")
ARK_IMAGE_BASE_URL = _getenv(
    "ARK_IMAGE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
)
ARK_IMAGE_MODEL = _getenv("ARK_IMAGE_MODEL", "doubao-seedream-4-5-251128")

# 启动期诊断：避免 Key/端点缺失时静默打到 OpenAI 官方端点（会导致 401 误判）
_masked_key = (ARK_API_KEY[:6] + "***" + ARK_API_KEY[-4:]) if ARK_API_KEY else "<EMPTY>"
_diag_msg = (
    f"[config] ARK_API_KEY={_masked_key} "
    f"ARK_BASE_URL={ARK_BASE_URL or '<EMPTY>'} "
    f"ARK_MODEL={ARK_MODEL or '<EMPTY>'} "
    f"ARK_IMAGE_BASE_URL={ARK_IMAGE_BASE_URL or '<EMPTY>'} "
    f"ARK_IMAGE_MODEL={ARK_IMAGE_MODEL}"
)
print(_diag_msg)
# 同时写 stderr，确保 CI 日志中可见（stdout 可能被缓冲/截断）
import sys
print(_diag_msg, file=sys.stderr)
# CI 环境下额外用 ::warning:: 注解，在 GitHub Actions 摘要页高亮显示
if os.getenv("GITHUB_ACTIONS") == "true":
    print(f"::warning:: {_diag_msg}", file=sys.stderr)

if not ARK_API_KEY:
    raise RuntimeError(
        "ARK_API_KEY 未配置或为空。请检查 .env 或 GitHub Secrets 中的 ARK_API_KEY。"
    )
if not ARK_BASE_URL or not ARK_BASE_URL.startswith("https://ark"):
    raise RuntimeError(
        f"ARK_BASE_URL 异常：{ARK_BASE_URL!r}。"
        "应为火山方舟端点（https://ark.*.volces.com/...），否则会用 ARK Key 请求 "
        "OpenAI 官方端点导致 401。"
    )

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
