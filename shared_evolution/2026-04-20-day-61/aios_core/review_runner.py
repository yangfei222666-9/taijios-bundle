"""
aios/core/review_runner.py · Multi-API review runner (Phase 2 + 5 + 6 + 7-prep).

P0-3 infrastructure for the multi-API review spec pack.

Responsibilities:
- Fan-out a claim to registered reviewers (voters + oracle_only).
- Aggregate votes with two hard rules:
    · oracle_only reviewers NEVER enter the vote pool.
    · verdicts sharing `independent_vote_group` collapse to one vote.
- Compute the Phase 6 dispute queue:
    · red-light (native disagreement)
    · yellow-light (cited-line wrong but pattern present)
    · auto-escalate when `tainted=true` AND verdict ∈ {confirmed, rejected}
- Stamp every verdict with provenance (provider_id, upstream_*, taint) pulled
  from the provider_registry.
- Validate every verdict against verdict_schema before returning.
- Build a `run_manifest` that carries `schema_version` + `registry_version`
  end-to-end (per orchestration §7).

Boot guard: __init__ calls assert_opt1_migration_complete() so no runner can
come up with legacy OPENAI_API_KEY/BASE leaking into verdicts.
"""

from __future__ import annotations
import json
import logging
import os
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from aios.core.provider_registry import ProviderRegistry, Provider
from aios.core.verdict_schema import validate_verdict
from aios.core.env_migration_guard import assert_opt1_migration_complete
from aios.core.review_hooks import HookDispatcher, ReviewHook

log = logging.getLogger("aios.core.review_runner")

# Business version of the verdict schema shape · bump when adding / removing
# required fields. Not the jsonschema draft identifier.
SCHEMA_VERSION_DEFAULT = "1.0"

# Verdict enum values that represent a committed call (i.e. not "insufficient"
# or transitional states). Used by tainted auto-escalation rule.
COMMITTED_VERDICTS = {"confirmed", "rejected"}

# usage_mode values that are NOT adjudicating · charter §R5.1 + CN layer §6.
# A reviewer with these modes never enters Phase 2 tally or Phase 5 dispute queue.
# Single source of truth for aggregate_votes() and compute_dispute_queue() —
# do not duplicate this set inside function bodies, or the two paths drift.
NON_ADJUDICATING_USAGE_MODES = frozenset({"style_learning", "corpus_mining", "dispute_review"})


def _is_adjudicating_voter(verdict: dict) -> bool:
    """Shared predicate: does this verdict count as an adjudication-eligible voter?

    Returns True iff:
      1. reviewer_role == "voter"  (oracle_only / final_judge never vote)
      2. usage_mode ∉ {style_learning, corpus_mining, dispute_review}
         (default "adjudication" when absent)
    """
    if verdict.get("reviewer_role") != "voter":
        return False
    return verdict.get("usage_mode", "adjudication") not in NON_ADJUDICATING_USAGE_MODES


# ─────────── runtime types ───────────

@dataclass
class RegisteredReviewer:
    """A reviewer instance · provider_id must match a registry entry.

    `call_fn(claim)` returns a partial verdict dict — the runner fills in
    provenance, tainted/taint_reasons, run_id, schema_version, timestamp, etc.
    `call_fn` failures are captured separately (not counted as agreement)."""
    provider_id: str
    reviewer_role: str              # "voter" | "oracle_only" | "final_judge"
    call_fn: Callable[[dict], dict]
    enabled: bool = True


@dataclass
class ReviewerFailure:
    """Recorded when a reviewer's call_fn raised or returned an invalid verdict.

    Not merged into verdict list · not counted as implicit agreement
    (per checklist P2)."""
    provider_id: str
    reviewer_role: str
    claim_id: str
    error_flavor: str               # e.g. "call_fn_exception", "schema_violation"
    error_detail: str


@dataclass
class AggregatedVote:
    """Outcome of Phase 5 vote aggregation for one claim."""
    claim_id: str
    independent_votes: int                # distinct vote groups (oracle_only excluded)
    verdict_tally: Dict[str, int]         # verdict → independent-vote count
    majority_verdict: Optional[str]       # None if tie
    per_group_verdicts: Dict[str, str]    # vote_group → one representative verdict


# ─────────── runner ───────────

