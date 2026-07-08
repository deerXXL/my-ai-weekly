from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RawItem:

    source: str

    title: str

    description: str

    url: str

    category: str = ""

    author: Optional[str] = None

    published_at: Optional[str] = None

    tags: Optional[list] = None

    extra: dict = field(
        default_factory=dict
    )