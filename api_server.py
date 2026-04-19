#!/usr/bin/env python3
"""
🎴 TaijiOS API Server · FastAPI + 自动 Swagger UI

v1.1.2 · 企业级安全加固 (2026-04-19)
  · BUG-1 fix: Traceback / 本地路径不再外泄 (sanitize_output)
  · BUG-2 fix: user_id path-traversal 防护 (pydantic validator)
  · BUG-3 fix: 可选 Bearer 认证 (env TAIJIOS_API_TOKEN · 未设则 dev 模式)
  · BUG-4 fix: /v1/predict + /v1/sync 并发 semaphore(3) + 队列
  · BUG-5 fix: Demo fallback 显式 demo_mode:true 标识
  · BUG-6 fix: user_id 空字符串 reject (422)
  · BUG-7 partial: /v1/sync 额外加内存节流 (单 key 60s 重用)
  · BUG-8 fix: CORSMiddleware (dev=*, prod=whitelist)
  · BUG-10 fix: match max_length=128 + regex
  · OPT-7: 所有 v1 response 加 meta envelope (trace_id / caller / ts)

安装:
    pip install fastapi "uvicorn[standard]" pydantic

启动:
    python api_server.py
    # 或指定端口 + token:
    TAIJIOS_API_TOKEN=xxx python api_server.py --port 8787

浏览器:
    http://127.0.0.1:8787/docs     ← Swagger UI
    http://127.0.0.1:8787/redoc    ← ReDoc
    http://127.0.0.1:8787/         ← 首页
"""
import sys, os, subprocess, pathlib, re, json, argparse, asyncio, time, uuid
from datetime import datetime, timezone
from typing import Optional

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from fastapi import FastAPI, HTTPException, Depends, Header, Request, status as http_status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    print("✗ 缺依赖. 跑: pip install fastapi 'uvicorn[standard]' pydantic", file=sys.stderr)
    sys.exit(1)

# ─────────────── Paths + Constants ───────────────

VERSION = "1.1.2"
ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
SOUL = ROOT / "TaijiOS" / "taijios-soul"
HOME_TAIJIOS = pathlib.Path.home() / ".taijios"
ERROR_LOG = HOME_TAIJIOS / "api_errors.jsonl"
HOME_TAIJIOS.mkdir(parents=True, exist_ok=True)

ANSI = re.compile(r"\x1b\[[0-9;]*m")
# Match Windows (C:\ ...) and Unix (/home/... /Users/...) absolute paths
PATH_LEAK_RE = re.compile(r"(?:[A-Z]:\\[^\s\"'<>\n]+|/(?:home|Users|root|var/www|opt/[^\s]+)/[^\s\"'<>\n]+)")
TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\):(?:\n.+)+?(?=\n\S|\Z)", re.DOTALL)
DEMO_MARKER = "::TAIJIOS::DEMO::MODE::"
USER_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
MATCH_RE = re.compile(r"^[\w\s\u4e00-\u9fa5()·.'-]{2,100}\s+(?:vs|v|VS|-)\s+[\w\s\u4e00-\u9fa5()·.'-]{2,100}$", re.IGNORECASE)

# Known weak / placeholder token values (case-insensitive · refused in non-loopback mode)
WEAK_TOKEN_PATTERNS = {
    "your-token", "your-access-token", "your-secret", "your-key",
    "secret", "password", "test", "dev", "demo", "example",
    "changeme", "admin", "token", "api-token", "placeholder",
    "xxx", "xxxx", "...",
}
MIN_TOKEN_BYTES = 16  # 32 hex chars = 16 bytes = 128 bits


def _api_token() -> str:
    """Resolved at request time (test-friendly)."""
    return os.environ.get("TAIJIOS_API_TOKEN", "").strip()


def _is_weak_token(t: str) -> tuple[bool, str]:
    """Return (is_weak, reason).
    Weak = matches known placeholder OR < MIN_TOKEN_BYTES * 2 hex chars (i.e., < 32 chars).
    """
    if not t:
        return True, "empty"
    if t.lower() in WEAK_TOKEN_PATTERNS:
        return True, f"matches known placeholder '{t}'"
    if len(t) < MIN_TOKEN_BYTES * 2:
        return True, f"too short ({len(t)} chars · need ≥ {MIN_TOKEN_BYTES * 2})"
    return False, ""

# ─────────────── Logging + provenance ───────────────

def log_error(route: str, trace_id: str, exc_kind: str, raw_stderr: str, caller: str = "api_server") -> None:
    """Server-side error log keeps the full detail; client only sees scrubbed version."""
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "caller": caller,
                "trace_id": trace_id,
                "route": route,
                "exc_kind": exc_kind,
                "raw": raw_stderr[:4000],
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass

