#!/usr/bin/env python3
"""
🎴 TaijiOS API Server · FastAPI + 自动 Swagger UI

安装:
    pip install fastapi "uvicorn[standard]" pydantic

启动:
    python api_server.py
    # 或指定端口: python api_server.py --port 8787

浏览器:
    http://127.0.0.1:8787/docs     ← Swagger UI (对外 API 文档)
    http://127.0.0.1:8787/redoc    ← ReDoc (更精美)
    http://127.0.0.1:8787/         ← 首页
"""
import sys, os, subprocess, pathlib, re, json, argparse

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
except ImportError:
    print("✗ 缺依赖. 跑: pip install fastapi 'uvicorn[standard]' pydantic", file=sys.stderr)
    sys.exit(1)

ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
SOUL = ROOT / "TaijiOS" / "taijios-soul"
HOME_TAIJIOS = pathlib.Path.home() / ".taijios"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

app = FastAPI(
    title="TaijiOS API",
    version="1.1.1",
    description=(
        "TaijiOS 全家桶对外 API · 诸葛亮推演 + 灵魂对话 + 晶体同步 + 共享审核.\n\n"
        "- `/v1/predict` · zhuge-skill 足球推演 (6 爻 + 64 卦 + 孔明亲笔)\n"
        "- `/v1/soul/chat` · taijios-soul 对话 (意图/关系/记忆)\n"
        "- `/v1/sync` · 公共晶体池只读 pull\n"
        "- `/v1/crystals/local` · 本地晶体库\n"
        "- `/v1/heartbeat/last` · 最近心跳日志\n\n"
        "架构: 单向 pull · 无 push 通道 · 隐私合约级保证."
    ),
)


# ─────────────── models ───────────────

class PredictIn(BaseModel):
    match: str = Field(..., description="对阵, 格式 'Home vs Away'", example="Inter vs Cagliari")


class ChatIn(BaseModel):
    message: str = Field(..., description="你对 soul 说的话")
    user_id: str = Field("default_user", description="独立人格 id · 不同 id = 不同记忆")


# ─────────────── endpoints ───────────────

@app.get("/", include_in_schema=False)
def index():
    return HTMLResponse(
        """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>TaijiOS API</title>
<style>body{font-family:-apple-system,sans-serif;max-width:720px;margin:3em auto;padding:0 1em;
background:#0a0f24;color:#e8f1ff;}h1{color:#00f0ff;}a{color:#ffd94a;}
.btn{display:inline-block;margin:8px 10px 8px 0;padding:10px 18px;background:#1a2a4a;
border:1px solid #00f0ff;border-radius:6px;color:#e8f1ff;text-decoration:none;}
.btn:hover{background:#2a3a5a;}</style></head>
<body><h1>🎴 TaijiOS API v1.1.1</h1>
<p>六爻为骨, 晶体为脉. 说不谎是日课.</p>
<p><a class="btn" href="/docs">📖 Swagger UI</a>
<a class="btn" href="/redoc">📄 ReDoc</a>
<a class="btn" href="/health">💓 Health</a></p>
<p style="margin-top:2em;opacity:0.6">零 push 通道 · 单向架构 · 隐私合约级.</p></body></html>""",
        status_code=200,
    )


@app.get("/health", summary="健康检查")
def health():
    return {"status": "ok", "version": "1.1.1", "service": "taijios-api"}


@app.get("/v1/status", summary="系统状态 · 7 repo + 心跳")
def system_status():
    repos = ["zhuge-skill", "TaijiOS", "TaijiOS-Lite", "zhuge-crystals",
             "self-improving-loop", "taijios-landing", "taiji"]
    return {
        "repos": {r: (ROOT / r).exists() for r in repos},
        "env_loaded": (ZHUGE / ".env").exists(),
        "heartbeat_log_exists": (HOME_TAIJIOS / "heartbeat.log").exists(),
        "experience_count": (
            sum(1 for _ in (ZHUGE / "data" / "experience.jsonl").read_text(encoding="utf-8").splitlines())
            if (ZHUGE / "data" / "experience.jsonl").exists() else 0
        ),
        "local_crystals_count": (
            sum(1 for _ in (ZHUGE / "data" / "crystals_local.jsonl").read_text(encoding="utf-8").splitlines())
            if (ZHUGE / "data" / "crystals_local.jsonl").exists() else 0
        ),
    }


