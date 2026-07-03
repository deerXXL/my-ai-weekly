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