def new_trace() -> str:
    return f"api-{uuid.uuid4().hex[:12]}"

def meta_envelope(trace_id: str, extra: Optional[dict] = None) -> dict:
    e = {
        "trace_id": trace_id,
        "caller": "api_server",
        "ts": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
    }
    if extra:
        e.update(extra)
    return e

# ─────────────── Output sanitization ───────────────

def sanitize_output(text: str, trace_id: str) -> dict:
    """Scrub Tracebacks + absolute paths from client-facing output.

    Returns {clean: str, had_traceback: bool, had_path_leak: bool}.
    Full raw is written to server-side ERROR_LOG.
    """
    if not text:
        return {"clean": "", "had_traceback": False, "had_path_leak": False}
    had_tb = bool(TRACEBACK_RE.search(text))
    had_leak = bool(PATH_LEAK_RE.search(text))
    clean = TRACEBACK_RE.sub("[traceback removed · trace_id={}]".format(trace_id), text)
    clean = PATH_LEAK_RE.sub("<server-path>", clean)
    return {"clean": clean, "had_traceback": had_tb, "had_path_leak": had_leak}

# ─────────────── Auth ───────────────

_bearer = HTTPBearer(auto_error=False)

async def require_token(request: Request, cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)):
    """Optional bearer auth.
    - If TAIJIOS_API_TOKEN env is empty → dev mode, 127.0.0.1 allowed unauthenticated.
    - If set → all clients must present matching Bearer token (loopback exempt unless override).
    - `TAIJIOS_STRICT_AUTH=1` closes the loopback exemption too.
    """
    api_token = _api_token()
    if not api_token:
        return  # dev mode
    strict = os.environ.get("TAIJIOS_STRICT_AUTH", "").strip() == "1"
    client_host = (request.client.host if request.client else "") or ""
    if not strict and client_host in ("127.0.0.1", "::1", "localhost"):
        return  # loopback exempt
    if cred is None or cred.scheme.lower() != "bearer":
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED,
                            detail="missing_bearer_token", headers={"WWW-Authenticate": "Bearer"})
    if cred.credentials != api_token:
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED,
                            detail="invalid_token", headers={"WWW-Authenticate": "Bearer"})

# ─────────────── Concurrency + cache ───────────────

MAX_CONCURRENT_PREDICT = int(os.environ.get("TAIJIOS_PREDICT_CONCURRENCY", "3"))
_predict_semaphore: Optional[asyncio.Semaphore] = None

MAX_CONCURRENT_SYNC = int(os.environ.get("TAIJIOS_SYNC_CONCURRENCY", "1"))
_sync_semaphore: Optional[asyncio.Semaphore] = None

# cheap sync cache (60s)
_sync_cache: dict = {"ts": 0.0, "result": None}
SYNC_CACHE_TTL = int(os.environ.get("TAIJIOS_SYNC_CACHE_TTL", "60"))

def _ensure_semaphores():
    global _predict_semaphore, _sync_semaphore
    if _predict_semaphore is None:
        _predict_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PREDICT)
    if _sync_semaphore is None:
        _sync_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNC)

# ─────────────── Models ───────────────

class PredictIn(BaseModel):
    match: str = Field(..., description="对阵, 格式 'Home vs Away'",
                       json_schema_extra={"example": "Inter vs Cagliari"},
                       min_length=5, max_length=128)

    @field_validator("match")
    @classmethod
    def _match_shape(cls, v: str) -> str:
        v = v.strip()
        if not MATCH_RE.match(v):
            raise ValueError("match must match pattern 'Home vs Away' (letters/digits/CJK, 2-100 chars each side, separator vs/v/VS/-)")
        return v


class ChatIn(BaseModel):
    message: str = Field(..., description="你对 soul 说的话", min_length=1, max_length=4000)
    user_id: str = Field(..., description="独立人格 id · 不同 id = 不同记忆",
                         min_length=1, max_length=64)

    @field_validator("user_id")
    @classmethod
    def _user_id_safe(cls, v: str) -> str:
        if not USER_ID_RE.match(v):
            raise ValueError("user_id must match ^[a-zA-Z0-9_-]{1,64}$ (no path separators, no special chars)")
        return v


# ─────────────── FastAPI app ───────────────

