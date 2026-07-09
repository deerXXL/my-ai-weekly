"""
AI 周报 Web 服务。
- /             首页
- /api/report   读取最新（或指定）weekly JSON 的前端文章列表
- /api/meta     元数据
- /api/archive  历史归档列表
- /api/collect  异步：跑 pipeline，生成最新周报
- /api/task/<id>查询后台任务状态
- /api/summarize 异步：批量重新生成所有 signal 的摘要
- /api/export   生成完整 Markdown 周报并返回下载链接
- /download/<file> 提供导出文件下载
"""
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict

from flask import (
    Flask, Response, jsonify, render_template,
    request, send_from_directory,
)

from app.services.report_reader import (
    load_latest_report,
    to_frontend_articles,
    find_latest_report_path,
)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

# ============================================================
# 简易后台任务队列（内存版）
# ============================================================
TASKS: Dict[str, Dict[str, Any]] = {}
TASK_LOCK = threading.Lock()


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
        report = run_pipeline(days=14, mode="practical")
        n = len(report.signals or [])
        _update_task(
            tid,
            status="success",
            progress=100,
            message=f"采集完成，共 {n} 条信号",
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

    report = load_latest_report()
    return jsonify(report.get("articles", []))


@app.route("/api/meta")
def api_meta():
    return jsonify(load_latest_report())


@app.route("/api/archive")
def api_archive():
    reports = []
    for file in sorted(OUTPUT_DIR.glob("weekly-*.json"), reverse=True):
        try:
            import json
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
            reports.append({
                "file": file.name,
                "date": file.stem.replace("weekly-", ""),
                "title": data.get("title", ""),
                "issue_number": data.get("issue_number", 0),
                "period_start": data.get("period_start", ""),
                "period_end": data.get("period_end", ""),
                "signal_count": len(data.get("signals", [])),
                "size_kb": round(file.stat().st_size / 1024, 1),
                "mtime": file.stat().st_mtime,
            })
        except Exception as exc:
            print("archive entry error:", file, exc)

    return jsonify(reports)


@app.route("/api/collect", methods=["POST"])
def api_collect():
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
        from app.services.export_builder import (
            build_export_markdown,
            _load_latest,
        )
        report = _load_latest()
        if report is None:
            return jsonify({
                "status": "failed",
                "message": "暂无可导出的周报数据，请先生成",
            }), 400

        content = build_export_markdown(report)
        date = report.get("date", "unknown")

        # 直接以可下载响应返回 Markdown，避免磁盘写权限问题
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


@app.route("/download/<path:filename>")
def download(filename: str):
    return send_from_directory(
        OUTPUT_DIR,
        filename,
        as_attachment=True,
        download_name=filename,
    )


if __name__ == "__main__":
    app.run(debug=True)
