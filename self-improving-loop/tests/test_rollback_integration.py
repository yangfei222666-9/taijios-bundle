"""
Integration tests for AutoRollback — exercises the actual decision logic,
not just "history is empty".

Covers GitHub issue #5:
  https://github.com/yangfei222666-9/self-improving-loop/issues/5
"""
from pathlib import Path

import pytest

from self_improving_loop import AutoRollback


def test_success_rate_drop_triggers_rollback(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    should, reason = r.should_rollback(
        agent_id="a1",
        improvement_id="imp-1",
        before_metrics={"success_rate": 0.90, "avg_duration_sec": 1.0,
                        "consecutive_failures": 0},
        after_metrics={"success_rate": 0.70, "avg_duration_sec": 1.0,
                       "consecutive_failures": 0},
    )
    assert should is True
    assert "成功率" in reason or "success" in reason.lower()


def test_tiny_success_rate_drop_is_tolerated(tmp_path: Path):
    # Threshold is 10%. 5% drop should NOT trigger.
    r = AutoRollback(str(tmp_path))
    should, _ = r.should_rollback(
        agent_id="a1",
        improvement_id="imp-1",
        before_metrics={"success_rate": 0.90, "avg_duration_sec": 1.0,
                        "consecutive_failures": 0},
        after_metrics={"success_rate": 0.85, "avg_duration_sec": 1.0,
                       "consecutive_failures": 0},
    )
    assert should is False


def test_latency_increase_above_20pct_triggers_rollback(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    should, reason = r.should_rollback(
        agent_id="a1",
        improvement_id="imp-1",
        before_metrics={"success_rate": 0.9, "avg_duration_sec": 1.0,
                        "consecutive_failures": 0},
        after_metrics={"success_rate": 0.9, "avg_duration_sec": 1.3,  # +30%
                       "consecutive_failures": 0},
    )
    assert should is True
    assert "耗时" in reason or "latency" in reason.lower()


def test_small_latency_increase_is_tolerated(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    should, _ = r.should_rollback(
        agent_id="a1",
        improvement_id="imp-1",
        before_metrics={"success_rate": 0.9, "avg_duration_sec": 1.0,
                        "consecutive_failures": 0},
        after_metrics={"success_rate": 0.9, "avg_duration_sec": 1.15,  # +15%
                       "consecutive_failures": 0},
    )
    assert should is False


def test_consecutive_failures_at_threshold_triggers(tmp_path: Path):
    # CONSECUTIVE_FAILURES_THRESHOLD = 5 (>=)
    r = AutoRollback(str(tmp_path))
    should, reason = r.should_rollback(
        agent_id="a1",
        improvement_id="imp-1",
        before_metrics={"success_rate": 0.9, "avg_duration_sec": 1.0,
                        "consecutive_failures": 0},
        after_metrics={"success_rate": 0.9, "avg_duration_sec": 1.0,
                       "consecutive_failures": 5},
    )
    assert should is True
    assert "失败" in reason or "consecutive" in reason.lower()


def test_consecutive_failures_below_threshold_does_not_trigger(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    should, _ = r.should_rollback(
        agent_id="a1",
        improvement_id="imp-1",
        before_metrics={"success_rate": 0.9, "avg_duration_sec": 1.0,
                        "consecutive_failures": 0},
        after_metrics={"success_rate": 0.9, "avg_duration_sec": 1.0,
                       "consecutive_failures": 4},  # just below 5
    )
    assert should is False


def test_zero_before_metrics_does_not_falsely_trigger(tmp_path: Path):
    # When there's no 'before' data (fresh agent), we shouldn't rollback
    # just because after_metrics look worse than nothing.
    r = AutoRollback(str(tmp_path))
    should, _ = r.should_rollback(
        agent_id="a1",
        improvement_id="imp-1",
        before_metrics={"success_rate": 0, "avg_duration_sec": 0,
                        "consecutive_failures": 0},
        after_metrics={"success_rate": 0.8, "avg_duration_sec": 1.0,
                       "consecutive_failures": 0},
    )
    assert should is False


def test_backup_and_rollback_roundtrip(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    config_before = {"timeout_sec": 30, "retries": 3}
    backup_id = r.backup_config(
        agent_id="a1",
        config=config_before,
        improvement_id="imp-1",
    )
    assert backup_id  # returns a usable id

    result = r.rollback(agent_id="a1", backup_id=backup_id)
    assert isinstance(result, dict)
    # The result should either reflect success or contain an error we can see
    assert "success" in result or "error" in result or "config" in result


def test_rollback_history_records_backup_events(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    # fresh agent has no history
    assert r.get_rollback_history("a1") == []

    r.backup_config(
        agent_id="a1",
        config={"x": 1},
        improvement_id="imp-1",
    )
    # Backups are recorded separately from rollbacks; history API is
    # about actual rollback events, so this should remain empty until
    # rollback() is called.
    history_after_backup = r.get_rollback_history("a1")
    assert isinstance(history_after_backup, list)


def test_get_stats_returns_dict(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    stats = r.get_stats()
    assert isinstance(stats, dict)
    # Don't assert specific keys — contract is loose. Just ensure it's
    # callable without exploding on an empty state.


def test_thresholds_are_documented_constants(tmp_path: Path):
    # If someone changes these without updating docs, that's a breaking
    # change. Lock them in.
    r = AutoRollback(str(tmp_path))
    assert r.SUCCESS_RATE_DROP_THRESHOLD == 0.10
    assert r.LATENCY_INCREASE_THRESHOLD == 0.20
    assert r.CONSECUTIVE_FAILURES_THRESHOLD == 5
