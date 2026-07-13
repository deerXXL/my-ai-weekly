"""HTTP 抓取公共配置。"""
import os

import requests

from config import USE_HTTP_PROXY

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_session: requests.Session | None = None


def get_http_session() -> requests.Session:
    """共享 Session。默认直连；需代理时在 .env 设置 AI_WEEKLY_USE_PROXY=1。"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.trust_env = USE_HTTP_PROXY
        _session.headers.update(DEFAULT_HEADERS)
        if USE_HTTP_PROXY:
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
            if proxy:
                print("  [http] 使用代理:", proxy)
            else:
                print("  [http] 已开启 AI_WEEKLY_USE_PROXY，但未设置 HTTP_PROXY/HTTPS_PROXY")
    return _session
