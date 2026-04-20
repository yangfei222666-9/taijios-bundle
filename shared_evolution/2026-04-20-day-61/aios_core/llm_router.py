"""
aios/core/llm_router.py · Cost-waterfall LLM router.

Codifies feedback_cost_routing_policy v1 (小九 2026-04-20):

    DeepSeek → 国产 (Doubao/Kimi/GLM) → Anthropic native  (兜底)
    [OpenAI official 不在默认链路 · whitelist only]

Design patterns borrowed from BerriAI/LiteLLM's Router (waterfall + fallback +
per-provider health tracking), without pulling in the dependency. Provider
transport stays injected so this module is loop/transport agnostic — review_runner,
intel_gather, zhuge skill callers all reuse the same router.

Contract:
- waterfall is a list of provider_ids resolved against an existing ProviderRegistry.
- caller(provider, prompt, schema) returns a raw text response.
- On timeout / rate-limit / ProviderCallError the router marks the provider
  failing and tries the next one.
- After N consecutive failures a provider enters a cooldown; it is skipped
  until the cooldown expires or reset() is called.
- If every provider in the waterfall is unavailable, the router raises
  ProviderExhaustedError with the ordered attempt history.

What the router does NOT do (by design):
- Does not decide vote independence (that's review_runner's job).
- Does not touch secrets (caller resolves provider.env to real key/url).
- Does not retry the same provider mid-attempt. One strike per cycle.
"""

from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from aios.core.provider_registry import Provider, ProviderRegistry

log = logging.getLogger("aios.core.llm_router")


# ─────────── exceptions ───────────


class ProviderCallError(Exception):
    """Raised by the injected caller when a provider call fails transiently.

    Router treats it as "skip provider, try the next." Any other exception
    type bubbles up to the caller (programming errors, validation, etc.)."""


class ProviderExhaustedError(Exception):
    """No provider in the waterfall succeeded for this call."""

    def __init__(self, attempts: List["AttemptRecord"]):
        self.attempts = attempts
        detail = " → ".join(
            f"{a.provider_id}:{a.flavor}" for a in attempts
        ) or "<empty waterfall>"
        super().__init__(f"all providers exhausted: {detail}")


# ─────────── records ───────────


@dataclass
class AttemptRecord:
    """One provider attempt within a single router.call()."""
    provider_id: str
    success: bool
    flavor: str            # "ok" | "skip_disabled" | "skip_cooldown" | "skip_missing" | "error_call" | "error_other"
    elapsed_ms: float
    detail: str = ""


@dataclass
class RouterResult:
    text: str
    provider_id: str
    attempts: List[AttemptRecord]
    provider_used: Provider


@dataclass
class _ProviderHealth:
    consecutive_fails: int = 0
    last_success_mono: float = 0.0
    cooldown_until_mono: float = 0.0


# ─────────── router ───────────


