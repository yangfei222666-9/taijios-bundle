#!/usr/bin/env python3
"""
🎴 TaijiOS 文生图 · Seedream 4.5 (Doubao / Volcengine Ark)

用法:
    python imagegen.py --prompt "诸葛亮 八卦 进化大脑" --out my_avatar.png
    python imagegen.py --prompt "..." --size 2048x2048

需要 .env 里:
    ARK_API_KEY=...
    DOUBAO_SEEDREAM_MODEL_ID=...   (默认 doubao-seedream-3-0-t2i-250415)
"""
import os, sys, json, pathlib, urllib.request, urllib.error, argparse, time

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent


def _load_env():
    for p in [ROOT / "zhuge-skill" / ".env", ROOT / ".env"]:
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


def generate(prompt: str, out_path: str = None, size: str = "2048x2048") -> str:
    """生成图 · 返回 output file path.

    坑 #16 (2026-04-19): Seedream 要求**最小 3686400 像素** (约 2048x1800). 小了返 400.
    自动升级到 2048x2048 if 用户传的尺寸不够.
    """
    _load_env()
    key = os.environ.get("ARK_API_KEY", "").strip()
    if not key:
        raise ValueError("✗ 无 ARK_API_KEY · Seedream 需要 · 去 volcengine.com/ark 申请")
    model = os.environ.get("DOUBAO_SEEDREAM_MODEL_ID", "doubao-seedream-3-0-t2i-250415")
    # Size 校验 · 最小 3686400 像素
    try:
        w, h = [int(x) for x in size.lower().split("x")]
        if w * h < 3_686_400:
            print(f"  ⚠ {size} 像素数 {w*h} < 下限 3686400 · 自动升到 2048x2048")
            size = "2048x2048"
    except Exception:
        size = "2048x2048"

    payload = {
        "model": model, "prompt": prompt, "size": size,
        "response_format": "url", "watermark": False,
    }
    req = urllib.request.Request(
        "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_preview = e.read()[:300].decode("utf-8", "replace")
        raise RuntimeError(f"Seedream API HTTP {e.code} · 详情: {body_preview}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"Seedream API 网络/超时错误: {getattr(e, 'reason', e)}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Seedream API 返回非 JSON: {e}")

    if not isinstance(resp, dict) or not resp.get("data"):
        err = resp.get("error", resp) if isinstance(resp, dict) else resp
        raise RuntimeError(f"Seedream API 返回异常 (无 data): {str(err)[:200]}")
    item = resp["data"][0] if resp["data"] else {}
    url = item.get("url")
    if not url:
        raise RuntimeError(f"Seedream API 返回缺 url 字段 · 完整 item: {str(item)[:200]}")

    out = out_path or str(pathlib.Path.home() / ".taijios" / f"imagegen_{int(time.time())}.png")
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, out)
    except Exception as e:
        # URL 仅写到本地 log 不暴露在 message
        import sys as _sys
        print(f"[imagegen] 下载失败 url={url[:80]}...", file=_sys.stderr)
        raise RuntimeError(f"图片下载失败 ({type(e).__name__}): {str(e)[:150]}")

    print(f"  ✓ {time.time()-t0:.1f}s · saved → {out}  ({pathlib.Path(out).stat().st_size//1024} KB)")
    return out


def main():
    ap = argparse.ArgumentParser(description="TaijiOS Seedream 文生图")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--size", default="2048x2048")
    args = ap.parse_args()
    print(f"🎴 Seedream · prompt: {args.prompt[:100]}")
    generate(args.prompt, args.out, args.size)


if __name__ == "__main__":
    main()