class ReviewRunner:
    def __init__(
        self,
        registry: ProviderRegistry,
        schema: dict,
        run_id: Optional[str] = None,
        proposal_source: str = "unknown",
        schema_version: str = SCHEMA_VERSION_DEFAULT,
        hooks: Optional[HookDispatcher] = None,
    ):
        # Boot-time fail-fast · no runner can exist with legacy OPENAI_API_KEY
        # polluting downstream verdicts' provenance.
        assert_opt1_migration_complete()

        self.registry = registry
        self.schema = schema
        self.run_id = run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        self.proposal_source = proposal_source
        self.schema_version = schema_version

        self._reviewers: List[RegisteredReviewer] = []
        self._failures: List[ReviewerFailure] = []
        self._hooks: HookDispatcher = hooks or HookDispatcher()

    # ─────────── hooks ───────────

    def attach_hook(self, hook: ReviewHook) -> None:
        """Register a ReviewHook · fires around every reviewer.call_fn."""
        self._hooks.register(hook)

    @property
    def hooks(self) -> HookDispatcher:
        return self._hooks

    # ─────────── reviewer registration ───────────

    def register_reviewer(self, reviewer: RegisteredReviewer) -> None:
        if reviewer.reviewer_role not in {"voter", "oracle_only", "final_judge"}:
            raise ValueError(f"invalid reviewer_role: {reviewer.reviewer_role}")
        if self.registry.get_provider(reviewer.provider_id) is None:
            raise ValueError(
                f"reviewer provider_id '{reviewer.provider_id}' not in registry · "
                f"register the provider first"
            )
        self._reviewers.append(reviewer)

    def enabled_reviewers(self) -> List[RegisteredReviewer]:
        return [r for r in self._reviewers if r.enabled]

    def oracle_only_reviewers(self) -> List[RegisteredReviewer]:
        return [r for r in self.enabled_reviewers() if r.reviewer_role == "oracle_only"]

    def voter_reviewers(self) -> List[RegisteredReviewer]:
        return [r for r in self.enabled_reviewers() if r.reviewer_role == "voter"]

    # ─────────── fan-out ───────────

    def review_claim(self, claim: dict) -> List[dict]:
        """Run all enabled reviewers against one claim · return stamped verdicts.

        `claim` must contain `claim_id`. Failed reviewer calls are recorded
        in self._failures rather than merged into the verdict list."""
        claim_id = claim.get("claim_id")
        if not claim_id:
            raise ValueError("claim missing claim_id")

        verdicts: List[dict] = []
        for reviewer in self.enabled_reviewers():
            self._hooks.pre(claim, reviewer.provider_id, reviewer.reviewer_role, self.run_id)
            t0 = time.monotonic()
            try:
                partial = reviewer.call_fn(claim)
            except Exception as e:
                elapsed_ms = (time.monotonic() - t0) * 1000
                self._hooks.post(None, reviewer.provider_id, reviewer.reviewer_role,
                                 self.run_id, elapsed_ms, error=e)
                self._failures.append(ReviewerFailure(
                    provider_id=reviewer.provider_id,
                    reviewer_role=reviewer.reviewer_role,
                    claim_id=claim_id,
                    error_flavor="call_fn_exception",
                    error_detail=f"{type(e).__name__}: {str(e)[:200]}",
                ))
                continue

            elapsed_ms = (time.monotonic() - t0) * 1000
            stamped = self._stamp(reviewer, claim_id, partial)
            ok, errors = validate_verdict(stamped, self.schema)
            if not ok:
                self._hooks.post(stamped, reviewer.provider_id, reviewer.reviewer_role,
                                 self.run_id, elapsed_ms,
                                 error=ValueError("schema_violation"))
                self._failures.append(ReviewerFailure(
                    provider_id=reviewer.provider_id,
                    reviewer_role=reviewer.reviewer_role,
                    claim_id=claim_id,
                    error_flavor="schema_violation",
                    error_detail=" | ".join(errors[:3]),
                ))
                continue
            self._hooks.post(stamped, reviewer.provider_id, reviewer.reviewer_role,
                             self.run_id, elapsed_ms, error=None)
            verdicts.append(stamped)
        return verdicts

    # ─────────── provenance stamping ───────────

    def _stamp(self, reviewer: RegisteredReviewer, claim_id: str, partial: dict) -> dict:
        """Fill in identity + provenance + taint from registry + partial verdict.

        The reviewer is expected to provide: verdict, confidence, evidence,
        optionally severity/note/model_alias. Everything else is stamped here."""
        provider = self.registry.get_provider(reviewer.provider_id)
        assert provider is not None  # guaranteed by register_reviewer

        stamped = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "claim_id": claim_id,
            "proposal_source": self.proposal_source,
            "reviewer": partial.get("reviewer", reviewer.provider_id),
            "reviewer_role": reviewer.reviewer_role,
            "provider_id": provider.provider_id,
            "provider_class": provider.provider_class,
            "independent_vote_group": provider.independent_vote_group,
            "upstream_provider": partial.get("upstream_provider") or provider.upstream_provider,
            "upstream_model": partial.get("upstream_model") or provider.upstream_model_default,
            "endpoint_url": partial.get("endpoint_url") or provider.endpoint_url,
            "auth_type": partial.get("auth_type") or provider.auth_type,
            "response_flavor": partial.get("response_flavor") or provider.response_flavor,
            "timestamp": partial.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        # Copy mandatory verdict/evidence fields from partial
        for k in ("verdict", "confidence", "evidence"):
            if k in partial:
                stamped[k] = partial[k]
        # Optional passthrough fields · incl. CN learning layer tags (charter §5)
        for k in ("severity", "note", "model_alias", "request_id", "latency_ms",
                  "error_flavor", "usage_mode", "domain_tag", "task_shape",
                  "language", "yijing_quality", "tokens_in", "tokens_out"):
            if k in partial:
                stamped[k] = partial[k]
        # Default usage_mode for any voter that didn't declare one
        if stamped.get("reviewer_role") == "voter" and "usage_mode" not in stamped:
            stamped["usage_mode"] = "adjudication"

        # Taint decision from registry · may add or override reasons from partial
        tainted, reasons = self.registry.should_taint(stamped)
        partial_reasons = partial.get("taint_reasons") or []
        all_reasons = sorted(set(reasons) | set(partial_reasons))
        stamped["tainted"] = bool(tainted or partial.get("tainted", False))
        if all_reasons:
            stamped["taint_reasons"] = all_reasons
        return stamped

    # ─────────── Phase 5 · vote aggregation ───────────

    def aggregate_votes(self, verdicts: List[dict]) -> AggregatedVote:
        """Collapse votes by `independent_vote_group`, exclude oracle_only reviewers.

        Rules:
        1. Only `reviewer_role == 'voter'` verdicts count.
        2. Multiple verdicts in the same vote_group collapse to ONE vote
           (per orchestration §'Weighting Rules': shared relay endpoint = shared group).
        3. Within a group, the representative verdict is the first one seen
           (deterministic by insertion order · caller can sort if needed).
        """
        if not verdicts:
            return AggregatedVote(claim_id="", independent_votes=0,
                                  verdict_tally={}, majority_verdict=None,
                                  per_group_verdicts={})

        claim_id = verdicts[0].get("claim_id", "")
        # CN layer §R5.1 · usage_mode gating handled by _is_adjudicating_voter()
        # (shared with compute_dispute_queue so the two paths cannot drift).
        voters_only = [v for v in verdicts if _is_adjudicating_voter(v)]
        per_group: Dict[str, str] = {}
        for v in voters_only:
            group = v.get("independent_vote_group", "_no_group")
            if group not in per_group:
                per_group[group] = v.get("verdict", "")

        tally = Counter(per_group.values())
        majority = None
        if tally:
            top_count = tally.most_common(1)[0][1]
            top_verdicts = [v for v, c in tally.items() if c == top_count]
            majority = top_verdicts[0] if len(top_verdicts) == 1 else None  # tie → None

        return AggregatedVote(
            claim_id=claim_id,
            independent_votes=len(per_group),
            verdict_tally=dict(tally),
            majority_verdict=majority,
            per_group_verdicts=per_group,
        )

    # ─────────── Phase 6 · dispute queue ───────────

    def compute_dispute_queue(self, verdicts: List[dict]) -> List[dict]:
        """Return the subset of verdicts that must be reviewed in Phase 6.

        Triggers:
        - auto-escalate: tainted=true AND verdict ∈ {confirmed, rejected}
        - native-vs-native disagreement (two natives with different verdicts)
        - no-majority among voters (tie)
        - relay verdict disagrees with native and is tainted
        """
        queue: List[dict] = []
        # Map (claim_id, provider_id) → enqueued verdict dict · lets subsequent
        # triggers append more dispute_reasons to the SAME entry instead of being
        # short-circuited (fix for 2026-04-19 audit · multi-reason accumulation).
        queued_by_key: Dict[tuple, dict] = {}

        def push(v: dict, reason: str) -> None:
            key = (v.get("claim_id"), v.get("provider_id"))
            existing_entry = queued_by_key.get(key)
            if existing_entry is not None:
                # Already queued · append reason (dedup) · do not double-enqueue
                reasons = existing_entry.setdefault("dispute_reasons", [])
                if reason not in reasons:
                    reasons.append(reason)
                return
            v2 = dict(v)
            prior = list(v2.get("dispute_reasons") or [])
            prior.append(reason)
            v2["dispute_reasons"] = prior
            queued_by_key[key] = v2
            queue.append(v2)

        # Group verdicts by claim_id for disagreement analysis
        by_claim: Dict[str, List[dict]] = {}
        for v in verdicts:
            by_claim.setdefault(v.get("claim_id", ""), []).append(v)

        for claim_id, claim_verdicts in by_claim.items():
            # Use the shared predicate · identical semantics to aggregate_votes.
            # Prior bug: filter was "reviewer_role=='voter'" only, so
            # style_learning / corpus_mining / dispute_review verdicts could
            # still trigger tainted_committed_auto_escalate even though they
            # never count as votes. Fixed 2026-04-19.
            voters = [v for v in claim_verdicts if _is_adjudicating_voter(v)]

            # Rule 1 · auto-escalate on tainted + committed verdict (per spec)
            for v in voters:
                if v.get("tainted") and v.get("verdict") in COMMITTED_VERDICTS:
                    push(v, "tainted_committed_auto_escalate")

            # Rule 2 · native disagreement
            native_voters = [v for v in voters if v.get("provider_class") == "native"]
            native_verdict_set = {v.get("verdict") for v in native_voters}
            if len(native_verdict_set) > 1:
                for v in native_voters:
                    push(v, "native_disagreement")

            # Rule 3 · relay disagrees with native majority AND is tainted
            if native_voters:
                native_majority_tally = Counter(v.get("verdict") for v in native_voters)
                if native_majority_tally:
                    native_majority = native_majority_tally.most_common(1)[0][0]
                    for v in voters:
                        if v.get("provider_class") == "relay" and v.get("tainted") and v.get("verdict") != native_majority:
                            push(v, "tainted_relay_disagrees_native")

            # Rule 4 · no majority (tie) among voters
            if voters:
                agg = self.aggregate_votes(claim_verdicts)
                if agg.independent_votes >= 2 and agg.majority_verdict is None:
                    for v in voters:
                        push(v, "no_majority_tie")

        return queue

    # ─────────── Phase 7 prep · run manifest ───────────

    def build_run_manifest(self, verdicts: List[dict]) -> dict:
        """Assemble the run_manifest required by orchestration §7.

        Guarantees `schema_version` + `registry_version` are both present
        (small-nine audit point 4)."""
        reviewers_listed = [
            {
                "provider_id": r.provider_id,
                "reviewer_role": r.reviewer_role,
                "enabled": r.enabled,
            }
            for r in self._reviewers
        ]
        enabled_provider_ids = [r.provider_id for r in self.enabled_reviewers()]
        # Providers in registry but not registered as reviewers → "missing" (informational)
        registered_ids = {r.provider_id for r in self._reviewers}
        missing_providers = [
            p.provider_id for p in self.registry.enabled_providers()
            if p.provider_id not in registered_ids
        ]
        failed_reviewers = [
            {"provider_id": f.provider_id, "reviewer_role": f.reviewer_role,
             "claim_id": f.claim_id, "error_flavor": f.error_flavor,
             "error_detail": f.error_detail}
            for f in self._failures
        ]

        return {
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "registry_version": str(self.registry.version),
            "registry_updated_at": self.registry.updated_at,
            "proposal_source": self.proposal_source,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "reviewer_list": reviewers_listed,
            "enabled_providers": enabled_provider_ids,
            "missing_providers": missing_providers,
            "oracle_only_reviewers": [r.provider_id for r in self.oracle_only_reviewers()],
            "voter_reviewers": [r.provider_id for r in self.voter_reviewers()],
            "failed_reviewers": failed_reviewers,
            "verdict_count": len(verdicts),
            "final_judge": self.registry.review_policy.final_judge,
        }

    # ─────────── persistence (minimal · orchestration file set) ───────────

    def save_verdicts(self, verdicts: List[dict], out_dir: Path) -> List[Path]:
        """Persist verdicts to `<out_dir>/verdicts/` · one file per verdict.

        Deterministic filename: `<claim_id>_<provider_id>.json`."""
        target_dir = out_dir / "verdicts"
        target_dir.mkdir(parents=True, exist_ok=True)
        paths: List[Path] = []
        for v in verdicts:
            name = f"{v['claim_id']}_{v['provider_id']}.json"
            p = target_dir / name
            p.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
            paths.append(p)
        return paths

    def save_manifest(self, manifest: dict, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "run_manifest.json"
        p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return p
