from dataclasses import dataclass, field
from typing import List

from app.models.signal_card import SignalCard
from app.models.raw_item import RawItem


@dataclass
class DailyReport:

    date: str

    title: str

    summary: str

    items: List[RawItem] = field(default_factory=list)

    signals: List[SignalCard] = field(default_factory=list)

    github_projects: List[dict] = field(default_factory=list)

    generated_at: str = ""

    # 双周报告元信息
    issue_number: int = 0       # 第N期
    period_start: str = ""      # 统计起始日期 YYYY-MM-DD
    period_end: str = ""        # 统计截止日期 YYYY-MM-DD
    total_sources: int = 0      # 数据源总数