"""
whisper_stt · OpenAI Whisper API adapter for TaijiOS

复用已有的 OPENAI_OFFICIAL_KEY · 不引入新 provider · 闭合 TTS (豆包) ↔ STT (Whisper) 循环.

用法:
    from aios.voice.whisper_stt import transcribe_file, transcribe_bytes

    # 转写本地 mp3/wav/m4a/webm 等 (< 25MB)
    text = transcribe_file("audio.mp3", language="zh")
    print(text)

    # 或直接传 bytes (e.g. from WebSocket upload)
    with open("audio.wav", "rb") as f:
        text = transcribe_bytes(f.read(), filename="audio.wav", language="zh")

设计决策 (2026-04-19):
    · 单向调 OpenAI /v1/audio/transcriptions (Whisper v1)
    · 默认 model=whisper-1 (最便宜 · $0.006/min)
    · 支持 language hint (zh/en/...) 提高准确率
    · 支持 response_format=text / json / verbose_json
    · 自动处理 25MB 上限 (超限 raise AudioTooLargeError)
    · 失败抛 WhisperError 带 trace_id 便于跨服务关联 (§5.3 provenance)
"""
from __future__ import annotations
import os
import json
import uuid
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Union

__all__ = ["transcribe_file", "transcribe_bytes", "WhisperError", "AudioTooLargeError"]

OPENAI_API_BASE = os.environ.get("OPENAI_API_BASE_WHISPER", "https://api.openai.com/v1")
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # OpenAI Whisper hard limit
DEFAULT_MODEL = "whisper-1"


class WhisperError(RuntimeError):
    def __init__(self, message: str, trace_id: str, code: Optional[int] = None):
        super().__init__(f"{message} (trace_id={trace_id})")
        self.trace_id = trace_id
        self.code = code


class AudioTooLargeError(WhisperError):
    pass


def _load_env_file() -> dict:
    """Load .env file as dict (NOT mutating os.environ).
    Drift defense: some shells have OPENAI_API_KEY = OPENCLAW_API_KEY via proxy shim,
    so we prefer the .env file value for OPENAI_OFFICIAL_KEY.
    """
    candidates = []
    explicit = os.environ.get("TAIJIOS_ENV_FILE", "").strip()
    if explicit:
        candidates.append(Path(explicit))
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
    """Resolve the OpenAI key with hard ordering to avoid shell pollution:
    1. explicit env TAIJIOS_WHISPER_OPENAI_KEY (for tests / override)
    2. .env file OPENAI_OFFICIAL_KEY (preferred · real new key)
    3. os.environ['OPENAI_OFFICIAL_KEY'] if non-empty
    Never falls through to OPENAI_API_KEY because that var is known to be
    contaminated by OpenClaw proxy shims.
    """
    trace = "whisper-no-key"
    override = os.environ.get("TAIJIOS_WHISPER_OPENAI_KEY", "").strip()
    if override and override.startswith("sk-"):
        return override
    env_file = _load_env_file()
    file_val = env_file.get("OPENAI_OFFICIAL_KEY", "").strip()
    if file_val and file_val.startswith("sk-"):
        return file_val
    shell_val = os.environ.get("OPENAI_OFFICIAL_KEY", "").strip()
    if shell_val and shell_val.startswith("sk-"):
        return shell_val
    raise WhisperError(
        "no OPENAI_OFFICIAL_KEY found in .env / os.environ (OPENAI_API_KEY is ignored here "
        "because it is commonly polluted by OpenClaw-proxy shims)",
        trace_id=trace,
    )


def _multipart_body(fields: dict, file_bytes: bytes, filename: str) -> tuple[bytes, str]:
    """Build a minimal multipart/form-data body · no external deps."""
    boundary = f"----taijios-whisper-{uuid.uuid4().hex[:12]}"
    lines: list[bytes] = []
    for k, v in fields.items():
        if v is None:
            continue
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        lines.append(str(v).encode("utf-8") + b"\r\n")
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    lines.append(b"Content-Type: application/octet-stream\r\n\r\n")
    lines.append(file_bytes)
    lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    body = b"".join(lines)
    return body, boundary


def transcribe_bytes(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    model: str = DEFAULT_MODEL,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    response_format: str = "text",
    timeout: int = 120,
) -> Union[str, dict]:
    """Transcribe raw audio bytes · returns text (default) or dict when response_format='json'."""
    trace_id = f"whisper-{uuid.uuid4().hex[:12]}"
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise AudioTooLargeError(
            f"audio {len(audio_bytes)} bytes exceeds 25MB Whisper limit",
            trace_id=trace_id,
        )
    key = _resolve_key()
    fields = {
        "model": model,
        "language": language,
        "prompt": prompt,
        "response_format": response_format,
    }
    body, boundary = _multipart_body(fields, audio_bytes, filename)
    req = urllib.request.Request(
        f"{OPENAI_API_BASE}/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Trace-Id": trace_id,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")[:400]
        raise WhisperError(f"HTTP {e.code}: {err}", trace_id=trace_id, code=e.code) from None
    except Exception as e:
        raise WhisperError(f"{type(e).__name__}: {str(e)[:200]}", trace_id=trace_id) from None
    if response_format == "text":
        return raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"text": raw, "_raw": True}


def transcribe_file(
    path: Union[str, Path],
    **kwargs,
) -> Union[str, dict]:
    p = Path(path)
    if not p.exists():
        raise WhisperError(f"file not found: {p}", trace_id=f"whisper-{uuid.uuid4().hex[:8]}")
    data = p.read_bytes()
    return transcribe_bytes(data, filename=p.name, **kwargs)


# ────────────────── CLI smoke test ──────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Whisper STT smoke test")
    ap.add_argument("file", help="audio file path")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--format", default="text", choices=["text", "json", "verbose_json", "srt", "vtt"])
    args = ap.parse_args()
    try:
        result = transcribe_file(args.file, language=args.language,
                                 prompt=args.prompt, response_format=args.format)
        if isinstance(result, dict):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)
    except WhisperError as e:
        print(f"ERROR: {e}")
        raise SystemExit(1)
