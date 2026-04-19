"""
firecrawl_adapter · Firecrawl v1 API adapter for TaijiOS

让 agent 主动采集网页 → 结晶到 crystal pool. 闭合 self-improving-loop 的"主动探索"环.

Env:
    FIRECRAWL_API_KEY  必填. 注册 https://firecrawl.dev free tier (500 credits)
    FIRECRAWL_API_BASE 可选. default https://api.firecrawl.dev

三个主功能:
    scrape(url)    → markdown + metadata (单页, 1 credit)
    crawl(url)     → 整站 (多页 · credit 按页计)
    search(query)  → web search (需 search 权限)

设计:
    · 所有 API 错误带 trace_id (§5.3 provenance)
    · FirecrawlError hierarchy: Missing/Auth/Quota/Network
    · Rate-limit 友好: 自动读 Retry-After header
    · 结果可直接 pipe 到 zhuge-skill crystallizer
"""
from __future__ import annotations
import os
import json
import time
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Any

__all__ = ["scrape", "crawl", "search", "FirecrawlError",
           "MissingKeyError", "QuotaExceededError"]


class FirecrawlError(RuntimeError):
    def __init__(self, message: str, trace_id: str, code: Optional[int] = None):
        super().__init__(f"{message} (trace_id={trace_id})")
        self.trace_id = trace_id
        self.code = code


class MissingKeyError(FirecrawlError):
    pass


class QuotaExceededError(FirecrawlError):
    def __init__(self, message: str, trace_id: str, retry_after_s: Optional[int]):
        super().__init__(message, trace_id, code=429)
        self.retry_after_s = retry_after_s


def _load_env_file() -> dict:
    """Drift-safe .env load (same logic as whisper_stt · don't rely on os.environ)."""
    candidates = []
    ex = os.environ.get("TAIJIOS_ENV_FILE", "").strip()
    if ex:
        candidates.append(Path(ex))
    candidates.append(Path(r"G:/taijios_full_workspace/.env"))
    candidates.append(Path.home() / ".taijios" / ".env")
    for p in candidates:
        if p and p.is_file():
            out = {}
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    out[k.strip()] = v.strip().strip('"').strip("'")
            return out
    return {}


def _resolve_key() -> str:
    for src in (os.environ.get("FIRECRAWL_API_KEY", "").strip(),
                _load_env_file().get("FIRECRAWL_API_KEY", "").strip()):
        if src:
            return src
    raise MissingKeyError(
        "FIRECRAWL_API_KEY not set. Register at https://firecrawl.dev (free tier · 500 credits), "
        "then add to G:/taijios_full_workspace/.env: FIRECRAWL_API_KEY=fc-...",
        trace_id=f"firecrawl-no-key-{uuid.uuid4().hex[:8]}",
    )


def _base_url() -> str:
    return os.environ.get("FIRECRAWL_API_BASE", "https://api.firecrawl.dev").rstrip("/")


def _post(path: str, body: dict, timeout: int = 120) -> dict:
    trace_id = f"firecrawl-{uuid.uuid4().hex[:12]}"
    key = _resolve_key()
    url = _base_url() + path
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Trace-Id": trace_id,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", "replace")[:400]
        retry_after = e.headers.get("Retry-After")
        retry_after_s = int(retry_after) if retry_after and retry_after.isdigit() else None
        if e.code == 401:
            raise FirecrawlError(f"auth failed: {body_err}", trace_id=trace_id, code=401) from None
        if e.code == 429:
            raise QuotaExceededError(f"rate-limited: {body_err}", trace_id=trace_id,
                                     retry_after_s=retry_after_s) from None
        raise FirecrawlError(f"HTTP {e.code}: {body_err}", trace_id=trace_id, code=e.code) from None
    except Exception as e:
        raise FirecrawlError(f"{type(e).__name__}: {str(e)[:200]}", trace_id=trace_id) from None


def scrape(url: str, formats: list[str] = None, only_main: bool = True,
           timeout: int = 120) -> dict:
    """Scrape a single URL → markdown (metadata is always returned alongside). 1 credit.

    Valid formats: markdown / html / rawHtml / links / screenshot /
                   screenshot@fullPage / extract / json / summary /
                   changeTracking / branding
    """
    return _post("/v1/scrape", {
        "url": url,
        "formats": formats or ["markdown"],
        "onlyMainContent": only_main,
    }, timeout=timeout)


def crawl(url: str, limit: int = 10, include_paths: list[str] = None,
          exclude_paths: list[str] = None, timeout: int = 300) -> dict:
    """Crawl an entire site (async on Firecrawl side). Returns job id · poll status."""
    body: dict[str, Any] = {"url": url, "limit": limit}
    if include_paths:
        body["includePaths"] = include_paths
    if exclude_paths:
        body["excludePaths"] = exclude_paths
    return _post("/v1/crawl", body, timeout=timeout)


def search(query: str, limit: int = 5, timeout: int = 60) -> dict:
    """Search the web. Requires search-enabled plan."""
    return _post("/v1/search", {"query": query, "limit": limit}, timeout=timeout)


# ────────────────── CLI smoke ──────────────────

if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser(description="Firecrawl smoke test")
    ap.add_argument("mode", choices=["scrape", "search"], help="scrape|search")
    ap.add_argument("target", help="URL for scrape, query for search")
    args = ap.parse_args()
    try:
        if args.mode == "scrape":
            r = scrape(args.target)
            data = r.get("data", {})
            md = data.get("markdown") or data.get("content") or ""
            print(f"title: {data.get('metadata', {}).get('title')}")
            print(f"markdown length: {len(md)}")
            print(f"head:\n{md[:300]}")
        else:
            r = search(args.target)
            for i, item in enumerate(r.get("data", []), 1):
                print(f"{i}. {item.get('title')} — {item.get('url')}")
    except MissingKeyError as e:
        print(f"SETUP NEEDED: {e}")
        sys.exit(2)
    except QuotaExceededError as e:
        print(f"QUOTA: {e} (retry_after={e.retry_after_s}s)")
        sys.exit(3)
    except FirecrawlError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
