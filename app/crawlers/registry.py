"""并行抓取各源列表页 / RSS，配置见 config/sources.json。"""
import inspect
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.sources_config import enabled_sources, load_sources_config, resolve_fetcher


def _call_fetcher(source_cfg: dict) -> tuple[str, list]:
    fetcher = resolve_fetcher(source_cfg["fetcher"])
    kwargs: dict = {}
    limit = source_cfg.get("limit")
    if limit is not None:
        sig = inspect.signature(fetcher)
        if "limit" in sig.parameters:
            kwargs["limit"] = limit
    try:
        result = fetcher(**kwargs)
        return source_cfg["name"], result
    except TypeError:
        result = fetcher()
        return source_cfg["name"], result


def fetch_all_lists() -> list:
    """阶段一：多站点并行抓取列表/摘要。"""
    sources = enabled_sources()
    items = []

    workers = min(len(sources), load_sources_config().get("list_workers", 8))

    with ThreadPoolExecutor(max_workers=max(workers, 1)) as executor:
        futures = {
            executor.submit(_call_fetcher, src): src
            for src in sources
        }
        for future in as_completed(futures):
            src = futures[future]
            try:
                name, result = future.result()
                items.extend(result)
                print(f"✅ {name}: {len(result)} 条")
            except Exception as exc:
                print(f"❌ {src['name']} error: {exc}")

    return items


def load_all_sources() -> list:
    """兼容旧调用。"""
    return fetch_all_lists()
