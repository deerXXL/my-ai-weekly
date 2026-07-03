from dataclasses import dataclass
from typing import Optional


@dataclass
class RawItem:
    source: str
    title: str
    description: str
    url: str

    author: Optional[str] = None
    published_at: Optional[str] = None
    tags: Optional[list] = None