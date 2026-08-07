"""Unit tests for `frob.verify._worker` (T-1688)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.verify._watermark import load_watermark, queue_status, record_intent
from frob.verify._worker import (
    CoalescingWorker,
    WorkerError,
    run_coalesced_verification,
)


# frob:waive WIRE001 reason="a private test-seed helper used only by this file's own \
# test methods below -- there is no production caller to wire it to by design, \
# mirroring tests/unit/test_mutation_sweep_queue.py's identical _make_ticket \
# precedent" permanent="true"
def _enqueue_n(root: Path, n: int) -> None:
    """Append `n` distinct queue entries to `root`'s verify queue."""
    for i in range(n):
        record_intent(
            root,
            commit_sha=f"c{i}",
            ticket_id=f"T-{1000 + i}",
            touched_symbols=(f"src/frob/mod{i}.py::fn{i}",),
            profile="rapid",
        )


class TestRunCoalescedVerification:
    """The coalescing contract: read the queue once, verify its tip ONCE,
    never loop over entries."""

    def test_empty_queue_is_a_noop(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_worker.py::run_coalesced_verification kind="unit"
        calls: list[str] = []
        result = run_coalesced_verification(
            tmp_path, verify_fn=lambda root, sha: calls.append(sha) or frozenset()
        )
        assert result.is_ok
        assert result.danger_ok.status == "empty"
        assert calls == []

    def test_five_queued_entries_call_verify_exactly_once(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_worker.py::run_coalesced_verification kind="unit"
        _enqueue_n(tmp_path, 5)
        calls: list[str] = []

        def counting_verify(root: Path, sha: str) -> frozenset[tuple[str, str]]:
            calls.append(sha)
            return frozenset()

        result = run_coalesced_verification(tmp_path, verify_fn=counting_verify)
        assert result.is_ok
        # Exactly ONE verification call, no matter how many entries were
        # queued -- the whole point of coalescing, not iterating.
        assert len(calls) == 1
        # And it verified the TIP (the last-appended entry), not the head.
        assert calls[0] == "c4"

    def test_unmeasurable_never_advances_watermark(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_worker.py::run_coalesced_verification kind="unit"
        _enqueue_n(tmp_path, 3)
        result = run_coalesced_verification(tmp_path, verify_fn=lambda root, sha: None)
        assert result.is_err
        assert result.danger_err is WorkerError.Unmeasurable
        watermark = load_watermark(tmp_path)
        assert watermark.is_ok
        assert watermark.danger_ok is None
        # The queue is untouched too -- nothing was compacted away.
        remaining = queue_status(tmp_path)
        assert remaining.is_ok
        assert len(remaining.danger_ok) == 3

    def test_first_run_establishes_baseline_without_advancing(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_worker.py::run_coalesced_verification kind="unit"
        _enqueue_n(tmp_path, 1)
        result = run_coalesced_verification(
            tmp_path, verify_fn=lambda root, sha: frozenset({("RULE1", "a.py")})
        )
        assert result.is_ok
        assert result.danger_ok.status == "baseline-established"
        assert result.danger_ok.advanced_watermark is False
        watermark = load_watermark(tmp_path)
        assert watermark.is_ok
        assert watermark.danger_ok is None

    def test_new_findings_file_a_ticket_and_do_not_advance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/verify/_worker.py::run_coalesced_verification kind="unit"
        from frob.app.ticket_runner import _rapid_sweep

        _enqueue_n(tmp_path, 1)
        # Seed a rolling baseline directly (bypassing a real first run).
        _rapid_sweep._write_baseline(tmp_path, frozenset({("RULE1", "a.py")}), "c0")

        filed_calls: list[object] = []

        def fake_file_ticket(root, final_id, commit_sha, new_findings):  # noqa: ANN001
            filed_calls.append((final_id, commit_sha, new_findings))
            return "T-9999"

        monkeypatch.setattr(_rapid_sweep, "_file_regression_ticket", fake_file_ticket)
        result = run_coalesced_verification(
            tmp_path,
            verify_fn=lambda root, sha: frozenset(
                {("RULE1", "a.py"), ("RULE2", "b.py")}
            ),
        )

        assert result.is_ok
        assert result.danger_ok.status == "red"
        assert result.danger_ok.filed_ticket == "T-9999"
        assert result.danger_ok.advanced_watermark is False
        assert len(filed_calls) == 1
        watermark = load_watermark(tmp_path)
        assert watermark.is_ok
        assert watermark.danger_ok is None

    def test_clean_run_advances_watermark_and_compacts_queue(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_worker.py::run_coalesced_verification kind="unit"
        from frob.app.ticket_runner import _rapid_sweep

        _enqueue_n(tmp_path, 5)
        _rapid_sweep._write_baseline(tmp_path, frozenset({("RULE1", "a.py")}), "seed")

        result = run_coalesced_verification(
            tmp_path,
            verify_fn=lambda root, sha: frozenset({("RULE1", "a.py")}),
        )
        assert result.is_ok
        outcome = result.danger_ok
        assert outcome.status == "green"
        assert outcome.advanced_watermark is True
        assert outcome.commit_sha == "c4"

        watermark = load_watermark(tmp_path)
        assert watermark.is_ok
        assert watermark.danger_ok is not None
        assert watermark.danger_ok.commit_sha == "c4"

        remaining = queue_status(tmp_path)
        assert remaining.is_ok
        assert remaining.danger_ok == ()

    def test_queue_unreadable_is_an_error(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_worker.py::run_coalesced_verification kind="unit"
        path = tmp_path / ".frob" / "verify-queue.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{", encoding="utf-8")
        result = run_coalesced_verification(tmp_path, verify_fn=lambda root, sha: frozenset())
        assert result.is_err
        assert result.danger_err is WorkerError.QueueUnreadable


class TestCoalescingWorker:
    """The trailing-edge debounce/periodic-floor decision logic, driven by
    an injectable clock -- never a real sleep."""

    def test_tick_with_nothing_pending_is_a_noop(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_worker.py::CoalescingWorker kind="unit"
        clock = [0.0]
        worker = CoalescingWorker(tmp_path, now_fn=lambda: clock[0])
        assert worker.tick() is None

    def test_notify_then_tick_before_deadline_does_not_run(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_worker.py::CoalescingWorker kind="unit"
        clock = [0.0]
        calls: list[str] = []
        worker = CoalescingWorker(
            tmp_path,
            debounce_window_s=90.0,
            periodic_floor_s=10_000.0,
            now_fn=lambda: clock[0],
            verify_fn=lambda root, sha: calls.append(sha) or frozenset(),
        )
        worker.notify()
        clock[0] = 30.0  # well under the 90s debounce window
        assert worker.tick() is None
        assert calls == []

    def test_notify_then_tick_after_deadline_runs_once(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_worker.py::CoalescingWorker kind="unit"
        _enqueue_n(tmp_path, 1)
        clock = [0.0]
        calls: list[str] = []
        worker = CoalescingWorker(
            tmp_path,
            debounce_window_s=90.0,
            periodic_floor_s=10_000.0,
            now_fn=lambda: clock[0],
            verify_fn=lambda root, sha: calls.append(sha) or frozenset(),
        )
        worker.notify()
        clock[0] = 91.0  # past the 90s debounce window
        result = worker.tick()
        assert result is not None
        assert result.is_ok
        assert len(calls) == 1
        # A second tick right after, with nothing new pending, is a no-op.
        assert worker.tick() is None
        assert len(calls) == 1

    def test_repeated_notify_pushes_the_deadline_out(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_worker.py::CoalescingWorker kind="unit"
        # T-1688's own acceptance shape: 5 notifies inside the debounce
        # window must still only ever produce one run once ticked past
        # the LAST notify's own deadline.
        _enqueue_n(tmp_path, 1)
        clock = [0.0]
        calls: list[str] = []
        worker = CoalescingWorker(
            tmp_path,
            debounce_window_s=90.0,
            periodic_floor_s=10_000.0,
            now_fn=lambda: clock[0],
            verify_fn=lambda root, sha: calls.append(sha) or frozenset(),
        )
        for t in (0.0, 20.0, 40.0, 60.0, 80.0):
            clock[0] = t
            worker.notify()
            assert worker.tick() is None  # still inside the window each time
        clock[0] = 80.0 + 91.0  # quiet for >90s since the LAST notify (t=80)
        result = worker.tick()
        assert result is not None
        assert result.is_ok
        assert len(calls) == 1

    def test_periodic_floor_forces_a_run_under_continuous_notify(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/verify/_worker.py::CoalescingWorker kind="unit"
        _enqueue_n(tmp_path, 1)
        clock = [0.0]
        calls: list[str] = []
        worker = CoalescingWorker(
            tmp_path,
            debounce_window_s=90.0,
            periodic_floor_s=200.0,
            now_fn=lambda: clock[0],
            verify_fn=lambda root, sha: calls.append(sha) or frozenset(),
        )
        # A steady stream of notifies every 30s never lets the debounce
        # window go quiet -- but the periodic floor must still force a
        # run once 200s of pending time has elapsed.
        for t in (0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0):
            clock[0] = t
            worker.notify()
            worker.tick()
        assert len(calls) == 1
