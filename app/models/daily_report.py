from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class OverviewBlock:
    date_start: str
    date_end: str
    editor: str
    core_summary: str
    cover_image: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OverviewBlock":
        return cls(
            date_start=data["date_start"],
            date_end=data["date_end"],
            editor=data["editor"],
            core_summary=data["core_summary"],
            cover_image=data.get("cover_image") or "",
        )


@dataclass
class IndustryNewsItem:
    date_label: str
    title: str
    summary: str
    url: str = ""
    image_url: str = ""
    usage_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IndustryNewsItem":
        return cls(
            date_label=data["date_label"],
            title=data["title"],
            summary=data["summary"],
            url=data.get("url") or "",
            image_url=data.get("image_url") or "",
            usage_note=data.get("usage_note") or "",
        )


@dataclass
class NumberedParagraph:
    index: int
    title: str
    body: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NumberedParagraph":
        return cls(
            index=int(data["index"]),
            title=data["title"],
            body=data["body"],
        )


@dataclass
class NumberedBulletGroup:
    index: int
    title: str
    bullets: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NumberedBulletGroup":
        return cls(
            index=int(data["index"]),
            title=data["title"],
            bullets=list(data.get("bullets") or []),
            summary=data.get("summary") or "",
        )


@dataclass
class TechSummarySection:
    title_suffix: str
    trends: list[NumberedParagraph] = field(default_factory=list)
    feasibility: list[NumberedBulletGroup] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title_suffix": self.title_suffix,
            "trends": [t.to_dict() for t in self.trends],
            "feasibility": [f.to_dict() for f in self.feasibility],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TechSummarySection":
        return cls(
            title_suffix=data.get("title_suffix") or "三大趋势",
            trends=[NumberedParagraph.from_dict(t) for t in data.get("trends", [])],
            feasibility=[
                NumberedBulletGroup.from_dict(f) for f in data.get("feasibility", [])
            ],
        )


@dataclass
class WeeklyNewsletter:
    brand_name: str
    overview: OverviewBlock

    industry_news: list[IndustryNewsItem] = field(default_factory=list)

    tech_summary: TechSummarySection | None = None

    issue_dir: str = ""


    # =====================
    # 报告元信息
    # =====================

    # 生成时间
    generated_at: str = ""

    # 第几期双周报告
    issue_number: int = 0

    # 覆盖周期
    period_start: str = ""
    period_end: str = ""

    # 使用的数据源数量
    total_sources: int = 0



    @property
    def date(self) -> str:

        if self.generated_at:
            return self.generated_at[:10]

        return (
            self.overview.date_end
            .replace("年", "-")
            .replace("月", "-")
            .replace("日", "")
        )



    def to_dict(self) -> dict[str, Any]:

        return {

            "brand_name": self.brand_name,


            # 内容
            "overview": self.overview.to_dict(),

            "industry_news": [
                item.to_dict()
                for item in self.industry_news
            ],

            "tech_summary":
                self.tech_summary.to_dict()
                if self.tech_summary
                else None,


            # 元信息
            "date": self.date,
            "generated_at": self.generated_at,

            "issue_number": self.issue_number,

            "period_start": self.period_start,

            "period_end": self.period_end,

            "total_sources": self.total_sources,
        }



    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any]
    ) -> "WeeklyNewsletter":


        tech = data.get("tech_summary")


        return cls(

            brand_name=data["brand_name"],


            overview=OverviewBlock.from_dict(
                data["overview"]
            ),


            industry_news=[
                IndustryNewsItem.from_dict(i)
                for i in data.get(
                    "industry_news",
                    []
                )
            ],


            tech_summary=
                TechSummarySection.from_dict(tech)
                if tech
                else None,


            # 元信息恢复

            generated_at=
                data.get("generated_at")
                or "",


            issue_number=int(
                data.get(
                    "issue_number",
                    0
                )
            ),


            period_start=
                data.get("period_start")
                or "",


            period_end=
                data.get("period_end")
                or "",


            total_sources=int(
                data.get(
                    "total_sources",
                    0
                )
            ),
        )