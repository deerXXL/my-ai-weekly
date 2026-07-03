from flask import Flask, render_template

from app.pipeline import run_pipeline

app = Flask(__name__)


@app.route("/")
def home():
    report = run_pipeline()

    return render_template(
        "index.html",
        summary=report.summary,
        signals=report.signals[:10]
    )


if __name__ == "__main__":
    app.run(debug=True)