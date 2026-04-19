#!/usr/bin/env python3
"""
🎴 TaijiOS Embedding · 给晶体池做语义检索 (让孔明真从过往经验里找相关的)

Doubao Embedding 4096 维 · 中文语义强 · 给 experience.jsonl / crystals 索引.

用法:
    from embed import embed_text, semantic_search
    vec = embed_text("Inter vs Cagliari 大胜")
    top = semantic_search("足球 主胜 大球", k=3)
"""
import os, sys, json, pathlib, urllib.request, urllib.error

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


def embed_text(text: str) -> list:
    """调 Doubao Embedding · 返回 4096 维向量. 无 key 返 []."""
    key = os.environ.get("ARK_API_KEY", "").strip()
    if not key:
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
    except Exception:
        return []


def _cosine(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    s = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return s / (na * nb + 1e-9)


def semantic_search(query: str, k: int = 3, pool: str = "experience") -> list:
    """在 experience.jsonl 或 crystals_local.jsonl 里语义搜 top-k.

    Returns [(score, record_dict)] · 无 ARK key 时返 []."""
    q_vec = embed_text(query)
    if not q_vec:
        return []
    path = ZHUGE / "data" / ("experience.jsonl" if pool == "experience" else "crystals_local.jsonl")
    if not path.exists():
        return []
    results = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        # 对每条记录组装 searchable text
        text = json.dumps(rec, ensure_ascii=False)[:500]
        vec = embed_text(text)
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
