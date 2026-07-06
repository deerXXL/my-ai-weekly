from flask import Flask, render_template, jsonify
import json
from pathlib import Path

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/report")
def api_report():

    report_path = Path("output/weekly_report.json")

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)