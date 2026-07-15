"""闪联AI周刊 Web 服务：HTML 预览、导出、静态资源。"""
import io
import json
import threading
import time
import traceback
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from app.services.report_reader import to_frontend_articles

from flask import (
    Flask,
    Response,
    jsonify,
    request,
    send_from_directory,
    render_template,
)
from app.services.export_builder import (
    build_export_html,
    build_export_markdown,
    load_latest_report_dict,
)

app = Flask(__name__)

TASKS = {}
TASK_LOCK = threading.Lock()

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
TASKS_FILE = OUTPUT_DIR / "tasks.json"


def _load_tasks():
    """从磁盘加载历史任务状态，避免 Render 实例重启/休眠后任务 ID 丢失。"""
    if not TASKS_FILE.exists():
        return
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        # 若任务仍标为 running 但已启动超过 30 分钟，大概率是实例重启导致线程中断
        for task in data.values():
            if task.get("status") == "running" and now - task.get("started_at", now) > 1800:
                task["status"] = "failed"
                task["message"] = "任务超时：后台实例已重启或休眠，请重新启动"
                task["error"] = "后台任务因实例重启而中断"
        with TASK_LOCK:
            TASKS.update(data)
        _save_tasks()
    except Exception as exc:
        print("加载任务状态失败：", exc)


def _save_tasks():
    """把当前任务状态写入磁盘。"""
    try:
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = TASKS_FILE.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(TASKS, f, ensure_ascii=False, indent=2)
        tmp.replace(TASKS_FILE)
    except Exception as exc:
        print("保存任务状态失败：", exc)


_load_tasks()


def _new_task(name: str) -> str:
    _load_tasks()  # 合并磁盘上的历史任务，防止实例重启后状态丢失
    tid = uuid.uuid4().hex[:12]
    with TASK_LOCK:
        TASKS[tid] = {
            "id": tid,
            "name": name,
            "status": "running",
            "progress": 0,
            "message": "已启动",
            "started_at": time.time(),
            "result": None,
            "error": None,
        }
    _save_tasks()
    return tid


def _update_task(tid: str, **kwargs):
    with TASK_LOCK:
        if tid not in TASKS:
            return
        TASKS[tid].update(kwargs)
    _save_tasks()


def _run_collect(tid: str):
    try:
        _update_task(tid, progress=5, message="正在加载数据源…")
        from app.pipeline import run_pipeline
        report = run_pipeline()
        n = len(report.industry_news or [])
        _update_task(
            tid,
            status="success",
            progress=100,
            message=f"采集完成，共 {n} 条行业动态",
            result={"signal_count": n, "date": report.date},
        )
    except Exception as exc:
        _update_task(
            tid,
            status="failed",
            message=f"采集失败：{exc}",
            error=traceback.format_exc(),
        )


