"""
tests/test_review_hooks.py · PreReview/PostReview hook dispatcher + built-ins.

运行: python -m pytest tests/test_review_hooks.py -v
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from aios.core.provider_registry import load_registry, DEFAULT_REGISTRY_PATH
from aios.core.verdict_schema import load_schema, DEFAULT_SCHEMA_PATH
from aios.core.review_runner import ReviewRunner, RegisteredReviewer
from aios.core.review_hooks import (
    HookDispatcher, AuditLogHook, CostGuardHook, ProviderCost,
)


@pytest.fixture(autouse=True)
def _clean_legacy_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)


@pytest.fixture(scope="module")
def registry():
    return load_registry(DEFAULT_REGISTRY_PATH)


@pytest.fixture(scope="module")
def schema():
    return load_schema(DEFAULT_SCHEMA_PATH)


def _mk_reviewer(provider_id, role, verdict, extra=None):
    def call_fn(claim):
        out = {
            "reviewer": f"{provider_id}-test",
            "verdict": verdict,
            "confidence": "high",
            "evidence": [{"path": "x.py", "line": 1, "note": "canned"}],
        }
        if extra:
            out.update(extra)
        return out
    return RegisteredReviewer(provider_id=provider_id, reviewer_role=role, call_fn=call_fn)


def _mk_failing_reviewer(provider_id, role, exc_class=RuntimeError):
    def call_fn(claim):
        raise exc_class("boom")
    return RegisteredReviewer(provider_id=provider_id, reviewer_role=role, call_fn=call_fn)


# ─────────── dispatcher isolation ───────────


class _Spy:
    def __init__(self):
        self.pre_calls = []
        self.post_calls = []

    def pre_reviewer_call(self, claim, provider_id, reviewer_role, run_id):
        self.pre_calls.append((provider_id, reviewer_role, claim["claim_id"]))

    def post_reviewer_call(self, verdict, provider_id, reviewer_role, run_id, elapsed_ms, error=None):
        self.post_calls.append({
            "provider_id": provider_id,
            "has_verdict": verdict is not None,
            "error": type(error).__name__ if error else None,
        })


def test_hooks_fire_for_every_reviewer(registry, schema):
    spy = _Spy()
    hooks = HookDispatcher([spy])
    runner = ReviewRunner(registry=registry, schema=schema,
                          proposal_source="test-hooks", hooks=hooks)
    runner.register_reviewer(_mk_reviewer("anthropic_native", "voter", "confirmed"))
    runner.register_reviewer(_mk_reviewer("deepseek_native",  "voter", "rejected"))

    verdicts = runner.review_claim({"claim_id": "CLAIM-A"})
    assert len(verdicts) == 2
    assert len(spy.pre_calls) == 2
    assert len(spy.post_calls) == 2
    assert all(c["has_verdict"] for c in spy.post_calls)
    assert all(c["error"] is None for c in spy.post_calls)


def test_hooks_fire_post_on_call_fn_exception(registry, schema):
    spy = _Spy()
    hooks = HookDispatcher([spy])
    runner = ReviewRunner(registry=registry, schema=schema,
                          proposal_source="test-hooks", hooks=hooks)
    runner.register_reviewer(_mk_failing_reviewer("anthropic_native", "voter"))
    runner.register_reviewer(_mk_reviewer("deepseek_native", "voter", "confirmed"))

    verdicts = runner.review_claim({"claim_id": "CLAIM-B"})
    assert len(verdicts) == 1
    assert len(spy.post_calls) == 2
    failing = [c for c in spy.post_calls if c["provider_id"] == "anthropic_native"][0]
    assert failing["has_verdict"] is False
    assert failing["error"] == "RuntimeError"


def test_hook_exceptions_do_not_break_runner(registry, schema):
    class _Boom:
        def pre_reviewer_call(self, *a, **k): raise RuntimeError("pre-boom")
        def post_reviewer_call(self, *a, **k): raise RuntimeError("post-boom")
    hooks = HookDispatcher([_Boom()])
    runner = ReviewRunner(registry=registry, schema=schema,
                          proposal_source="test-hooks", hooks=hooks)
    runner.register_reviewer(_mk_reviewer("anthropic_native", "voter", "confirmed"))
    # Runner must still succeed even if every hook raises.
    verdicts = runner.review_claim({"claim_id": "CLAIM-C"})
    assert len(verdicts) == 1


def test_attach_hook_method_works(registry, schema):
    spy = _Spy()
    runner = ReviewRunner(registry=registry, schema=schema, proposal_source="test-hooks")
    runner.attach_hook(spy)
    runner.register_reviewer(_mk_reviewer("anthropic_native", "voter", "confirmed"))
    runner.review_claim({"claim_id": "CLAIM-D"})
    assert len(spy.pre_calls) == 1


# ─────────── AuditLogHook ───────────


def test_audit_log_hook_writes_jsonl(registry, schema, tmp_path):
    log_path = tmp_path / "audit.jsonl"
    audit = AuditLogHook(log_path=log_path)
    runner = ReviewRunner(registry=registry, schema=schema, proposal_source="test-audit")
    runner.attach_hook(audit)
    runner.register_reviewer(_mk_reviewer("anthropic_native", "voter", "confirmed"))
    runner.register_reviewer(_mk_failing_reviewer("deepseek_native", "voter"))

    runner.review_claim({"claim_id": "CLAIM-AUDIT"})

    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert {r["provider_id"] for r in rows} == {"anthropic_native", "deepseek_native"}

    ok_row = [r for r in rows if r["provider_id"] == "anthropic_native"][0]
    assert ok_row["verdict"] == "confirmed"
    assert ok_row["claim_id"] == "CLAIM-AUDIT"
    assert "error_flavor" not in ok_row
    assert ok_row["elapsed_ms"] >= 0

    fail_row = [r for r in rows if r["provider_id"] == "deepseek_native"][0]
    assert fail_row["error_flavor"] == "RuntimeError"
    assert "verdict" not in fail_row


def test_audit_log_hook_include_evidence_flag(registry, schema, tmp_path):
    log_path = tmp_path / "audit_ev.jsonl"
    audit = AuditLogHook(log_path=log_path, include_evidence=True)
    runner = ReviewRunner(registry=registry, schema=schema, proposal_source="test-audit")
    runner.attach_hook(audit)
    runner.register_reviewer(_mk_reviewer("anthropic_native", "voter", "confirmed"))
    runner.review_claim({"claim_id": "CLAIM-EV"})

    row = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert "evidence" in row
    assert row["evidence"][0]["path"] == "x.py"


# ─────────── CostGuardHook ───────────


def test_cost_guard_counts_calls_and_warns(registry, schema):
    warnings_fired = []
    def on_warn(provider_id, reason, c: ProviderCost):
        warnings_fired.append((provider_id, reason))

    guard = CostGuardHook(max_calls_warn=2, max_tokens_out_warn=10_000, on_warn=on_warn)
    runner = ReviewRunner(registry=registry, schema=schema, proposal_source="test-cost")
    runner.attach_hook(guard)
    runner.register_reviewer(_mk_reviewer("anthropic_native", "voter", "confirmed"))

    runner.review_claim({"claim_id": "C1"})
    runner.review_claim({"claim_id": "C2"})  # hits max_calls_warn=2

    snap = guard.snapshot()
    assert snap["anthropic_native"]["calls"] == 2
    assert ("anthropic_native", "calls_threshold") in warnings_fired


def test_cost_guard_counts_tokens_when_reviewer_reports(registry, schema):
    guard = CostGuardHook(max_tokens_out_warn=500)
    runner = ReviewRunner(registry=registry, schema=schema, proposal_source="test-cost")
    runner.attach_hook(guard)
    runner.register_reviewer(_mk_reviewer(
        "anthropic_native", "voter", "confirmed",
        extra={"tokens_in": 120, "tokens_out": 80},
    ))
    runner.review_claim({"claim_id": "C-T1"})
    runner.review_claim({"claim_id": "C-T2"})

    snap = guard.snapshot()
    assert snap["anthropic_native"]["tokens_in"] == 240
    assert snap["anthropic_native"]["tokens_out"] == 160


def test_cost_guard_reset_clears_counters(registry, schema):
    guard = CostGuardHook()
    runner = ReviewRunner(registry=registry, schema=schema, proposal_source="test-cost")
    runner.attach_hook(guard)
    runner.register_reviewer(_mk_reviewer("anthropic_native", "voter", "confirmed"))
    runner.review_claim({"claim_id": "C-R"})
    guard.reset()
    assert guard.snapshot() == {}


# ─────────── backward compat · no hooks = no behavior change ───────────


def test_runner_without_hooks_has_empty_dispatcher(registry, schema):
    runner = ReviewRunner(registry=registry, schema=schema, proposal_source="test-compat")
    assert runner.hooks.hooks == []  # default dispatcher is empty
    runner.register_reviewer(_mk_reviewer("anthropic_native", "voter", "confirmed"))
    verdicts = runner.review_claim({"claim_id": "C-COMPAT"})
    assert len(verdicts) == 1  # untouched behavior
