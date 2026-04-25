#!/usr/bin/env python3
"""
🎴 TaijiOS Embedding · 给晶体池做语义检索 (让孔明真从过往经验里找相关的)

Doubao Embedding 4096 维 · 中文语义强 · 给 experience.jsonl / crystals 索引.

用法:
    from embed import embed_text, semantic_search
    vec = embed_text("Inter vs Cagliari 大胜")
    top = semantic_search("足球 主胜 大球", k=3)
"""
import os, sys, json, pathlib, urllib.request, urllib.error, hashlib

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
CACHE = pathlib.Path.home() / ".taijios" / "embed_cache.jsonl"


def _load_env():
    for p in [ZHUGE / ".env", ROOT / ".env"]:
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if k and v and k not in os.environ:
                    os.environ[k] = v
            return


_load_env()

_MISSING_KEY_WARNED = False


def embed_text(text: str) -> list:
    """调 Doubao Embedding · 返回 4096 维向量. 无 key 返 []."""
    global _MISSING_KEY_WARNED
    key = os.environ.get("ARK_API_KEY", "").strip()
    if not key:
        if not _MISSING_KEY_WARNED:
            print("[embed.py] ARK_API_KEY 未设置 · embedding disabled; returning []", file=sys.stderr)
            _MISSING_KEY_WARNED = True
        return []
    model = os.environ.get("DOUBAO_EMB_MODEL", "doubao-embedding-large-text-240915")
    payload = {"model": model, "input": [text]}
    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/embeddings",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["data"][0]["embedding"]
    except urllib.error.HTTPError as e:
        # 不 print response body 避免泄露 token / 错误细节; 仅 code + 类型
        print(f"[embed.py] Doubao Embedding HTTP {e.code} (body redacted)", file=sys.stderr)
        return []
    except urllib.error.URLError as e:
        print(f"[embed.py] Doubao Embedding 网络错误: {e.reason}", file=sys.stderr)
        return []
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"[embed.py] Doubao Embedding 返回格式异常: {type(e).__name__}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[embed.py] Doubao Embedding 未知错误: {type(e).__name__}", file=sys.stderr)
        return []


def _cosine(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    s = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return s / (na * nb + 1e-9)


def _text_hash(text: str) -> str:
    """sha256 全 hex (不截) · 防止 audit 报的"截短哈希冲突"风险."""
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


_CACHE_SIZE_WARN_BYTES = 50 * 1024 * 1024  # 50MB warn threshold (cache 无 LRU · 长期跑大需手动清)


def _cache_load() -> dict:
    """Load embed cache from CACHE jsonl. Returns {hash: vec}.

    Cache 无 expiry 也无 LRU · 长期运行需手动 rm ~/.taijios/embed_cache.jsonl 重建.
    Single-process 安全 · 多进程并发写未做锁 (POSIX O_APPEND 大多场景 atomic, Windows
    一般也 OK 但不保证) · 多 worker 场景应改用 sqlite 或加 portalocker 锁 (P3 优化)."""
    if not CACHE.exists():
        return {}
    if CACHE.stat().st_size > _CACHE_SIZE_WARN_BYTES:
        print(f"[embed.py] cache size {CACHE.stat().st_size//1024//1024} MB · 超 50MB · 建议清: rm {CACHE}", file=sys.stderr)
    out = {}
    for line in CACHE.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            out[d["h"]] = d["v"]
        except Exception:
            continue
    return out


def _cache_append(text_hash: str, vec: list) -> None:
    """Append-only · 单行一个记录 · 后续 _cache_load 后写胜出."""
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"h": text_hash, "v": vec}) + "\n")


def semantic_search(query: str, k: int = 3, pool: str = "experience") -> list:
    """在 experience.jsonl 或 crystals_local.jsonl 里语义搜 top-k.

    用 ~/.taijios/embed_cache.jsonl 做 cache · 第二次跑同样 record ≈ 0 API call · 仅 cosine.
    避免原 N+1 灾难 (10 条 record = 11 次 API; 1000 条 = 1001 次).

    Returns [(score, record_dict)] · 无 ARK key 或池空返 []."""
    q_vec = embed_text(query)
    if not q_vec:
        return []
    path = ZHUGE / "data" / ("experience.jsonl" if pool == "experience" else "crystals_local.jsonl")
    if not path.exists():
        return []

    cache = _cache_load()
    results = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        text = json.dumps(rec, ensure_ascii=False)[:500]
        h = _text_hash(text)
        vec = cache.get(h)
        if vec is None:
            vec = embed_text(text)
            if vec:
                cache[h] = vec
                _cache_append(h, vec)
        if vec:
            results.append((_cosine(q_vec, vec), rec))
    results.sort(key=lambda x: -x[0])
    return results[:k]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--pool", default="experience", choices=["experience", "crystals"])
    args = ap.parse_args()
    res = semantic_search(args.query, args.k, args.pool)
    if not res:
        print("(无结果 · 可能无 ARK_API_KEY 或池为空)")
    for score, rec in res:
        print(f"  {score:.3f}  {json.dumps(rec, ensure_ascii=False)[:200]}")
