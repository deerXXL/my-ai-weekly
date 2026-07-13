"""带端到端墙钟计时的 pipeline 运行脚本（不启动 Web 服务）。"""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: F401
from app.pipeline import run_pipeline

print("=" * 50)
print("闪联AI周刊 — 性能测试运行")
print("开始时间:", datetime.now().strftime("%H:%M:%S"))
print("=" * 50)

wall_start = time.perf_counter()
newsletter = run_pipeline()
wall_elapsed = time.perf_counter() - wall_start

print("\n" + "=" * 50)
print("性能汇总")
print("=" * 50)
print(f"  端到端墙钟耗时: {wall_elapsed:.1f}s ({wall_elapsed / 60:.1f} 分钟)")
print(f"  行业动态: {len(newsletter.industry_news)} 条")
print(f"  结束时间: {datetime.now().strftime('%H:%M:%S')}")
