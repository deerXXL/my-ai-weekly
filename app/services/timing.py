"""Pipeline 阶段耗时统计。"""
import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class StageTimer:
    stages: dict[str, float] = field(default_factory=dict)
    _starts: dict[str, float] = field(default_factory=dict)

    @contextmanager
    def stage(self, name: str):
        self._starts[name] = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - self._starts.pop(name, time.perf_counter())
            self.stages[name] = self.stages.get(name, 0.0) + elapsed

    def summary(self) -> str:
        total = sum(self.stages.values())
        lines = ["\n⏱ 耗时分布:"]
        for name, sec in sorted(self.stages.items(), key=lambda x: -x[1]):
            pct = (sec / total * 100) if total else 0
            lines.append(f"  {name:<22} {sec:6.1f}s  ({pct:4.0f}%)")
        lines.append(f"  {'合计':<22} {total:6.1f}s")
        return "\n".join(lines)
