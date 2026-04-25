#!/usr/bin/env python3
"""
🎴 TaijiOS Vision · 孔明看图说话

自动选 vision provider (优先顺序):
  1. Claude (ANTHROPIC_API_KEY)     · claude-sonnet-4-6 · 最强
  2. Doubao Vision (ARK_API_KEY)    · doubao-1-5-vision-pro
  3. OpenAI (OPENAI_API_KEY)        · gpt-4o
  4. Kimi (KIMI_API_KEY)            · moonshot-v1-8k-vision-preview

用法:
    python vision.py --image path.png --question "这是什么?"
    python vision.py --image snap.jpg --question "诊断这个截图有什么问题?"
    cat image.png | base64 | python vision.py --question "..." --stdin-b64

支持图片格式: PNG / JPEG / GIF / WEBP
"""
import os, sys, json, base64, pathlib, argparse, urllib.request, urllib.error

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent


def _load_env():
    """Load zhuge-skill/.env so keys are picked up."""
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


_load_env()


def _detect_media_type(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff" or data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"GIF8":
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"  # fallback


def _call_claude(img_b64: str, media_type: str, question: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY 未设置 · 无法用 Claude vision · 在 .env 加: ANTHROPIC_API_KEY=sk-ant-...")
    payload = {
        "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                {"type": "text", "text": question},
            ],
        }],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["content"][0]["text"]


def _call_openai_compat(img_b64: str, media_type: str, question: str,
                       base: str, key: str, model: str) -> str:
    """OpenAI 兼容 vision · GPT-4o / Doubao / Kimi / 通义 vision."""
    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{img_b64}"}},
                {"type": "text", "text": question},
            ],
        }],
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def analyze_image(image_path: str, question: str, provider: str = None) -> tuple:
    """主 API · 返回 (provider_used, answer_text)."""
    img_data = pathlib.Path(image_path).read_bytes()
    img_b64 = base64.b64encode(img_data).decode()
    mt = _detect_media_type(img_data)

    providers = [
        ("claude", "ANTHROPIC_API_KEY", None, None, None),
        ("doubao", "ARK_API_KEY",
         "https://ark.cn-beijing.volces.com/api/v3",
         os.environ.get("DOUBAO_VISION_MODEL_ID", "doubao-1-5-vision-pro-32k-250115"),
         None),
        ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1", "gpt-4o", None),
        ("kimi",   "KIMI_API_KEY",
         "https://api.moonshot.cn/v1", "moonshot-v1-8k-vision-preview", None),
    ]

    errors = []
    for name, env_key, base, model, _ in providers:
        if provider and provider != name:
            continue
        key = os.environ.get(env_key, "").strip()
        if not key:
            if provider == name:
                return (name, f"✗ {env_key} 未设置 · 无法使用指定 vision provider: {name}")
            continue
        try:
            if name == "claude":
                return (name, _call_claude(img_b64, mt, question))
            return (name, _call_openai_compat(img_b64, mt, question, base, key, model))
        except urllib.error.HTTPError as e:
            body = e.read()[:200].decode("utf-8", errors="replace")
            msg = f"(HTTP {e.code}): {body}"
        except Exception as e:
            msg = f"(err: {type(e).__name__}: {e})"
        if provider:
            return (name, msg)
        errors.append(f"{name}: {msg}")

    if errors:
        return ("none", "✗ vision providers all failed: " + " | ".join(errors))
    return ("none", "✗ 无 vision key. 需要 ANTHROPIC_API_KEY / ARK_API_KEY / OPENAI_API_KEY / KIMI_API_KEY 之一 (DeepSeek 暂不支持 vision).")


def main():
    ap = argparse.ArgumentParser(description="TaijiOS Vision · 看图说话")
    ap.add_argument("--image", required=True, help="图片路径")
    ap.add_argument("--question", default="孔明, 此图何解?", help="问孔明什么")
    ap.add_argument("--provider", default=None, help="强制 provider (claude/doubao/openai/kimi)")
    args = ap.parse_args()

    if not pathlib.Path(args.image).exists():
        print(f"✗ 图片不存在: {args.image}", file=sys.stderr)
        sys.exit(1)

    print(f"🎴 看图: {args.image}")
    print(f"   问: {args.question}")
    prov, answer = analyze_image(args.image, args.question, args.provider)
    print(f"   provider: {prov}")
    print()
    print("━━━━━━━━━━━━━━ 孔明所见 ━━━━━━━━━━━━━━")
    print(answer)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
