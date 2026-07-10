"""闪联AI周刊 Web 服务：HTML 预览、导出、静态资源。"""
import threading
import time
import traceback
import uuid
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

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"


def _new_task(name: str) -> str:
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
    return tid


def _update_task(tid: str, **kwargs):
    with TASK_LOCK:
        if tid not in TASKS:
            return
        TASKS[tid].update(kwargs)


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
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/report")
def api_report():
    filename = request.args.get("file")

    if filename:
        path = OUTPUT_DIR / filename
        if not path.exists():
            return jsonify({"error": f"文件不存在：{filename}"}), 404
        import json
        with open(path, "r", encoding="utf-8") as f:
            report = json.load(f)
        return jsonify(to_frontend_articles(report))

    report = load_latest_report_dict()

    if report is None:
        return jsonify([])

    # 如果 report 已经是 report_reader 处理过的（有 articles 字段），直接返回
    if "articles" in report:
        return jsonify(report["articles"])

    # 否则走 to_frontend_articles 转换（兼容 signals 和 industry_news 两种格式）
    return jsonify(to_frontend_articles(report))


@app.route("/api/meta")
def api_meta():
    report = load_latest_report_dict()
    if report is None:
        return jsonify({})
    # 前端需要: title, period_start, period_end, date
    return jsonify({
        "title": report.get("title") or report.get("brand_name", ""),
        "date": report.get("date") or (report.get("generated_at") or "")[:10],
        "period_start": report.get("period_start", ""),
        "period_end": report.get("period_end", ""),
        "issue_number": report.get("issue_number", 0),
    })


@app.route("/api/archive")
def api_archive():
    reports = []
    # 按日期升序编号（最旧的 = 第1期）
    files = sorted(OUTPUT_DIR.glob("weekly-*.json"))
    total = len(files)
    for idx, file in enumerate(files, 1):
        try:
            import json
            from datetime import datetime, timedelta
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            date_str = file.stem.replace("weekly-", "")

            # 如果JSON中没有period字段，从文件名日期反推双周区间
            period_start = data.get("period_start", "")
            period_end = data.get("period_end", "")
            if not period_start or not period_end:
                try:
                    d = datetime.strptime(date_str, "%Y-%m-%d")
                    period_start = period_start or (d - timedelta(days=14)).strftime("%Y-%m-%d")
                    period_end = period_end or date_str
                except ValueError:
                    pass

            # 如果没有issue_number，用反向编号（最新的是第N期）
            issue_number = data.get("issue_number") or (total - idx + 1)

            # 兼容旧标题
            title = data.get("title", "")
            if not title or title == "AI Daily Report":
                title = f"AI双周产品周报 · 第{issue_number}期"

            reports.append({
                "file": file.name,
                "date": date_str,
                "title": title,
                "issue_number": issue_number,
                "period_start": period_start,
                "period_end": period_end,
                "signal_count": len(data.get("signals", [])),
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
    today_report = OUTPUT_DIR / f"weekly-{today}.json"
    if today_report.exists():
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
    if not task:
        return jsonify({"error": "task not found"}), 404
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

        fmt = request.args.get("format", "md").lower()
        date = (report.get("generated_at") or "unknown")[:10]

        if fmt == "html":
            content = build_export_html(report)
            return Response(
                content,
                mimetype="text/html; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="weekly-{date}.html"; '
                        f"filename*=UTF-8''weekly-{date}.html"
                    ),
                },
            )

        content = build_export_markdown(report)
        return Response(
            content,
            mimetype="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="weekly-{date}.md"; '
                    f"filename*=UTF-8''weekly-{date}.md"
                ),
                "X-Export-Date": date,
                "X-Export-Size": str(len(content.encode("utf-8"))),
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
    app.run(debug=True)
