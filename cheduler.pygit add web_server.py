[1mdiff --cc web_server.py[m
[1mindex af01b61,aefafd2..0000000[m
[1m--- a/web_server.py[m
[1m+++ b/web_server.py[m
[36m@@@ -1,37 -1,284 +1,284 @@@[m
[31m -"""[m
[31m -AI 周报 Web 服务。[m
[31m -- /             首页[m
[31m -- /api/report   读取最新（或指定）weekly JSON 的前端文章列表[m
[31m -- /api/meta     元数据[m
[31m -- /api/archive  历史归档列表[m
[31m -- /api/collect  异步：跑 pipeline，生成最新周报[m
[31m -- /api/task/<id>查询后台任务状态[m
[31m -- /api/summarize 异步：批量重新生成所有 signal 的摘要[m
[31m -- /api/export   生成完整 Markdown 周报并返回下载链接[m
[31m -- /download/<file> 提供导出文件下载[m
[31m -"""[m
[32m +"""闪联AI周刊 Web 服务：HTML 预览、导出、静态资源。"""[m
[32m+ import threading[m
[32m+ import time[m
[32m+ import traceback[m
[32m+ import uuid[m
  from pathlib import Path[m
[31m -from typing import Any, Dict[m
[32m++from app.services.report_reader import to_frontend_articles[m
  [m
[31m- from flask import Flask, Response, jsonify, request, send_from_directory[m
[31m- [m
[32m+ from flask import ([m
[31m -    Flask, Response, jsonify, render_template,[m
[31m -    request, send_from_directory,[m
[32m++    Flask,[m
[32m++    Response,[m
[32m++    jsonify,[m
[32m++    request,[m
[32m++    send_from_directory,[m
[32m++    render_template,[m
[32m+ )[m
[31m -[m
[31m -from app.services.report_reader import ([m
[31m -    load_latest_report,[m
[31m -    to_frontend_articles,[m
[31m -    find_latest_report_path,[m
[32m +from app.services.export_builder import ([m
[32m +    build_export_html,[m
[32m +    build_export_markdown,[m
[32m +    load_latest_report_dict,[m
  )[m
[31m- from app.services.issue_paths import find_latest_newsletter_html[m
  [m
[31m -app = Flask([m
[31m -    __name__,[m
[31m -    template_folder="templates",[m
[31m -    static_folder="static",[m
[31m -)[m
[32m +app = Flask(__name__)[m
[32m +[m
[32m++[m
[32m++TASKS = {}[m
[32m++[m
[32m++TASK_LOCK = threading.Lock()[m
[32m++[m
[32m+ [m
  BASE_DIR = Path(__file__).resolve().parent[m
  OUTPUT_DIR = BASE_DIR / "output"[m
  [m
[31m -# ============================================================[m
[31m -# 简易后台任务队列（内存版）[m
[31m -# ============================================================[m
[31m -TASKS: Dict[str, Dict[str, Any]] = {}[m
[31m -TASK_LOCK = threading.Lock()[m
[32m++BASE_DIR = Path(__file__).resolve().parent[m
[32m++OUTPUT_DIR = BASE_DIR / "output"[m
[32m+ [m
[32m+ [m
[32m+ def _new_task(name: str) -> str:[m
[32m+     tid = uuid.uuid4().hex[:12][m
[32m+     with TASK_LOCK:[m
[32m+         TASKS[tid] = {[m
[32m+             "id": tid,[m
[32m+             "name": name,[m
[32m+             "status": "running",[m
[32m+             "progress": 0,[m
[32m+             "message": "已启动",[m
[32m+             "started_at": time.time(),[m
[32m+             "result": None,[m
[32m+             "error": None,[m
[32m+         }[m
[32m+     return tid[m
[32m+ [m
[32m+ [m
[32m+ def _update_task(tid: str, **kwargs):[m
[32m+     with TASK_LOCK:[m
[32m+         if tid not in TASKS:[m
[32m+             return[m
[32m+         TASKS[tid].update(kwargs)[m
[32m+ [m
[32m+ [m
[32m+ def _run_collect(tid: str):[m
[32m+     try:[m
[32m+         _update_task(tid, progress=5, message="正在加载数据源…")[m
[32m+         from app.pipeline import run_pipeline[m
[31m -        report = run_pipeline(days=14, mode="practical")[m
[32m++        report = run_pipeline()[m
[32m+         n = len(report.signals or [])[m
[32m+         _update_task([m
[32m+             tid,[m
[32m+             status="success",[m
[32m+             progress=100,[m
[32m+             message=f"采集完成，共 {n} 条信号",[m
[32m+             result={"signal_count": n, "date": report.date},[m
[32m+         )[m
[32m+     except Exception as exc:[m
[32m+         _update_task([m
[32m+             tid,[m
[32m+             status="failed",[m
[32m+             message=f"采集失败：{exc}",[m
[32m+             error=traceback.format_exc(),[m
[32m+         )[m
[32m+ [m
[32m+ [m
[32m+ def _run_summarize(tid: str):[m
[32m+     try:[m
[32m+         import json[m
[32m+         from datetime import datetime[m
[32m+         from app.services.llm_signal import regenerate_signal_card[m
[32m+ [m
[32m+         latest = OUTPUT_DIR / "latest.json"[m
[32m+         if not latest.exists():[m
[32m+             candidates = sorted(OUTPUT_DIR.glob("weekly-*.json"), reverse=True)[m
[32m+             if not candidates:[m
[32m+                 _update_task([m
[32m+                     tid, status="failed",[m
[32m+                     message="未找到可用的 weekly JSON"[m
[32m+                 )[m
[32m+                 return[m
[32m+             latest = candidates[0][m
[32m+ [m
[32m+         _update_task(tid, progress=10, message=f"读取 {latest.name}…")[m
[32m+         with open(latest, "r", encoding="utf-8") as f:[m
[32m+             report = json.load(f)[m
[32m+ [m
[32m+         signals = report.get("signals", [])[m
[32m+         total = len(signals)[m
[32m+         if total == 0:[m
[32m+             _update_task([m
[32m+                 tid, status="failed", message="当前报告无 signal"[m
[32m+             )[m
[32m+             return[m
[32m+ [m
[32m+         updated = 0[m
[32m+         for i, sig in enumerate(signals, 1):[m
[32m+             _update_task([m
[32m+                 tid,[m
[32m+                 progress=10 + int(80 * i / total),[m
[32m+                 message=f"正在整理 {i}/{total}：{sig.get('title','')[:30]}",[m
[32m+             )[m
[32m+             new = regenerate_signal_card(sig)[m
[32m+             sig["signal"] = new["signal"][m
[32m+             sig["insight"] = new["insight"][m
[32m+             sig["category"] = new["category"][m
[32m+             sig["impact"] = new["impact"][m
[32m+             updated += 1[m
[32m+ [m
[32m+         # 重新生成 summary[m
[32m+         top = sorted(signals, key=lambda x: x.get("impact", 0), reverse=True)[:3][m
[32m+         report["summary"] = ([m
[32m+             f"本次整理共刷新 {updated} 条信号。"[m
[32m+             f"重点关注：{' / '.join(t.get('title','') for t in top if t.get('title'))}"[m
[32m+         )[m
[32m+         report["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")[m
[32m+         report.setdefault("date", datetime.now().strftime("%Y-%m-%d"))[m
[32m+ [m
[32m+         with open(latest, "w", encoding="utf-8") as f:[m
[32m+             json.dump(report, f, ensure_ascii=False, indent=2)[m
  [m
[32m+         # 同步 weekly-日期.json[m
[32m+         weekly = OUTPUT_DIR / f"weekly-{report['date']}.json"[m
[32m+         with open(weekly, "w", encoding="utf-8") as f:[m
[32m+             json.dump(report, f, ensure_ascii=False, indent=2)[m
[32m+ [m
[32m+         _update_task([m
[32m+             tid,[m
[32m+             status="success",[m
[32m+             progress=100,[m
[32m+             message=f"摘要整理完成，共刷新 {updated} 条",[m
[32m+             result={"updated": updated, "date": report["date"]},[m
[32m+         )[m
[32m+     except Exception as exc:[m
[32m+         _update_task([m
[32m+             tid,[m
[32m+             status="failed",[m
[32m+             message=f"整理失败：{exc}",[m
[32m+             error=traceback.format_exc(),[m
[32m+         )[m
[32m+ [m
[32m+ [m
[32m+ # ============================================================[m
[32m+ # 路由[m
[32m+ # ============================================================[m
  @app.route("/")[m
  def home():[m
[31m-     html_path = find_latest_newsletter_html()[m
[31m-     if html_path and html_path.exists():[m
[31m-         return Response([m
[31m-             html_path.read_text(encoding="utf-8"),[m
[31m-             mimetype="text/html; charset=utf-8",[m
[31m-         )[m
[32m+     return render_template("index.html")[m
[32m+ [m
[32m+ [m
[32m+ @app.route("/api/report")[m
[32m+ def api_report():[m
[32m+     filename = request.args.get("file")[m
[32m+ [m
[32m+     if filename:[m
[32m+         path = OUTPUT_DIR / filename[m
[32m+         if not path.exists():[m
[32m+             return jsonify({"error": f"文件不存在：{filename}"}), 404[m
[32m+         import json[m
[32m+         with open(path, "r", encoding="utf-8") as f:[m
[32m+             report = json.load(f)[m
[32m+         return jsonify(to_frontend_articles(report))[m
[32m+ [m
[31m -    report = load_latest_report()[m
[32m +    report = load_latest_report_dict()[m
[32m++[m
[32m +    if report is None:[m
[31m-         return Response([m
[31m-             "<html><body><h1>暂无周刊</h1><p>请运行 python main.py 生成</p></body></html>",[m
[31m-             mimetype="text/html; charset=utf-8",[m
[31m-             status=404,[m
[31m-         )[m
[31m-     return Response(build_export_html(report), mimetype="text/html; charset=utf-8")[m
[32m++        return jsonify([])[m
[32m++    [m
[32m++    return jsonify([m
[32m++    report.get("articles", [])[m
[32m++    )[m
[32m+     return jsonify(report.get("articles", []))[m
[32m+ [m
[32m+ [m
[32m+ @app.route("/api/meta")[m
[32m+ def api_meta():[m
[31m -    return jsonify(load_latest_report())[m
[32m++    return jsonify([m
[32m++    load_latest_report_dict() or {}[m
[32m++    )[m
[32m+ [m
[32m+ [m
[32m+ @app.route("/api/archive")[m
[32m+ def api_archive():[m
[32m+     reports = [][m
[32m+     # 按日期升序编号（最旧的 = 第1期）[m
[32m+     files = sorted(OUTPUT_DIR.glob("weekly-*.json"))[m
[32m+     total = len(files)[m
[32m+     for idx, file in enumerate(files, 1):[m
[32m+         try:[m
[32m+             import json[m
[32m+             from datetime import datetime, timedelta[m
[32m+             with open(file, "r", encoding="utf-8") as f:[m
[32m+                 data = json.load(f)[m
[32m+ [m
[32m+             date_str = file.stem.replace("weekly-", "")[m
[32m+ [m
[32m+             # 如果JSON中没有period字段，从文件名日期反推双周区间[m
[32m+             period_start = data.get("period_start", "")[m
[32m+             period_end = data.get("period_end", "")[m
[32m+             if not period_start or not period_end:[m
[32m+                 try:[m
[32m+                     d = datetime.strptime(date_str, "%Y-%m-%d")[m
[32m+                     period_start = period_start or (d - timedelta(days=14)).strftime("%Y-%m-%d")[m
[32m+                     period_end = period_end or date_str[m
[32m+                 except ValueError:[m
[32m+                     pass[m
[32m+ [m
[32m+             # 如果没有issue_number，用反向编号（最新的是第N期）[m
[32m+             issue_number = data.get("issue_number") or (total - idx + 1)[m
[32m+ [m
[32m+             # 兼容旧标题[m
[32m+             title = data.get("title", "")[m
[32m+             if not title or title == "AI Daily Report":[m
[32m+                 title = f"AI双周产品周报 · 第{issue_number}期"[m
[32m+ [m
[32m+             reports.append({[m
[32m+                 "file": file.name,[m
[32m+                 "date": date_str,[m
[32m+                 "title": title,[m
[32m+                 "issue_number": issue_number,[m
[32m+                 "period_start": period_start,[m
[32m+                 "period_end": period_end,[m
[32m+                 "signal_count": len(data.get("signals", [])),[m
[32m+                 "size_kb": round(file.stat().st_size / 1024, 1),[m
[32m+                 "mtime": file.stat().st_mtime,[m
[32m+             })[m
[32m+         except Exception as exc:[m
[32m+             print("archive entry error:", file, exc)[m
[32m+ [m
[32m+     # 降序返回（最新的在前）[m
[32m+     reports.reverse()[m
[32m+     return jsonify(reports)[m
[32m+ [m
[32m+ [m
[32m+ @app.route("/api/collect", methods=["POST"])[m
[32m+ def api_collect():[m
[32m+     tid = _new_task("collect")[m
[32m+     th = threading.Thread(target=_run_collect, args=(tid,), daemon=True)[m
[32m+     th.start()[m
[32m+     return jsonify({[m
[32m+         "status": "started",[m
[32m+         "task_id": tid,[m
[32m+         "message": "采集任务已启动，可在 5–10 分钟后回来查看",[m
[32m+     })[m
[32m+ [m
[32m+ [m
[32m+ @app.route("/api/summarize", methods=["POST"])[m
[32m+ def api_summarize():[m
[32m+     tid = _new_task("summarize")[m
[32m+     th = threading.Thread(target=_run_summarize, args=(tid,), daemon=True)[m
[32m+     th.start()[m
[32m+     return jsonify({[m
[32m+         "status": "started",[m
[32m+         "task_id": tid,[m
[32m+         "message": "摘要整理任务已启动",[m
[32m+     })[m
[32m+ [m
[32m+ [m
[32m+ @app.route("/api/task/<tid>")[m
[32m+ def api_task(tid: str):[m
[32m+     with TASK_LOCK:[m
[32m+         task = TASKS.get(tid)[m
[32m+     if not task:[m
[32m+         return jsonify({"error": "task not found"}), 404[m
[32m+     return jsonify(task)[m
  [m
  [m
  @app.route("/api/export", methods=["POST", "GET"])[m
