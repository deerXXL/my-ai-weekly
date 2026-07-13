"""抓取源配置加载。"""
import importlib
import json
from pathlib import Path
from typing import Any, Callable

from config import BASE_DIR

SOURCES_CONFIG_PATH = BASE_DIR / "config" / "sources.json"

_config_cache: dict | None = None


def load_sources_config() -> dict:
    global _config_cache
    if _config_cache is None:
        with open(SOURCES_CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
    return _config_cache


def reload_sources_config() -> dict:
    global _config_cache
    _config_cache = None
    return load_sources_config()


def enabled_sources() -> list[dict]:
    cfg = load_sources_config()
    sources = [s for s in cfg.get("sources", []) if s.get("enabled", True)]
    # 国内源优先，同区域内按 weight 降序
    sources.sort(
        key=lambda s: (
            0 if s.get("region") == "domestic" else 1,
            -int(s.get("weight", 5)),
        )
    )
    return sources


def domestic_source_names() -> set[str]:
    return {
        s["name"]
        for s in load_sources_config().get("sources", [])
        if s.get("region") == "domestic"
    }


def source_weights() -> dict[str, int]:
    return {
        s["name"]: int(s.get("weight", 5))
        for s in load_sources_config().get("sources", [])
    }


def source_enrich_flags() -> dict[str, bool]:
    return {
        s["name"]: bool(s.get("enrich_detail", True))
        for s in load_sources_config().get("sources", [])
    }


def resolve_fetcher(fetcher_path: str) -> Callable:
    """fetcher_path 格式：app.crawlers.module:function"""
    module_path, func_name = fetcher_path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)
