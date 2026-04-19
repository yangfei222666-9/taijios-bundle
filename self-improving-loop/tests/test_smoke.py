"""
Smoke tests — verify imports, basic instantiation, and core execution path.
These are intentionally minimal; the full 17-test suite lives in the parent
TaijiOS repo and is being ported here in follow-up PRs.
"""
import json
import tempfile
from pathlib import Path

import pytest

from self_improving_loop import (
    SelfImprovingLoop,
    AutoRollback,
    AdaptiveThreshold,
    TelegramNotifier,
    __version__,
)


def test_version_is_set():
    assert __version__
    assert __version__.count(".") >= 1  # at least major.minor


def test_imports_resolve():
    # If any of these blow up, the package is broken at install-time
    assert SelfImprovingLoop
    assert AutoRollback
    assert AdaptiveThreshold
    assert TelegramNotifier


def test_loop_instantiates_with_tempdir(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    assert loop.data_dir == tmp_path
    assert loop.state_file.parent == tmp_path
    assert loop.auto_rollback is not None
    assert loop.adaptive_threshold is not None
    assert loop.notifier is not None
    # alias exposed to README-facing users
    assert loop.rollback is loop.auto_rollback


def test_execute_with_improvement_records_success(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    result = loop.execute_with_improvement(
        agent_id="smoke-agent",
        task="trivial task",
        execute_fn=lambda: {"ok": True},
    )
    assert result["success"] is True
    assert result["result"] == {"ok": True}
    assert result["error"] is None
    assert result["duration_sec"] >= 0
    assert result["improvement_triggered"] is False  # single success, no trigger
    assert result["rollback_executed"] is None

    # Trace file should have been written
    traces_file = tmp_path / "traces.jsonl"
    assert traces_file.exists()
    lines = traces_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["agent_id"] == "smoke-agent"
    assert row["success"] is True


def test_execute_with_improvement_captures_failure(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))

    def bad():
        raise ValueError("boom")

    result = loop.execute_with_improvement(
        agent_id="fail-agent",
        task="will fail",
        execute_fn=bad,
    )
    assert result["success"] is False
    assert "boom" in (result["error"] or "")


def test_adaptive_threshold_returns_tuple(tmp_path: Path):
    t = AdaptiveThreshold(str(tmp_path))
    failure, window, cooldown = t.get_threshold("some-agent", task_history=[])
    # all three should be positive integers
    assert isinstance(failure, int) and failure > 0
    assert isinstance(window, int) and window > 0
    assert isinstance(cooldown, int) and cooldown > 0


def test_manual_threshold_overrides_adaptive(tmp_path: Path):
    t = AdaptiveThreshold(str(tmp_path))
    t.set_manual_threshold(
        "critical-agent",
        failure_threshold=1,
        analysis_window_hours=12,
        cooldown_hours=1,
        is_critical=True,
    )
    failure, window, cooldown = t.get_threshold("critical-agent", task_history=[])
    assert failure == 1
    assert window == 12
    assert cooldown == 1


def test_notifier_default_is_noninvasive(capsys, tmp_path: Path):
    # Default stub should never raise and should be replaceable.
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    loop.notifier.notify_improvement(
        agent_id="x", improvements_applied=1, details={"k": "v"}
    )
    # stub prints to stdout; we just assert it didn't crash
    captured = capsys.readouterr()
    assert "x" in captured.out or captured.out == ""  # either format is fine


def test_custom_notifier_subclass_is_honored(tmp_path: Path):
    received = []

    class MyNotifier(TelegramNotifier):
        def _send_message(self, message, priority="normal"):
            received.append((priority, message))

    loop = SelfImprovingLoop(data_dir=str(tmp_path), notifier=MyNotifier())
    loop.notifier.notify_improvement(
        agent_id="custom", improvements_applied=2, details=None
    )
    assert len(received) == 1
    priority, message = received[0]
    assert priority in ("normal", "high")
    assert "custom" in message


def test_get_improvement_stats_empty(tmp_path: Path):
    loop = SelfImprovingLoop(data_dir=str(tmp_path))
    stats = loop.get_improvement_stats()
    assert isinstance(stats, dict)
    # Just assert the shape; keys will be zero/empty
    assert "total_improvements" in stats or "total_rollbacks" in stats or stats == {}


def test_auto_rollback_history_is_empty_for_new_agent(tmp_path: Path):
    r = AutoRollback(str(tmp_path))
    history = r.get_rollback_history("never-seen-agent")
    assert isinstance(history, list)
    assert len(history) == 0