@app.post("/v1/predict", summary="诸葛亮足球推演", tags=["zhuge"])
def predict(body: PredictIn):
    r = subprocess.run(
        [sys.executable, str(ZHUGE / "scripts" / "predict.py"), body.match],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, cwd=str(ZHUGE),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    text = ANSI.sub("", (r.stdout or "") + (r.stderr or ""))
    return {"match": body.match, "exit_code": r.returncode, "output": text}


@app.post("/v1/soul/chat", summary="Soul 对话一轮", tags=["soul"])
def soul_chat(body: ChatIn):
    sys.path.insert(0, str(SOUL / "src"))
    try:
        from taijios import Soul
    except ImportError:
        raise HTTPException(500, "taijios-soul 未 pip install -e · 跑 python taijios.py install")
    s = Soul(user_id=body.user_id)
    r = s.chat(body.message)
    return {
        "user_id": body.user_id,
        "interaction_count": r.interaction_count,
        "intent": r.intent,
        "stage": r.stage,
        "frustration": r.frustration,
        "reply": r.reply,
    }


@app.get("/v1/soul/{user_id}", summary="Soul 完整状态", tags=["soul"])
def soul_state(user_id: str):
    sys.path.insert(0, str(SOUL / "src"))
    try:
        from taijios import Soul
    except ImportError:
        raise HTTPException(500, "taijios-soul 未装")
    s = Soul(user_id=user_id)
    return {
        "user_id": user_id,
        "stage": s.stage,
        "backend": s.backend,
        "memory": s._memory.to_dict(),
        "generals": s._council.to_dict(),
    }


@app.post("/v1/sync", summary="拉公共晶体池 (HTTP 只读)", tags=["crystals"])
def sync_crystals():
    r = subprocess.run(
        [sys.executable, str(ZHUGE / "scripts" / "sync.py"), "pull"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, cwd=str(ZHUGE),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return {"exit_code": r.returncode, "output": ANSI.sub("", r.stdout or "")}


@app.get("/v1/crystals/local", summary="本地晶体库", tags=["crystals"])
def list_local_crystals():
    f = ZHUGE / "data" / "crystals_local.jsonl"
    if not f.exists():
        return {"count": 0, "crystals": []}
    crystals = []
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                crystals.append(json.loads(line))
            except Exception:
                pass
    return {"count": len(crystals), "crystals": crystals[:20]}


@app.get("/v1/heartbeat/last", summary="最近 heartbeat 日志", tags=["daemon"])
def heartbeat_last(lines: int = 20):
    log = HOME_TAIJIOS / "heartbeat.log"
    if not log.exists():
        return {"exists": False, "reason": "还没 tick 过 · 跑 python heartbeat.py"}
    all_lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    return {
        "exists": True,
        "total_lines": len(all_lines),
        "recent": all_lines[-lines:],
    }


@app.get("/v1/share/queue", summary="共享队列待审", tags=["crystals"])
def share_queue():
    q = HOME_TAIJIOS / "share_queue"
    if not q.exists():
        return {"batches": 0, "total_crystals": 0, "files": []}
    files = list(q.glob("*.jsonl"))
    total = 0
    for f in files:
        total += sum(1 for line in f.read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "batches": len(files),
        "total_crystals": total,
        "files": [str(f.name) for f in files],
    }


# ─────────────── main ───────────────

def main():
    ap = argparse.ArgumentParser(description="TaijiOS API Server")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("✗ uvicorn 未装. 跑: pip install 'uvicorn[standard]'", file=sys.stderr)
        sys.exit(1)

    print(f"\n🎴 TaijiOS API Server v1.1.1")
    print(f"   Swagger UI: http://{args.host}:{args.port}/docs")
    print(f"   ReDoc:      http://{args.host}:{args.port}/redoc")
    print(f"   首页:        http://{args.host}:{args.port}/")
    print(f"   Ctrl+C 退出\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
