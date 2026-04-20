"""
aios/core/review_hooks.py · Pluggable PreReview/PostReview hooks.

Inspired by Claude Agent SDK's HookMatcher (PreToolUse/PostToolUse). Lets
TaijiOS attach auditing / cost-guard / tracing logic around every reviewer
call_fn inside ReviewRunner without touching runner internals each time a new
concern shows up.

Design choices (小九 2026-04-20 P1):
- Sync hooks. review_runner.call_fn is sync; async would need a separate path.
- Hooks never break the runner · dispatcher catches every exception and logs.
- Two concrete hooks ship here:
    · AuditLogHook  → append-only jsonl · shared_evolution spec handoff friendly
    · CostGuardHook → per-provider token / call accounting with soft-warn threshold
- review_runner accepts an optional HookDispatcher · backward compatible (all
  existing 86 tests keep passing untouched when no hooks are attached).
"""

from __future__ import annotations
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

log = logging.getLogger("aios.core.review_hooks")


# ─────────── protocol ───────────


@runtime_checkable
class ReviewHook(Protocol):
    """Pluggable interceptor around reviewer.call_fn.

    Both methods are sync and must not raise into the runner. HookDispatcher
    swallows any exception and routes it to `log.warning`.
    """

    def pre_reviewer_call(
        self,
        claim: dict,
        provider_id: str,
        reviewer_role: str,
        run_id: str,
    ) -> None: ...

    def post_reviewer_call(
        self,
        verdict: Optional[dict],
        provider_id: str,
        reviewer_role: str,
        run_id: str,
        elapsed_ms: float,
        error: Optional[BaseException] = None,
    ) -> None: ...


# ─────────── dispatcher ───────────


class HookDispatcher:
    """Fan-out across registered ReviewHooks. Never raises."""

    def __init__(self, hooks: Optional[List[ReviewHook]] = None):
        self._hooks: List[ReviewHook] = list(hooks or [])

    def register(self, hook: ReviewHook) -> None:
        self._hooks.append(hook)

    def clear(self) -> None:
        self._hooks.clear()

    @property
    def hooks(self) -> List[ReviewHook]:
        return list(self._hooks)

    def pre(self, claim: dict, provider_id: str, reviewer_role: str, run_id: str) -> None:
        for h in self._hooks:
            try:
                h.pre_reviewer_call(claim, provider_id, reviewer_role, run_id)
            except Exception as e:
                log.warning("pre_reviewer_call hook %s raised: %s", type(h).__name__, e)

    def post(
        self,
        verdict: Optional[dict],
        provider_id: str,
        reviewer_role: str,
        run_id: str,
        elapsed_ms: float,
        error: Optional[BaseException] = None,
    ) -> None:
        for h in self._hooks:
            try:
                h.post_reviewer_call(
                    verdict, provider_id, reviewer_role, run_id, elapsed_ms, error
                )
            except Exception as e:
                log.warning("post_reviewer_call hook %s raised: %s", type(h).__name__, e)


# ─────────── concrete hook · AuditLogHook ───────────