def _run_summarize(tid: str):
    try:
        import json
        from datetime import datetime
        from app.services.llm_signal import regenerate_signal_card

        latest = OUTPUT_DIR / "latest.json"
        if not latest.exists():
            candidates = sorted(OUTPUT_DIR.glob("weekly-*.json"), reverse=True)
            if not candidates:
                _update_task(
                    tid, status="failed",
                    message="未找到可用的 weekly JSON"
                )
                return
            latest = candidates[0]

        _update_task(tid, progress=10, message=f"读取 {latest.name}…")
        with open(latest, "r", encoding="utf-8") as f:
            report = json.load(f)

        signals = report.get("signals", [])
        total = len(signals)
        if total == 0:
            _update_task(
                tid, status="failed", message="当前报告无 signal"
            )
            return

        updated = 0
        for i, sig in enumerate(signals, 1):
            _update_task(
                tid,
                progress=10 + int(80 * i / total),
                message=f"正在整理 {i}/{total}：{sig.get('title','')[:30]}",
            )
            new = regenerate_signal_card(sig)
            sig["signal"] = new["signal"]
            sig["insight"] = new["insight"]
            sig["category"] = new["category"]
            sig["impact"] = new["impact"]
            updated += 1

        # 重新生成 summary
        top = sorted(signals, key=lambda x: x.get("impact", 0), reverse=True)[:3]
        report["summary"] = (
            f"本次整理共刷新 {updated} 条信号。"
            f"重点关注：{' / '.join(t.get('title','') for t in top if t.get('title'))}"
        )
        report["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report.setdefault("date", datetime.now().strftime("%Y-%m-%d"))

        with open(latest, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 同步 weekly-日期.json
        weekly = OUTPUT_DIR / f"weekly-{report['date']}.json"
        with open(weekly, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        _update_task(
            tid,
            status="success",
            progress=100,
            message=f"摘要整理完成，共刷新 {updated} 条",
            result={"updated": updated, "date": report["date"]},
        )
    except Exception as exc:
        _update_task(
            tid,
            status="failed",
            message=f"整理失败：{exc}",
            error=traceback.format_exc(),
        )


# ============================================================
# 路由
# ============================================================
@app.route("/output/<path:filename>")
def output_file(filename):
    return send_from_directory(
        OUTPUT_DIR,
        filename
    )

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/report")
def api_report():
    import json as _json
    filename = request.args.get("file")

    if filename:
        path = OUTPUT_DIR / filename
        # 兼容新格式目录：output/weekly-YYYY-MM-DD/newsletter.json
        if path.is_dir():
            path = path / "newsletter.json"
        if not path.exists():
            return jsonify({"error": f"文件不存在：{filename}"}), 404
        with open(path, "r", encoding="utf-8") as f:
            report = _json.load(f)
    else:
        report = load_latest_report_dict()
        print("加载报告结果:", report)

    if report is None:
        return jsonify([])

    # 将原始报告统一转为前端所需格式（兼容 industry_news 和 signals）
    articles = to_frontend_articles(report)

    # 提取 overview / meta 信息一并返回
    overview = report.get("overview") or {}
    result = {
        "articles": articles,
        "overview": overview,
        "brand_name": report.get("brand_name", ""),
        "title": report.get("title", ""),
        "date": report.get("date", ""),
        "generated_at": report.get("generated_at", ""),
        "period_start": report.get("period_start", ""),
        "period_end": report.get("period_end", ""),
        "issue_number": report.get("issue_number", 0),
    }

    # 新格式 industry_news 中每条有 image_url，也保留在 articles 里
    # image_url 字段已通过 to_frontend_articles 从 industry_news / signals 透传
    return jsonify(result)


@app.route("/api/meta")
def api_meta():
    report = load_latest_report_dict()
    if report is None:
        return jsonify({})

    overview = report.get("overview") or {}

    period_start = (
        report.get("period_start")
        or overview.get("date_start", "")
        or ""
    )

    period_end = (
        report.get("period_end")
        or overview.get("date_end", "")
        or ""
    )


    # 获取当前周报目录
    date = report.get("date") or (report.get("generated_at") or "")[:10]


    raw_cover = overview.get("cover_image", "")

    if raw_cover.startswith(("http://", "https://", "/output/")):
        # 已是完整可访问地址，原样返回
        cover_image = raw_cover
    else:
        # 相对路径：去掉可能带上的 issue 目录前缀（weekly-YYYY-MM-DD/），
        # 仅保留 images/xxx 形式，由前端拼接 /output/weekly-{date}/ 得到最终地址
        rel = raw_cover
        issue_prefix = f"weekly-{date}/"
        if rel.startswith(issue_prefix):
            rel = rel[len(issue_prefix):]
        cover_image = rel

    return jsonify({
        "title": report.get("title") or report.get("brand_name", ""),
        "date": date,
        "period_start": period_start,
        "period_end": period_end,
        "issue_number": report.get("issue_number", 0),

        "cover_image": cover_image,

        "overview": overview
    })


@app.route("/api/archive")
def api_archive():
    import json
    from datetime import datetime, timedelta

    # 收集所有期号：兼容两种存储格式
    #  - 旧：output/weekly-YYYY-MM-DD.json
    #  - 新：output/weekly-YYYY-MM-DD/newsletter.json
    entries = []  # (date_str, path)

    for file in OUTPUT_DIR.glob("weekly-*.json"):
        date_str = file.stem.replace("weekly-", "")
        entries.append((date_str, file))

    for d in OUTPUT_DIR.glob("weekly-*"):
        if not d.is_dir():
            continue
        nj = d / "newsletter.json"
        if nj.exists():
            date_str = d.name.replace("weekly-", "")
            entries.append((date_str, nj))

    # 同一日期去重（优先目录内 newsletter.json）
    seen = {}
    for date_str, path in entries:
        key = date_str
        prefer_dir = path.name == "newsletter.json"
        if key not in seen or (prefer_dir and seen[key].name != "newsletter.json"):
            seen[key] = path

    # 按日期升序编号（最旧的 = 第1期）
    sorted_items = sorted(seen.items(), key=lambda kv: kv[0])
    total = len(sorted_items)
    reports = []
    for idx, (date_str, file) in enumerate(sorted_items, 1):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            overview = data.get("overview") or {}
            period_start = data.get("period_start") or overview.get("date_start", "")
            period_end = data.get("period_end") or overview.get("date_end", "")
            if not period_start or not period_end:
                try:
                    d = datetime.strptime(date_str, "%Y-%m-%d")
                    period_start = period_start or (d - timedelta(days=14)).strftime("%Y-%m-%d")
                    period_end = period_end or date_str
                except ValueError:
                    pass

            issue_number = data.get("issue_number") or (total - idx + 1)

            title = data.get("title", "")
            if not title or title == "AI Daily Report":
                title = f"AI双周产品周报 · 第{issue_number}期"

            # 新格式用 industry_news，旧格式用 signals
            count = len(data.get("industry_news") or data.get("signals") or [])

            reports.append({
                "file": file.parent.name if file.name == "newsletter.json" else file.name,
                "date": date_str,
                "title": title,
                "issue_number": issue_number,
                "period_start": period_start,
                "period_end": period_end,
                "signal_count": count,
                "size_kb": round(file.stat().st_size / 1024, 1),
                "mtime": file.stat().st_mtime,
            })
        except Exception as exc:
            print("archive entry error:", file, exc)

    # 降序返回（最新的在前）
    reports.reverse()
    return jsonify(reports)


@app.route("/api/collect", methods=["POST"])
def api_collect():
    # 同一天已采集过则直接返回，不重复跑流水线
    today = datetime.now().strftime("%Y-%m-%d")
    # 兼容新旧两种存储：新格式目录内的 newsletter.json，或旧格式平铺 json
    today_new = OUTPUT_DIR / f"weekly-{today}" / "newsletter.json"
    today_old = OUTPUT_DIR / f"weekly-{today}.json"
    if today_new.exists() or today_old.exists():
        return jsonify({
            "status": "already_updated",
            "message": f"今天（{today}）已更新过本期资讯，无需重复采集",
            "date": today,
        })

    tid = _new_task("collect")
    th = threading.Thread(target=_run_collect, args=(tid,), daemon=True)
    th.start()
    return jsonify({
        "status": "started",
        "task_id": tid,
        "message": "采集任务已启动，可在 5–10 分钟后回来查看",
    })


@app.route("/api/summarize", methods=["POST"])
def api_summarize():
    tid = _new_task("summarize")
    th = threading.Thread(target=_run_summarize, args=(tid,), daemon=True)
    th.start()
    return jsonify({
        "status": "started",
        "task_id": tid,
        "message": "摘要整理任务已启动",
    })


@app.route("/api/task/<tid>")
def api_task(tid: str):
    with TASK_LOCK:
        task = TASKS.get(tid)
    # 内存里没有则尝试从磁盘恢复（Render 实例休眠/重启后 TASKS 会被清空）
    if not task:
        _load_tasks()
        with TASK_LOCK:
            task = TASKS.get(tid)
    if not task:
        return jsonify({
            "status": "not_found",
            "message": "任务已失效，请重新启动"
        }), 200
    return jsonify(task)


@app.route("/api/export", methods=["POST", "GET"])
def api_export():
    try:
        report = load_latest_report_dict()
        if report is None:
            return jsonify({
                "status": "failed",
                "message": "暂无可导出的周报数据，请先生成",
            }), 400

        date = (report.get("generated_at") or "unknown")[:10]

        md = build_export_markdown(report)
        # 导出 HTML 使用相对路径，脱离服务器也能显示图片
        html = build_export_html(report, relative=True)

        # 组装自包含 ZIP：newsletter.md + newsletter.html + images/
        # 解压后 md/html 与 images/ 同级，图片即可正常显示
        issue_dir = OUTPUT_DIR / f"weekly-{date}"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("newsletter.md", md)
            zf.writestr("newsletter.html", html)
            images_dir = issue_dir / "images"
            if images_dir.is_dir():
                for p in sorted(images_dir.iterdir()):
                    if p.is_file():
                        zf.write(p, f"images/{p.name}")
        buf.seek(0)

        return Response(
            buf.getvalue(),
            mimetype="application/zip",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="weekly-{date}.zip"; '
                    f"filename*=UTF-8''weekly-{date}.zip"
                ),
                "X-Export-Date": date,
            },
        )
    except Exception as exc:
        return jsonify({
            "status": "failed",
            "message": f"导出失败：{exc}",
        }), 500


@app.route("/issues/<issue_id>/<path:filepath>")
def serve_issue_files(issue_id: str, filepath: str):
    if not issue_id.startswith("weekly-"):
        return jsonify({"error": "invalid issue id"}), 404
    root = OUTPUT_DIR / issue_id
    if not root.is_dir():
        return jsonify({"error": "issue not found"}), 404
    return send_from_directory(root, filepath)


if __name__ == "__main__":
    if __name__ == "__main__":
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False
    )