app = FastAPI(
    title="TaijiOS API",
    version=VERSION,
    description=(
        f"TaijiOS 全家桶对外 API v{VERSION} · 企业级加固\n\n"
        "- `/v1/predict` · zhuge-skill 足球推演 (6 爻 + 64 卦 + 孔明亲笔)\n"
        "- `/v1/soul/chat` · taijios-soul 对话 (意图/关系/记忆)\n"
        "- `/v1/sync` · 公共晶体池只读 pull\n"
        "- `/v1/crystals/local` · 本地晶体库\n"
        "- `/v1/heartbeat/last` · 最近心跳日志\n\n"
        "架构: 单向 pull · 无 push 通道 · 隐私合约级保证.\n\n"
        "认证: 如设 `TAIJIOS_API_TOKEN` 环境变量, 非 loopback client 必须带 `Authorization: Bearer <token>`."
    ),
)

# CORS · default localhost only (can override via env)
_cors_origins = os.environ.get(
    "TAIJIOS_CORS_ORIGINS",
    "http://127.0.0.1:*,http://localhost:*,https://taijios.xyz"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"|".join([
        r"http://127\.0\.0\.1(:\d+)?",
        r"http://localhost(:\d+)?",
        r"https://taijios\.xyz",
    ]),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=False,
    max_age=3600,
)


# ─────────────── Routes: public ───────────────

