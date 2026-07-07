from flask import Flask, jsonify, render_template

from app.services.report_reader import load_latest_report

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/report")
def api_report():
    report = load_latest_report()
    return jsonify(report["articles"])


@app.route("/api/meta")
def api_meta():
    return jsonify(load_latest_report())


if __name__ == "__main__":
    app.run(debug=True)
