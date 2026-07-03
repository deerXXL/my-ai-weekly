from dataclasses import dataclass


@dataclass
class SignalCard:
    signal: str
    insight: str
    category: str
    impact: int

    # 🔥 扩展字段（用于系统升级）
    source: str = ""
    title: str = ""
    url: str = ""