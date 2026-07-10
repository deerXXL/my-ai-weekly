from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from app.crawlers.registry import load_all_sources
from app.models.daily_report import (
    IndustryNewsItem,
    NumberedBulletGroup,
    NumberedParagraph,
    OverviewBlock,
    TechSummarySection,
    WeeklyNewsletter,
)
from app.services.file_writer import write_html, write_json, write_markdown
from app.services.filter import filter_items
from app.services.issue_paths import ensure_issue_dir
from app.services.image_matcher import resolve_image_url
from app.services.llm_signal import analyze_item, compose_newsletter
from app.services.timing import StageTimer
from config import format_date_label, load_newsletter_config, issue_period

ANALYZE_LIMIT = 20
MAX_INDUSTRY_ITEMS = 10
MAX_LLM_WORKERS = 5
MAX_IMAGE_WORKERS = 5

TRUSTED_IMAGE_SOURCES = {"AIbase"}


def _assign_date_labels(count: int, end: datetime, period_days: int = 14) -> list[str]:
    if count <= 0:
        return []
    if count == 1:
        return [format_date_label(end)]
    labels: list[str] = []
    span = max(period_days - 1, 1)
    for i in range(count):
        offset = int(round(i * span / (count - 1)))
        labels.append(format_date_label(end - timedelta(days=offset)))
    return labels

def _sort_items_by_date(items):
    """
    按发布时间升序排列
    无日期排最后
    """

    def _key(item):

        if item.published_at:

            try:
                return datetime.strptime(
                    item.published_at,
                    "%Y-%m-%d"
                )

            except (
                ValueError,
                TypeError
            ):
                pass

        return datetime.max


    return sorted(
        items,
        key=_key
    )


def _analyze_parallel(items, limit: int) -> list[dict]:
    targets = items[:limit]
    slots: list[dict | None] = [None] * len(targets)
    with ThreadPoolExecutor(max_workers=MAX_LLM_WORKERS) as executor:
        future_map = {
            executor.submit(analyze_item, item): idx
            for idx, item in enumerate(targets)
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                slots[idx] = future.result()
            except Exception as exc:
                print(f"  分析失败: {targets[idx].title[:30]} — {exc}")
    return [s for s in slots if s is not None]


def _resolve_one_image(args: tuple) -> tuple[int, str]:
    idx, c, date_tag = args
    path = resolve_image_url(
        c["title_zh"],
        c["summary"],
        page_url=c.get("url") or "",
        candidate_image=c.get("image_url") or "",
        date_tag=date_tag,
        index=idx,
        trust_candidate=bool(c.get("image_url"))
        and c.get("source") in TRUSTED_IMAGE_SOURCES,
    )
    return idx, path


def _build_industry_news(
    candidates: list[dict],
    selected_indices: list[int],
    end: datetime,
    date_tag: str,
    period_days: int,
    industry_notes: dict | None = None,
) -> list[IndustryNewsItem]:
    labels = _assign_date_labels(len(selected_indices), end, period_days)
    image_paths: dict[int, str] = {}
    notes = industry_notes or {}

    tasks = []
    for img_idx, idx in enumerate(selected_indices):
        if 0 <= idx < len(candidates):
            tasks.append((img_idx, candidates[idx], date_tag))

    with ThreadPoolExecutor(max_workers=MAX_IMAGE_WORKERS) as executor:
        futures = [executor.submit(_resolve_one_image, t) for t in tasks]
        for future in as_completed(futures):
            img_idx, path = future.result()
            if path:
                image_paths[img_idx] = path

    items: list[IndustryNewsItem] = []
    for img_idx, (label, idx) in enumerate(zip(labels, selected_indices)):
        if idx < 0 or idx >= len(candidates):
            continue
        c = candidates[idx]
        note = notes.get(str(idx)) or notes.get(idx) or ""
        items.append(
            IndustryNewsItem(
                date_label=label,
                title=c["title_zh"],
                summary=c["summary"],
                url=c.get("url") or "",
                image_url=image_paths.get(img_idx, ""),
                usage_note=str(note).strip(),
            )
        )
    return items


def _build_tech_summary(data: dict) -> TechSummarySection:
    raw = data.get("tech_summary") or {}
    trends = [
        NumberedParagraph(
            index=int(t.get("index", i + 1)),
            title=t.get("title") or f"趋势{i + 1}",
            body=t.get("body") or "",
        )
        for i, t in enumerate(raw.get("trends") or [])
    ]
    feasibility = [
        NumberedBulletGroup(
            index=int(f.get("index", i + 1)),
            title=f.get("title") or f"方向{i + 1}",
            bullets=list(f.get("bullets") or []),
        )
        for i, f in enumerate(raw.get("feasibility") or [])
    ]
    return TechSummarySection(
        title_suffix=raw.get("title_suffix") or "三大趋势",
        trends=trends[:3],
        feasibility=feasibility[:3],

    )


def run_pipeline(analyze_limit: int = ANALYZE_LIMIT) -> WeeklyNewsletter:
    """闪联AI周刊主流程：抓取 → 分析 → 策展 → 配图 → 输出。"""
    cfg = load_newsletter_config()
    now = datetime.now()
    date_tag = now.strftime("%Y-%m-%d")
    ensure_issue_dir(date_tag)
    timer = StageTimer()

    print(f"\n本期范围：近 {cfg.period_days} 天\n")

    with timer.stage("抓取资讯"):

        items = filter_items(
            load_all_sources(),
            days=cfg.period_days,
            mode="practical",
        )

        items = _sort_items_by_date(items)
    print(f"过滤后 {len(items)} 条，并行分析前 {analyze_limit} 条（{MAX_LLM_WORKERS} 并发）\n")

    with timer.stage("LLM逐条分析"):
        candidates = _analyze_parallel(items, analyze_limit)

    if not candidates:
        raise RuntimeError("没有成功分析的资讯条目")
    print(f"\n分析完成 {len(candidates)} 条\n")

    with timer.stage("LLM策展合成"):
        composed = compose_newsletter(candidates, MAX_INDUSTRY_ITEMS)

    selected = composed.get("selected_indices") or list(
        range(min(MAX_INDUSTRY_ITEMS, len(candidates)))
    )
    selected = [int(i) for i in selected[:MAX_INDUSTRY_ITEMS]]
    date_start, date_end = issue_period(cfg.period_days, today=now)

    industry_notes = composed.get("industry_notes") or {}

    with timer.stage("配图下载"):
        industry_news = _build_industry_news(
            candidates,
            selected,
            now,
            date_tag,
            cfg.period_days,
            industry_notes=industry_notes,
        )
    with_images = sum(1 for n in industry_news if n.image_url)
    with_notes = sum(1 for n in industry_news if n.usage_note)
    print(f"  配图成功 {with_images}/{len(industry_news)} 条")
    print(f"  使用说明 {with_notes}/{len(industry_news)} 条\n")

    newsletter = WeeklyNewsletter(
        brand_name=cfg.brand_name,
        overview=OverviewBlock(
            date_start=date_start,
            date_end=date_end,
            editor=cfg.default_editor,
            core_summary=composed.get("core_summary") or "近两周 AI 领域持续活跃。",
        ),
        industry_news=industry_news,
        tech_summary=_build_tech_summary(composed),
        generated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
    )

    with timer.stage("写入文件"):
        write_json(newsletter)
        write_markdown(newsletter)
        write_html(newsletter)

    print(
        f"Pipeline finished. industry_news={len(newsletter.industry_news)} "
        f"images={with_images} usage_notes={with_notes}"
    )
    print(timer.summary())
    return newsletter
