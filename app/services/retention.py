"""期刊保留策略：仅保留最近 N 个「不重复周期」的期，自动清理更旧的目录/文件。

设计要点：
- 每一期本质是「一段时间」而非单天：覆盖周期由 ``period_start`` → ``period_end`` 界定
  （如 2026年7月1日 — 2026年7月14日，双周窗口）。因此去重/排序都以「周期」为单位，
  而不是用 ``date`` 这个单天字段，避免把「同日生成但周期重叠」的期刊误判为两期。
- 去重键 = ``period_start``（同一起点的期视为同一周期，只保留最新的一份）；
  排序键 = ``period_end``（取周期更近的一端）。
- 取周期降序的前 N 个不重复周期作为保留集，其余（更旧的 / 同周期的旧副本）一并删除。
- 不同时删除 ``latest.json``、``.latest`` 指针与 ``tasks.json``（它们不属于某一期）。
- 周期字段缺失或解析失败时，回退到目录名日期（ISO），仍按周期语义处理。
"""
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

from config import OUTPUT_DIR, REPORT_RETAIN_ISSUES

_CN_DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")


def _parse_date(value) -> date | None:
    """兼容中文「YYYY年M月D日」与 ISO「YYYY-MM-DD」两种格式。"""
    if not value:
        return None
    s = str(value).strip()
    m = _CN_DATE_RE.search(s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _iter_issue_candidates():
    """遍历磁盘上的全部期刊，yield (date_str, path, is_dir)。"""
    for p in sorted(OUTPUT_DIR.glob("weekly-*"), reverse=True):
        if p.is_dir():
            nj = p / "newsletter.json"
            if nj.exists():
                yield (p.name.replace("weekly-", ""), p, True)
        elif p.suffix == ".json" and p.name != "latest.json":
            # 旧格式平铺：weekly-YYYY-MM-DD.json
            yield (p.stem.replace("weekly-", ""), p, False)


def _issue_period(path: Path, fallback_date_str: str):
    """返回 (sort_key, dedup_key)。

    sort_key 用于排序（取周期末端 period_end，回退到单天 date / 目录名日期）；
    dedup_key 用于去重（取周期起点 period_start，回退到 sort_key）。
    解析失败一律回退到目录名日期，保证总有可比较的值。
    """
    fb = _parse_date(fallback_date_str) or date.min
    ps = pe = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ps = _parse_date(data.get("period_start"))
        pe = _parse_date(data.get("period_end"))
    except Exception:
        pass

    sort_key = pe or _parse_date(fallback_date_str) or fb
    dedup_key = ps or sort_key
    return sort_key, dedup_key


def cleanup_old_issues(keep: int | None = None, dry_run: bool = False) -> dict:
    """清理保留集以外的旧期刊。

    Args:
        keep: 保留的不重复周期期数，默认取 ``REPORT_RETAIN_ISSUES``。
        dry_run: 仅统计将要删除的项，不真正删除。

    Returns:
        包含 kept_periods / removed / 计数等信息的字典。
    """
    # 至少保留 1 期：保证网页永远有内容可展示（不会因配置错误或清理逻辑异常而清空）
    if keep is None:
        keep = REPORT_RETAIN_ISSUES
    keep = max(1, keep)
    items = []
    for date_str, path, is_dir in _iter_issue_candidates():
        sort_key, dedup_key = _issue_period(
            (path / "newsletter.json") if is_dir else path, date_str
        )
        items.append((sort_key, dedup_key, date_str, path, is_dir))

    # 按周期末端降序；保留前 keep 个「不重复周期」（同周期只留最新一份）
    items.sort(key=lambda it: it[0], reverse=True)
    keep_keys: set = set()
    kept = []
    removed = []
    for sort_key, dedup_key, date_str, path, is_dir in items:
        if dedup_key in keep_keys:
            # 与已保留期同周期（如同一窗口的重复生成）→ 删除旧副本
            if not dry_run:
                if is_dir:
                    shutil.rmtree(path)
                else:
                    path.unlink()
            removed.append(str(path))
        elif len(keep_keys) < keep:
            keep_keys.add(dedup_key)
            kept.append(date_str)
        else:
            if not dry_run:
                if is_dir:
                    shutil.rmtree(path)
                else:
                    path.unlink()
            removed.append(str(path))

    # 删除后按日期升序重排剩余期号，避免留空档
    # （如删掉第1期后，原第2、3期重排为第1、2期，保持连续递增）
    if not dry_run:
        renumber_all_issues()

    return {
        "keep": keep,
        "kept_periods": sorted({it[1].isoformat() for it in items if it[1] in keep_keys}, reverse=True),
        "kept_count": len(kept),
        "removed": removed,
        "removed_count": len(removed),
        "dry_run": bool(dry_run),
    }


def renumber_all_issues() -> int:
    """按日期升序把磁盘上所有期重新连续编号为 1..N，并同步 latest.json。

    用于定期删除（cleanup_old_issues）之后，使保留下来的期号不留空档、连续递增。
    排序键优先用 ``period_start``（周期起点），回退单天 ``date``，保证按周期先后连续。
    新生成的当期若已写入磁盘，也会被纳入并排在序列末尾（编号最大）。

    Returns:
        重排后的期数 N。若无任何期刊则返回 0。
    """
    candidates = []
    for date_str, path, is_dir in _iter_issue_candidates():
        nj = (path / "newsletter.json") if is_dir else path
        try:
            with open(nj, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        sort_date = (
            _parse_date(data.get("period_start"))
            or _parse_date(data.get("date"))
            or date.min
        )
        candidates.append((sort_date, date_str, path, is_dir, data))

    candidates.sort(key=lambda c: c[0])  # 日期升序
    n = 0
    for i, (_, date_str, path, is_dir, data) in enumerate(candidates, 1):
        data["issue_number"] = i
        target = (path / "newsletter.json") if is_dir else path
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        n = i

    # 同步 latest.json 的 issue_number 为最新一期（升序最后即最新）
    _sync_latest_issue_number(n)
    return n


def _sync_latest_issue_number(issue_no: int | None) -> None:
    """把 latest.json 里的顶层 issue_number 更新为最新一期号（不改动其他字段）。"""
    if not issue_no:
        return
    lp = OUTPUT_DIR / "latest.json"
    if not lp.exists():
        return
    try:
        with open(lp, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["issue_number"] = issue_no
        with open(lp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
