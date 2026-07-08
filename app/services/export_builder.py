"""
为"生成完整周报文档"按钮服务。
读取 weekly JSON，生成排版精美、可直接发给团队的 Markdown。
"""
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import json


BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "output"


CATEGORY_LABELS = {
    "大模型": "大模型动态",
    "产品更新": "产品更新",
    "行业报告": "行业报告",
    "多模态": "多模态",
    "ToB": "ToB 与企业服务",
    "办公AI": "办公 AI",
    "产品评测": "产品评测",
    "开源项目": "开源项目",
    "AI": "其他",
    "Unknown": "其他",
}

CATEGORY_ORDER = [
    "大模型", "产品更新", "行业报告", "多模态",
    "ToB", "办公AI", "产品评测", "开源项目", "AI", "Unknown",
]


def _load_latest() -> dict | None:
    latest = OUTPUT_DIR / "latest.json"
    target = latest if latest.exists() else None

    if target is None:
        candidates = sorted(OUTPUT_DIR.glob("weekly-*.json"), reverse=True)
        target = candidates[0] if candidates else None

    if target is None or not target.exists():
        return None

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def build_export_markdown(report: dict) -> str:
    date = report.get("date") or datetime.now().strftime("%Y-%m-%d")
    title = report.get("title") or "AI 双周产品周报"
    signals = report.get("signals", [])

    # 按 category 分组
    grouped = defaultdict(list)
    for s in signals:
        cat = s.get("category") or "AI"
        grouped[cat].append(s)

    # 组内按 impact 降序
    for cat in grouped:
        grouped[cat].sort(key=lambda x: x.get("impact", 0), reverse=True)

    lines = []
    lines.append(f"# {title}（{date}）")
    lines.append("")
    lines.append(f"> 本期共收录 **{len(signals)}** 条 AI 行业信号，"
                 f"统计周期：{date}（双周）")
    lines.append("")
    lines.append(f"**编辑**：产品资讯归档组  ")
    lines.append(f"**生成时间**：{report.get('generated_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**编辑整理**：WorkBuddy 协助")
    lines.append("")

    summary = report.get("summary", "").strip()
    if summary:
        lines.append("## 本期概览")
        lines.append("")
        lines.append(summary)
        lines.append("")

    # 分类小节
    lines.append("## 分类速览")
    lines.append("")
    for cat in CATEGORY_ORDER:
        if cat in grouped:
            lines.append(f"- **{CATEGORY_LABELS.get(cat, cat)}**：{len(grouped[cat])} 条")
    lines.append("")

    # 详细正文：按分类、热度排序
    lines.append("## 资讯详情")
    lines.append("")
    for cat in CATEGORY_ORDER:
        items = grouped.get(cat)
        if not items:
            continue
        lines.append(f"### {CATEGORY_LABELS.get(cat, cat)}")
        lines.append("")
        for i, s in enumerate(items, 1):
            t = s.get("title") or s.get("signal") or "(无标题)"
            url = s.get("url") or "#"
            source = s.get("source") or ""
            impact = s.get("impact", 1)
            insight = s.get("insight") or s.get("signal") or ""
            lines.append(f"#### {i}. {t}")
            lines.append("")
            lines.append(f"- **来源**：{source}　**热度**：{'★' * max(1, int(impact))}（{impact}/5）")
            if url and url != "#":
                lines.append(f"- **原文**：[点击阅读]({url})")
            if insight:
                lines.append(f"- **摘要**：{insight}")
            lines.append("")

    # 来源统计
    sources = defaultdict(int)
    for s in signals:
        sources[s.get("source") or "未知"] += 1
    if sources:
        lines.append("## 来源统计")
        lines.append("")
        for src, n in sorted(sources.items(), key=lambda x: -x[1]):
            lines.append(f"- {src}：{n} 条")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 WorkBuddy 协作生成，原始数据来自 GitHub Trending、"
                 "OpenAI Blog、HuggingFace、Google Research、TechCrunch、VentureBeat、"
                 "机器之心、36 氪、Reddit ML 等公开渠道。*")
    lines.append("")

    return "\n".join(lines)


def export_latest_markdown() -> Path | None:
    """
    生成最新一期完整 Markdown 周报，返回文件路径。
    文件名: weekly-日期-export.md
    """
    report = _load_latest()
    if report is None:
        return None

    date = report.get("date") or datetime.now().strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"weekly-{date}-export.md"

    content = build_export_markdown(report)
    # Windows 上同名文件可能被 AV / Search Indexer 短暂持锁，
    # 先尝试移除再写；失败则用临时文件 rename
    try:
        if out_path.exists():
            out_path.unlink()
    except OSError:
        pass
    tmp_path = out_path.with_suffix(".md.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    try:
        tmp_path.replace(out_path)
    except OSError:
        # 最后兜底：直接覆盖
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        tmp_path.unlink(missing_ok=True)
    return out_path
