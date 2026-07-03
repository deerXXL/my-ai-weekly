import time
import subprocess
from datetime import datetime


def run_report():
    print("\n🚀 运行AI日报系统...\n")

    result = subprocess.run(
        ["python", "run_test.py"],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.stderr:
        print("❌ 错误：")
        print(result.stderr)


def main():
    print("⏰ AI日报定时系统启动成功")

    while True:
        now = datetime.now()

        # 🕘 每天 9:00 运行
        if now.hour == 9 and now.minute == 0:
            run_report()
            time.sleep(60)  # 防止重复执行

        time.sleep(10)


if __name__ == "__main__":
    main()