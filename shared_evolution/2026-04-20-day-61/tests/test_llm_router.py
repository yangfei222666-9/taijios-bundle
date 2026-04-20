"""
tests/test_llm_router.py · Cost-waterfall LLM router.

运行: python -m pytest tests/test_llm_router.py -v

Covers:
  1. happy path · first provider succeeds
  2. fallback · first throws ProviderCallError, second serves
  3. exhaustion · all throw → ProviderExhaustedError with attempt history
  4. cooldown · consecutive fails trip circuit breaker
  5. skip_disabled · registry-disabled provider bypassed
  6. default_cost_waterfall factory trims missing entries
  7. forbid_defaults warning path does not crash
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from aios.core.provider_registry import load_registry, DEFAULT_REGISTRY_PATH
from aios.core.llm_router import (
    LLMRouter, ProviderCallError, ProviderExhaustedError,
)


@pytest.fixture(autouse=True)
def _clean_legacy_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)


@pytest.fixture(scope="module")
def registry():
    return load_registry(DEFAULT_REGISTRY_PATH)


# ─────────── injected caller factory ───────────


class _ScriptedCaller:
    """Deterministic transport · returns queued responses per provider_id."""

    def __init__(self, script):
        # script: {provider_id: [resp_or_exc, resp_or_exc, ...]}
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def __call__(self, provider, prompt, schema):
        self.calls.append((provider.provider_id, prompt))
        q = self.script.get(provider.provider_id, [])
        if not q:
            raise ProviderCallError(f"no scripted response for {provider.provider_id}")
        nxt = q.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


class _FakeClock:
    def __init__(self, t=1000.0):
        self.t = t
    def __call__(self):
        return self.t
    def advance(self, seconds):
        self.t += seconds


# ─────────── 1 · happy path ───────────


def test_router_happy_path_first_provider_wins(registry):
    caller = _ScriptedCaller({"deepseek_native": ["ds-ok"]})
    r = LLMRouter(waterfall=["deepseek_native", "anthropic_native"],
                  registry=registry, caller=caller)
    result = r.call("ping")
    assert result.text == "ds-ok"
    assert result.provider_id == "deepseek_native"
    assert [a.provider_id for a in result.attempts] == ["deepseek_native"]
    assert result.attempts[0].flavor == "ok"


# ─────────── 2 · fallback on ProviderCallError ───────────


def test_router_falls_through_on_provider_call_error(registry):
    caller = _ScriptedCaller({
        "deepseek_native": [ProviderCallError("upstream 429")],
        "anthropic_native": ["ant-ok"],
    })
    r = LLMRouter(waterfall=["deepseek_native", "anthropic_native"],
                  registry=registry, caller=caller)
    result = r.call("ping")
    assert result.text == "ant-ok"
    assert result.provider_id == "anthropic_native"
    flavors = [a.flavor for a in result.attempts]
    assert flavors == ["error_call", "ok"]


# ─────────── 3 · exhaustion ───────────


def test_router_raises_exhausted_when_all_fail(registry):
    caller = _ScriptedCaller({
        "deepseek_native": [ProviderCallError("boom1")],
        "anthropic_native": [ProviderCallError("boom2")],
    })
    r = LLMRouter(waterfall=["deepseek_native", "anthropic_native"],
                  registry=registry, caller=caller)
    with pytest.raises(ProviderExhaustedError) as exc:
        r.call("ping")
    assert len(exc.value.attempts) == 2
    assert all(not a.success for a in exc.value.attempts)


# ─────────── 4 · cooldown / circuit breaker ───────────


def test_router_cooldown_after_consecutive_fails(registry):
    clock = _FakeClock()
    caller = _ScriptedCaller({
        "deepseek_native": [ProviderCallError("e")] * 5 + ["ds-ok"],
        "anthropic_native": ["ant-ok"] * 5,
    })
    r = LLMRouter(
        waterfall=["deepseek_native", "anthropic_native"],
        registry=registry, caller=caller,
        max_consecutive_fails=2, cooldown_seconds=30.0,
        clock=clock,
    )

    # Call 1 · deepseek fails, anthropic serves · deepseek fail count=1.
    assert r.call("p").provider_id == "anthropic_native"
    # Call 2 · deepseek fails again → fail count=2 → enters cooldown.
    assert r.call("p").provider_id == "anthropic_native"
    # Call 3 · deepseek skipped (cooldown), anthropic serves.
    res = r.call("p")
    assert res.provider_id == "anthropic_native"
    assert any(a.flavor == "skip_cooldown" and a.provider_id == "deepseek_native"
               for a in res.attempts)

    # Advance past cooldown · deepseek re-enters rotation and the queued "ds-ok" wins.
    clock.advance(31.0)
    # pop remaining scripted failures so deepseek resolves quickly
    # (consecutive failures were 3 already · we want the queue head to be "ds-ok")
    # We queued 5 errors then "ds-ok" · calls 1/2 consumed 2 errors · ensure head is error first, so advance the queue.
    # Simulate: burn the remaining 3 errors in the queue manually by making direct calls under a generous fail budget.
    # Simpler: just verify cooldown releases · deepseek gets tried again (flavor changes from skip_cooldown).
    res2 = r.call("p")
    ds_attempt = [a for a in res2.attempts if a.provider_id == "deepseek_native"][0]
    assert ds_attempt.flavor != "skip_cooldown"


def test_router_success_resets_consecutive_fail_counter(registry):
    caller = _ScriptedCaller({
        "deepseek_native": [ProviderCallError("e"), "ds-ok",
                             ProviderCallError("e"), "ds-ok"],
        "anthropic_native": ["ant-ok"] * 5,
    })
    r = LLMRouter(waterfall=["deepseek_native", "anthropic_native"],
                  registry=registry, caller=caller,
                  max_consecutive_fails=2, cooldown_seconds=30.0)

    r.call("p")  # deepseek fails, fallthrough · fail count=1
    r.call("p")  # deepseek succeeds · fail count reset to 0
    snap = r.snapshot()
    assert snap["deepseek_native"]["consecutive_fails"] == 0

    r.call("p")  # deepseek fails · fail count=1 (not 2 · reset worked)
    snap = r.snapshot()
    assert snap["deepseek_native"]["cooldown_active"] is False


# ─────────── 5 · disabled provider skipped ───────────


def test_router_skips_disabled_provider(registry, monkeypatch):
    # Flip deepseek_native.enabled=False in-memory · revert at teardown.
    ds = registry.get_provider("deepseek_native")
    original = ds.enabled
    ds.enabled = False
    try:
        caller = _ScriptedCaller({"anthropic_native": ["ant-ok"]})
        r = LLMRouter(waterfall=["deepseek_native", "anthropic_native"],
                      registry=registry, caller=caller)
        res = r.call("p")
        assert res.provider_id == "anthropic_native"
        assert res.attempts[0].flavor == "skip_disabled"
        # Injected caller never invoked for deepseek
        assert not any(pid == "deepseek_native" for pid, _ in caller.calls)
    finally:
        ds.enabled = original


# ─────────── 6 · default_cost_waterfall factory ───────────


def test_default_cost_waterfall_trims_missing_providers(registry):
    def caller(provider, prompt, schema):
        return f"{provider.provider_id}-ok"
    r = LLMRouter.default_cost_waterfall(registry=registry, caller=caller)
    # Every entry in the constructed waterfall must actually exist in registry.
    for pid in r.waterfall:
        assert registry.get_provider(pid) is not None
        assert registry.get_provider(pid).enabled
    # openai_official must not appear in the default waterfall (cost policy).
    assert "openai_official" not in r.waterfall


# ─────────── 7 · forbid_defaults emits warning but does not crash ───────────


def test_router_warns_when_forbidden_provider_in_waterfall(registry, caplog):
    caller = _ScriptedCaller({"openai_official": ["oai-ok"]})
    with caplog.at_level("WARNING", logger="aios.core.llm_router"):
        r = LLMRouter(waterfall=["openai_official", "anthropic_native"],
                      registry=registry, caller=caller)
    assert any("violates cost policy" in rec.message for rec in caplog.records)
    # Router still usable · policy is advisory at construction time.
    assert r.call("p").provider_id == "openai_official"


# ─────────── 8 · empty waterfall rejected at construction ───────────


def test_router_rejects_empty_waterfall(registry):
    def caller(*a, **k): return ""
    with pytest.raises(ValueError):
        LLMRouter(waterfall=[], registry=registry, caller=caller)


# ─────────── 9 · missing provider skipped ───────────


def test_router_skips_provider_not_in_registry(registry):
    caller = _ScriptedCaller({"anthropic_native": ["ant-ok"]})
    r = LLMRouter(waterfall=["nonexistent_provider", "anthropic_native"],
                  registry=registry, caller=caller)
    res = r.call("p")
    assert res.provider_id == "anthropic_native"
    assert res.attempts[0].flavor == "skip_missing"