class LLMRouter:
    """Cost-waterfall router · tries providers left-to-right.

    Typical construction:

        router = LLMRouter(
            waterfall=["deepseek_native", "doubao_native", "anthropic_native"],
            registry=load_registry(),
            caller=my_transport_fn,
        )
        result = router.call("hello world")
        print(result.text, result.provider_id)
    """

    # Default waterfall per feedback_cost_routing_policy v1.
    # openai_official is DELIBERATELY excluded · whitelist access only.
    DEFAULT_WATERFALL: Tuple[str, ...] = (
        "deepseek_native",
        "doubao_native",
        "kimi_native",
        "glm_relay",
        "anthropic_native",
    )

    def __init__(
        self,
        waterfall: List[str],
        registry: ProviderRegistry,
        caller: Callable[[Provider, str, Optional[dict]], str],
        *,
        max_consecutive_fails: int = 3,
        cooldown_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        forbid_defaults: Tuple[str, ...] = ("openai_official",),
    ):
        if not waterfall:
            raise ValueError("waterfall must be non-empty")
        self.registry = registry
        self.caller = caller
        self.max_consecutive_fails = max_consecutive_fails
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._health: Dict[str, _ProviderHealth] = {}

        self.waterfall: List[str] = list(waterfall)
        for forbidden in forbid_defaults:
            if forbidden in self.waterfall:
                log.warning(
                    "LLMRouter · provider '%s' in default waterfall violates cost policy · "
                    "use the whitelist path instead", forbidden,
                )

    # ─────────── state ───────────

    def _h(self, provider_id: str) -> _ProviderHealth:
        return self._health.setdefault(provider_id, _ProviderHealth())

    def is_healthy(self, provider_id: str) -> bool:
        h = self._h(provider_id)
        if h.cooldown_until_mono and self._clock() < h.cooldown_until_mono:
            return False
        return True

    def mark_success(self, provider_id: str) -> None:
        h = self._h(provider_id)
        h.consecutive_fails = 0
        h.last_success_mono = self._clock()
        h.cooldown_until_mono = 0.0

    def mark_fail(self, provider_id: str) -> None:
        h = self._h(provider_id)
        h.consecutive_fails += 1
        if h.consecutive_fails >= self.max_consecutive_fails:
            h.cooldown_until_mono = self._clock() + self.cooldown_seconds

    def reset(self, provider_id: Optional[str] = None) -> None:
        if provider_id is None:
            self._health.clear()
        else:
            self._health.pop(provider_id, None)

    def snapshot(self) -> Dict[str, dict]:
        return {
            pid: {
                "consecutive_fails": h.consecutive_fails,
                "cooldown_active": bool(h.cooldown_until_mono and self._clock() < h.cooldown_until_mono),
                "cooldown_remaining_s": max(0.0, h.cooldown_until_mono - self._clock()),
            }
            for pid, h in self._health.items()
        }

    # ─────────── call ───────────

    def call(self, prompt: str, schema: Optional[dict] = None) -> RouterResult:
        """Run prompt through the waterfall · return first successful response.

        Raises ProviderExhaustedError if every provider is skipped/failed.
        """
        attempts: List[AttemptRecord] = []
        for provider_id in self.waterfall:
            provider = self.registry.get_provider(provider_id)
            if provider is None:
                attempts.append(AttemptRecord(provider_id, False, "skip_missing", 0.0,
                                              "provider not found in registry"))
                continue
            if not provider.enabled:
                attempts.append(AttemptRecord(provider_id, False, "skip_disabled", 0.0,
                                              "provider disabled in registry"))
                continue
            if not self.is_healthy(provider_id):
                attempts.append(AttemptRecord(provider_id, False, "skip_cooldown", 0.0,
                                              "provider in cooldown"))
                continue

            t0 = self._clock()
            try:
                text = self.caller(provider, prompt, schema)
            except ProviderCallError as e:
                elapsed_ms = (self._clock() - t0) * 1000
                self.mark_fail(provider_id)
                attempts.append(AttemptRecord(provider_id, False, "error_call", elapsed_ms,
                                              f"{type(e).__name__}: {str(e)[:200]}"))
                continue
            except Exception as e:  # non-transient · still count as failure but re-raise policy undecided
                elapsed_ms = (self._clock() - t0) * 1000
                self.mark_fail(provider_id)
                attempts.append(AttemptRecord(provider_id, False, "error_other", elapsed_ms,
                                              f"{type(e).__name__}: {str(e)[:200]}"))
                # Non-ProviderCallError is still treated as waterfall-skippable so
                # one broken adapter can't take down cost routing entirely. If you
                # want strict surfacing, wrap your caller to re-raise.
                continue

            elapsed_ms = (self._clock() - t0) * 1000
            self.mark_success(provider_id)
            attempts.append(AttemptRecord(provider_id, True, "ok", elapsed_ms))
            return RouterResult(text=text, provider_id=provider_id,
                                attempts=attempts, provider_used=provider)

        raise ProviderExhaustedError(attempts)

    # ─────────── convenience factories ───────────

    @classmethod
    def default_cost_waterfall(
        cls,
        registry: ProviderRegistry,
        caller: Callable[[Provider, str, Optional[dict]], str],
        **kwargs: Any,
    ) -> "LLMRouter":
        """Build a router using DEFAULT_WATERFALL, filtered to providers that
        actually exist + are enabled in the registry.

        Missing waterfall entries are silently dropped (logged) so a TaijiOS
        install that hasn't wired up Doubao yet still boots · the router just
        falls through to the next available provider.
        """
        available = []
        for pid in cls.DEFAULT_WATERFALL:
            p = registry.get_provider(pid)
            if p is None or not p.enabled:
                log.info("LLMRouter.default_cost_waterfall · skipping '%s' (not in registry / disabled)", pid)
                continue
            available.append(pid)
        if not available:
            raise ValueError(
                "no providers from DEFAULT_WATERFALL are available in registry · "
                "check provider_registry.yaml"
            )
        return cls(waterfall=available, registry=registry, caller=caller, **kwargs)
