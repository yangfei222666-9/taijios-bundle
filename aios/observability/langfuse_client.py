"""
langfuse_client · 0-dependency thin Langfuse ingestion client

Sends trace/generation events to a self-hosted Langfuse (docker-compose in deploy/langfuse/).
Protocol: POST /api/public/ingestion · Basic auth (public_key:secret_key).

Use via:
    from aios.observability.langfuse_client import LangfuseTracer

    lf = LangfuseTracer()  # reads LANGFUSE_* from .env
    if lf.enabled:
        with lf.trace("predict_match", user_id="taijios") as t:
            reply = call_openai(...)
            t.log_generation(
                name="openai-gpt-4o-mini",
                model="gpt-4o-mini",
                input=messages,
                output=reply,
                usage={"input": 30, "output": 15},
            )

Designed to **fail soft** — if Langfuse is down, traces get dropped with a warning
log but the caller's LLM call is never interrupted.

§5.3 provenance: every event carries a trace_id we control (stable across retries)
so Langfuse dashboard + sentinel.log.jsonl can be cross-joined.
"""
from __future__ import annotations
import base64
import json
import os
import time
import uuid
import urllib.request
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_env_file() -> dict:
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


def _resolve(key: str, default: str = "") -> str:
    v = os.environ.get(key, "").strip()
    if v:
        return v
    return _load_env_file().get(key, default).strip()


class _Trace:
    def __init__(self, parent: "LangfuseTracer", trace_id: str, name: str, user_id: Optional[str]):
        self._parent = parent
        self.trace_id = trace_id
        self.name = name
        self.user_id = user_id
        self._events: list[dict] = []
        self._started_at = _iso_now()

    def log_generation(
        self,
        *,
        name: str,
        model: str,
        input: Any,
        output: Any,
        usage: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        gen_id = f"gen-{uuid.uuid4().hex[:12]}"
        event = {
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": _iso_now(),
            "body": {
                "id": gen_id,
                "traceId": self.trace_id,
                "name": name,
                "model": model,
                "startTime": _iso_now(),
                "endTime": _iso_now(),
                "input": input,
                "output": output,
                "usage": usage or {},
                "metadata": metadata or {},
            },
        }
        self._events.append(event)

    def log_event(self, name: str, metadata: Optional[dict] = None) -> None:
        event = {
            "id": str(uuid.uuid4()),
            "type": "event-create",
            "timestamp": _iso_now(),
            "body": {
                "id": f"ev-{uuid.uuid4().hex[:12]}",
                "traceId": self.trace_id,
                "name": name,
                "startTime": _iso_now(),
                "metadata": metadata or {},
            },
        }
        self._events.append(event)

    def _flush(self) -> None:
        # Prepend the trace-create event
        self._events.insert(0, {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": self._started_at,
            "body": {
                "id": self.trace_id,
                "name": self.name,
                "userId": self.user_id,
                "timestamp": self._started_at,
            },
        })
        self._parent._ingest(self._events)


class LangfuseTracer:
    def __init__(self, host: Optional[str] = None,
                 public_key: Optional[str] = None,
                 secret_key: Optional[str] = None,
                 timeout: int = 5):
        self.host = (host or _resolve("LANGFUSE_HOST", "http://localhost:3000")).rstrip("/")
        self.public_key = public_key or _resolve("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or _resolve("LANGFUSE_SECRET_KEY")
        self.timeout = timeout
        self.enabled = bool(self.public_key and self.secret_key)

    @contextmanager
    def trace(self, name: str, user_id: Optional[str] = None,
              trace_id: Optional[str] = None):
        """Context manager. Yields a _Trace object. Flush on exit (best-effort)."""
        tid = trace_id or f"trace-{uuid.uuid4().hex[:12]}"
        t = _Trace(self, tid, name, user_id)
        try:
            yield t
        finally:
            if self.enabled:
                try:
                    t._flush()
                except Exception as e:
                    # Fail-soft: never break the caller because observability is down
                    self._warn(f"flush failed: {type(e).__name__}: {str(e)[:100]}")

    def _ingest(self, events: list[dict]) -> None:
        if not events:
            return
        creds = f"{self.public_key}:{self.secret_key}".encode()
        auth = base64.b64encode(creds).decode()
        data = json.dumps({"batch": events}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/public/ingestion",
            data=data,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            _ = r.read()

    def _warn(self, msg: str) -> None:
        # Minimal stderr · avoid logging deps
        import sys
        print(f"[langfuse-warn] {msg}", file=sys.stderr)

    def ping(self) -> bool:
        """Best-effort reachability probe (does not consume quota)."""
        try:
            req = urllib.request.Request(f"{self.host}/api/public/health")
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status == 200
        except Exception:
            return False


# ───────────── CLI smoke ─────────────

if __name__ == "__main__":
    lf = LangfuseTracer()
    if not lf.enabled:
        print("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set · enabled=False")
        print(f"host: {lf.host}")
        raise SystemExit(2)
    print(f"host: {lf.host}  enabled: {lf.enabled}")
    print(f"ping: {lf.ping()}")
    with lf.trace("smoke_test", user_id="taijios") as t:
        t.log_generation(
            name="test-call",
            model="mock-model",
            input=[{"role": "user", "content": "ping"}],
            output="pong",
            usage={"input": 1, "output": 1, "total": 2},
        )
        t.log_event("smoke_ok", metadata={"ts": _iso_now()})
    print(f"flushed trace_id={t.trace_id}")