class AuditLogHook:
    """Append one jsonl row per reviewer call (both success and failure).

    Row shape:
      ts · run_id · claim_id · provider_id · reviewer_role ·
      verdict · confidence · tainted · elapsed_ms · error_flavor · error_detail

    Aligns with shared_evolution handoff spec (feedback_shared_evolution_handoff_spec.md):
    every reviewer call is auditable from a single append-only file · no ad-hoc
    logging scattered across adapters.
    """

    def __init__(self, log_path: Path | str, include_evidence: bool = False):
        self.log_path = Path(log_path)
        self.include_evidence = include_evidence
        self._lock = threading.Lock()
        self._pending_claim: Dict[str, str] = {}
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def pre_reviewer_call(self, claim, provider_id, reviewer_role, run_id):
        self._pending_claim[f"{run_id}:{provider_id}"] = claim.get("claim_id", "")

    def post_reviewer_call(
        self, verdict, provider_id, reviewer_role, run_id, elapsed_ms, error=None
    ):
        claim_id = self._pending_claim.pop(f"{run_id}:{provider_id}", "")
        row = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_id": run_id,
            "claim_id": claim_id or (verdict.get("claim_id", "") if verdict else ""),
            "provider_id": provider_id,
            "reviewer_role": reviewer_role,
            "elapsed_ms": round(elapsed_ms, 2),
        }
        if verdict is not None:
            row["verdict"] = verdict.get("verdict")
            row["confidence"] = verdict.get("confidence")
            row["tainted"] = bool(verdict.get("tainted", False))
            if self.include_evidence and "evidence" in verdict:
                row["evidence"] = verdict["evidence"]
        if error is not None:
            row["error_flavor"] = type(error).__name__
            row["error_detail"] = str(error)[:200]
        line = json.dumps(row, ensure_ascii=False)
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


# ─────────── concrete hook · CostGuardHook ───────────


@dataclass
class ProviderCost:
    calls: int = 0
    errors: int = 0
    elapsed_ms_total: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0

    def as_dict(self) -> dict:
        return {
            "calls": self.calls,
            "errors": self.errors,
            "elapsed_ms_total": round(self.elapsed_ms_total, 2),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
        }


class CostGuardHook:
    """Track per-provider cost · warn once a soft threshold is crossed.

    Token accounting reads verdict["tokens_in"] / ["tokens_out"] if the
    reviewer adapter fills them · otherwise counts stay at 0 and the hook
    degrades gracefully to call + latency accounting.

    Thresholds (per-provider):
      max_calls_warn         · warn after this many calls
      max_tokens_out_warn    · warn after this many output tokens
    Crossings fire once then stay silent unless `reset()` is called.
    """

    def __init__(
        self,
        max_calls_warn: int = 1000,
        max_tokens_out_warn: int = 1_000_000,
        on_warn: Optional[Callable[[str, str, ProviderCost], None]] = None,
    ):
        self.max_calls_warn = max_calls_warn
        self.max_tokens_out_warn = max_tokens_out_warn
        self.on_warn = on_warn or self._default_warn
        self._counters: Dict[str, ProviderCost] = {}
        self._warned: set[tuple] = set()  # (provider_id, reason)
        self._lock = threading.Lock()

    def pre_reviewer_call(self, claim, provider_id, reviewer_role, run_id):
        return  # nothing to do pre-call

    def post_reviewer_call(
        self, verdict, provider_id, reviewer_role, run_id, elapsed_ms, error=None
    ):
        with self._lock:
            c = self._counters.setdefault(provider_id, ProviderCost())
            c.calls += 1
            c.elapsed_ms_total += elapsed_ms
            if error is not None:
                c.errors += 1
                return
            if verdict is not None:
                c.tokens_in += int(verdict.get("tokens_in") or 0)
                c.tokens_out += int(verdict.get("tokens_out") or 0)
            self._maybe_warn(provider_id, c)

    def _maybe_warn(self, provider_id: str, c: ProviderCost) -> None:
        if c.calls >= self.max_calls_warn and (provider_id, "calls") not in self._warned:
            self._warned.add((provider_id, "calls"))
            self.on_warn(provider_id, "calls_threshold", c)
        if c.tokens_out >= self.max_tokens_out_warn and (provider_id, "tokens_out") not in self._warned:
            self._warned.add((provider_id, "tokens_out"))
            self.on_warn(provider_id, "tokens_out_threshold", c)

    @staticmethod
    def _default_warn(provider_id: str, reason: str, c: ProviderCost) -> None:
        log.warning(
            "CostGuard · provider=%s threshold=%s calls=%d tokens_out=%d",
            provider_id, reason, c.calls, c.tokens_out,
        )

    def snapshot(self) -> Dict[str, dict]:
        with self._lock:
            return {pid: c.as_dict() for pid, c in self._counters.items()}

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._warned.clear()
