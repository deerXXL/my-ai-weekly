"""闪联AI周刊 Web 服务：HTML 预览、导出、静态资源。"""
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory

from app.services.export_builder import (
    build_export_html,
    build_export_markdown,
    load_latest_report_dict,
)
from app.services.issue_paths import find_latest_newsletter_html

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"


@app.route("/")
def home():
    html_path = find_latest_newsletter_html()
    if html_path and html_path.exists():
        return Response(
            html_path.read_text(encoding="utf-8"),
            mimetype="text/html; charset=utf-8",
        )
    report = load_latest_report_dict()
    if report is None:
        return Response(
            "<html><body><h1>暂无周刊</h1><p>请运行 python main.py 生成</p></body></html>",
            mimetype="text/html; charset=utf-8",
            status=404,
        )
    return Response(build_export_html(report), mimetype="text/html; charset=utf-8")


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