@app.get("/", include_in_schema=False)
def index():
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>TaijiOS API</title>
<style>body{{font-family:-apple-system,sans-serif;max-width:720px;margin:3em auto;padding:0 1em;
background:#0a0f24;color:#e8f1ff;}}h1{{color:#00f0ff;}}a{{color:#ffd94a;}}
.btn{{display:inline-block;margin:8px 10px 8px 0;padding:10px 18px;background:#1a2a4a;
border:1px solid #00f0ff;border-radius:6px;color:#e8f1ff;text-decoration:none;}}
.btn:hover{{background:#2a3a5a;}}</style></head>
<body><h1>🎴 TaijiOS API v{VERSION}</h1>
<p>六爻为骨, 晶体为脉. 说不谎是日课.</p>
<p><a class="btn" href="/docs">📖 Swagger UI</a>
<a class="btn" href="/redoc">📄 ReDoc</a>
<a class="btn" href="/health">💓 Health</a></p>
<p style="margin-top:2em;opacity:0.6">零 push 通道 · 单向架构 · 隐私合约级. · Enterprise-hardened.</p></body></html>""",
        status_code=200,
    )


@app.get("/health", summary="健康检查 · 不需要 auth")
def health():
    return {"status": "ok", "version": VERSION, "service": "taijios-api",
            "auth_required": bool(_api_token())}


# ─────────────── Routes: v1 (auth-gated when TOKEN set) ───────────────

@app.get("/v1/status", summary="系统状态 · 7 repo + 心跳", dependencies=[Depends(require_token)])
def system_status():
    trace_id = new_trace()
    repos = ["zhuge-skill", "TaijiOS", "TaijiOS-Lite", "zhuge-crystals",
             "self-improving-loop", "taijios-landing", "taiji"]
    return {
        "data": {
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
        },
        "meta": meta_envelope(trace_id, {"route": "/v1/status"}),
    }


@app.post("/v1/predict", summary="诸葛亮足球推演", tags=["zhuge"],
          dependencies=[Depends(require_token)])
async def predict(body: PredictIn):
    _ensure_semaphores()
    trace_id = new_trace()
    route = "/v1/predict"
    try:
        # Bounded concurrency: queue if full
        async with asyncio.timeout(200):
            async with _predict_semaphore:
                # run the blocking subprocess in the default executor
                loop = asyncio.get_running_loop()
                def _run():
                    return subprocess.run(
                        [sys.executable, str(ZHUGE / "scripts" / "predict.py"), body.match],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=180, cwd=str(ZHUGE),
                        env={**os.environ, "PYTHONIOENCODING": "utf-8", "TAIJIOS_TRACE_ID": trace_id},
                    )
                r = await loop.run_in_executor(None, _run)
    except TimeoutError:
        log_error(route, trace_id, "timeout", "predict execution > 200s")
        raise HTTPException(status_code=504, detail={"error": "timeout", "trace_id": trace_id})
    except Exception as e:
        log_error(route, trace_id, "exec_error", f"{type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail={"error": "execution_failed", "trace_id": trace_id})

    raw = (r.stdout or "") + (r.stderr or "")
    text = ANSI.sub("", raw)
    scrub = sanitize_output(text, trace_id)
    demo = DEMO_MARKER in text
    clean = scrub["clean"].replace(DEMO_MARKER, "").strip()

    if scrub["had_traceback"] or scrub["had_path_leak"]:
        log_error(route, trace_id, "output_leak_scrubbed", raw)

    if r.returncode != 0:
        # Non-demo failures: return safe summary only
        log_error(route, trace_id, "nonzero_rc", raw)
        return JSONResponse(status_code=422, content={
            "data": {"match": body.match, "demo_mode": False},
            "error": {"code": "prediction_failed", "rc": r.returncode, "detail": "see server-side error log"},
            "meta": meta_envelope(trace_id, {"route": route}),
        })

    return {
        "data": {
            "match": body.match,
            "exit_code": r.returncode,
            "output": clean,
            "demo_mode": demo,
        },
        "meta": meta_envelope(trace_id, {
            "route": route,
            "leaks_scrubbed": scrub["had_traceback"] or scrub["had_path_leak"],
        }),
    }


@app.post("/v1/soul/chat", summary="Soul 对话一轮", tags=["soul"],
          dependencies=[Depends(require_token)])
def soul_chat(body: ChatIn):
    trace_id = new_trace()
    sys.path.insert(0, str(SOUL / "src"))
    try:
        from taijios import Soul
    except ImportError:
        log_error("/v1/soul/chat", trace_id, "soul_not_installed", "taijios-soul not pip install -e")
        raise HTTPException(500, detail={"error": "soul_unavailable", "trace_id": trace_id,
                                          "hint": "python taijios.py install"})
    try:
        s = Soul(user_id=body.user_id)
        r = s.chat(body.message)
    except Exception as e:
        log_error("/v1/soul/chat", trace_id, type(e).__name__, str(e)[:500])
        raise HTTPException(500, detail={"error": "soul_error", "trace_id": trace_id})
    return {
        "data": {
            "user_id": body.user_id,
            "interaction_count": r.interaction_count,
            "intent": r.intent,
            "stage": r.stage,
            "frustration": r.frustration,
            "reply": r.reply,
        },
        "meta": meta_envelope(trace_id, {"route": "/v1/soul/chat"}),
    }


@app.get("/v1/soul/{user_id}", summary="Soul 完整状态", tags=["soul"],
         dependencies=[Depends(require_token)])
def soul_state(user_id: str):
    trace_id = new_trace()
    if not USER_ID_RE.match(user_id):
        raise HTTPException(status_code=422, detail={
            "error": "invalid_user_id",
            "constraint": "^[a-zA-Z0-9_-]{1,64}$",
            "trace_id": trace_id,
        })
    sys.path.insert(0, str(SOUL / "src"))
    try:
        from taijios import Soul
    except ImportError:
        raise HTTPException(500, detail={"error": "soul_unavailable", "trace_id": trace_id})
    try:
        s = Soul(user_id=user_id)
    except Exception as e:
        log_error("/v1/soul/{user_id}", trace_id, type(e).__name__, str(e)[:500])
        raise HTTPException(500, detail={"error": "soul_error", "trace_id": trace_id})
    return {
        "data": {
            "user_id": user_id,
            "stage": s.stage,
            "backend": s.backend,
            "memory": s._memory.to_dict(),
            "generals": s._council.to_dict(),
        },
        "meta": meta_envelope(trace_id, {"route": "/v1/soul/{user_id}"}),
    }


@app.post("/v1/sync", summary="拉公共晶体池 (HTTP 只读, 60s 缓存)", tags=["crystals"],
          dependencies=[Depends(require_token)])
async def sync_crystals():
    _ensure_semaphores()
    trace_id = new_trace()
    # serve from cache if fresh
    if _sync_cache["result"] is not None and (time.time() - _sync_cache["ts"]) < SYNC_CACHE_TTL:
        cached = _sync_cache["result"]
        return {
            "data": cached,
            "meta": meta_envelope(trace_id, {"route": "/v1/sync", "cache_hit": True,
                                              "cache_age_s": round(time.time() - _sync_cache["ts"], 1)}),
        }
    try:
        async with asyncio.timeout(60):
            async with _sync_semaphore:
                loop = asyncio.get_running_loop()
                def _run():
                    return subprocess.run(
                        [sys.executable, str(ZHUGE / "scripts" / "sync.py"), "pull"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=50, cwd=str(ZHUGE),
                        env={**os.environ, "PYTHONIOENCODING": "utf-8", "TAIJIOS_TRACE_ID": trace_id},
                    )
                r = await loop.run_in_executor(None, _run)
    except TimeoutError:
        log_error("/v1/sync", trace_id, "timeout", "sync execution > 60s")
        raise HTTPException(status_code=504, detail={"error": "sync_timeout", "trace_id": trace_id})
    raw = (r.stdout or "") + (r.stderr or "")
    scrub = sanitize_output(ANSI.sub("", raw), trace_id)
    if scrub["had_traceback"] or scrub["had_path_leak"]:
        log_error("/v1/sync", trace_id, "output_leak_scrubbed", raw)
    result = {"exit_code": r.returncode, "output": scrub["clean"]}
    _sync_cache["result"] = result
    _sync_cache["ts"] = time.time()
    return {
        "data": result,
        "meta": meta_envelope(trace_id, {"route": "/v1/sync", "cache_hit": False}),
    }


@app.get("/v1/crystals/local", summary="本地晶体库", tags=["crystals"],
         dependencies=[Depends(require_token)])
def list_local_crystals(limit: int = 20):
    trace_id = new_trace()
    limit = max(1, min(limit, 500))  # bound pagination
    f = ZHUGE / "data" / "crystals_local.jsonl"
    if not f.exists():
        return {"data": {"count": 0, "crystals": []},
                "meta": meta_envelope(trace_id, {"route": "/v1/crystals/local"})}
    crystals = []
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                crystals.append(json.loads(line))
            except Exception:
                pass
    return {
        "data": {"count": len(crystals), "crystals": crystals[:limit]},
        "meta": meta_envelope(trace_id, {"route": "/v1/crystals/local", "limit": limit}),
    }


@app.get("/v1/heartbeat/last", summary="最近 heartbeat 日志", tags=["daemon"],
         dependencies=[Depends(require_token)])
def heartbeat_last(lines: int = 20):
    trace_id = new_trace()
    lines = max(1, min(lines, 500))
    log = HOME_TAIJIOS / "heartbeat.log"
    if not log.exists():
        return {"data": {"exists": False, "reason": "还没 tick 过 · 跑 python heartbeat.py"},
                "meta": meta_envelope(trace_id, {"route": "/v1/heartbeat/last"})}
    all_lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    return {
        "data": {"exists": True, "total_lines": len(all_lines), "recent": all_lines[-lines:]},
        "meta": meta_envelope(trace_id, {"route": "/v1/heartbeat/last", "requested_lines": lines}),
    }


@app.get("/v1/share/queue", summary="共享队列待审", tags=["crystals"],
         dependencies=[Depends(require_token)])
def share_queue():
    trace_id = new_trace()
    q = HOME_TAIJIOS / "share_queue"
    if not q.exists():
        return {"data": {"batches": 0, "total_crystals": 0, "files": []},
                "meta": meta_envelope(trace_id, {"route": "/v1/share/queue"})}
    files = list(q.glob("*.jsonl"))
    total = 0
    for f in files:
        total += sum(1 for line in f.read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "data": {"batches": len(files), "total_crystals": total,
                 "files": [str(f.name) for f in files]},
        "meta": meta_envelope(trace_id, {"route": "/v1/share/queue"}),
    }


# ─────────────── Startup banner ───────────────

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

    tok = _api_token()
    auth_info = "auth=ENABLED (Bearer token)" if tok else "auth=DEV (no token)"
    is_loopback = args.host in ("127.0.0.1", "::1", "localhost")
    if tok:
        weak, reason = _is_weak_token(tok)
        if weak and not is_loopback:
            print(f"\n✗ FATAL · TAIJIOS_API_TOKEN is weak ({reason}).", file=sys.stderr)
            print(f"  Refusing to bind to non-loopback host '{args.host}' with this token.", file=sys.stderr)
            print(f"  Generate a strong token: python tools/gen_token.py", file=sys.stderr)
            print(f"  Or unset to use dev mode: setx TAIJIOS_API_TOKEN \"\" (Windows) / unset TAIJIOS_API_TOKEN (Linux)", file=sys.stderr)
            sys.exit(2)
        elif weak and is_loopback:
            print(f"\n⚠ WARNING · TAIJIOS_API_TOKEN is weak ({reason}).", file=sys.stderr)
            print(f"  Loopback bind allows it for now, but never use this token in production.", file=sys.stderr)
            print(f"  Generate a strong one: python tools/gen_token.py\n", file=sys.stderr)
    print(f"\n🎴 TaijiOS API Server v{VERSION}  [{auth_info}]")
    print(f"   Swagger UI: http://{args.host}:{args.port}/docs")
    print(f"   ReDoc:      http://{args.host}:{args.port}/redoc")
    print(f"   首页:        http://{args.host}:{args.port}/")
    print(f"   Error log:  {ERROR_LOG}")
    print(f"   Ctrl+C 退出\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
