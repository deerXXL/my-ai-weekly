import time
import subprocess
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "output"

LOG_FILE = BASE_DIR / "scheduler.log"

def log(msg):

    print(msg)

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            f"{datetime.now()} {msg}\n"
        )

def get_latest_report_date():

    files = list(
        OUTPUT_DIR.glob(
            "weekly-*.json"
        )
    )


    if not files:
        return None


    latest = max(
        files,
        key=lambda x:x.stat().st_mtime
    )


    date_str = (
        latest.stem
        .replace(
            "weekly-",
            ""
        )
    )


    return datetime.strptime(
        date_str,
        "%Y-%m-%d"
    )



def need_generate():

    latest_date = get_latest_report_date()


    if latest_date is None:
        return True


    today = datetime.now()


    days = (
        today - latest_date
    ).days


    print(
        f"距离上次报告:{days}天"
    )


    return days >= 14



def run_report():

    print(
        "🚀 开始生成AI双周报告..."
    )


    result = subprocess.run(
        [
            "python",
             str(
                BASE_DIR / "generate_weekly.py"
             )
        ],
        capture_output=True,
        text=True
    )


    if result.returncode == 0:

        print(
            "✅ 报告生成完成"
        )

    else:

        print(
            "❌ 报告生成失败"
        )

        print(
            result.stderr
        )



def scheduler():

    print(
        "⏰ AI双周调度启动"
    )


    while True:


        if need_generate():

            run_report()

        else:

            print(
                "未达到14天周期，等待..."
            )


        # 每天检查一次

        time.sleep(
            60 * 60 * 24
        )



if __name__=="__main__":

    scheduler()