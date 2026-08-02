"""Unit tests for `frob.tickets._land_queue` (T-1345)."""

from __future__ import annotations

from pathlib import Path

from typani.result import Err, Ok

from frob.tickets._land_queue import (
    QueueError,
    drain_next,
    enqueue,
    queue_status,
)
from frob.tickets._models import LandError, LandReport


def _report(ticket_id: str, commit_sha: str = "deadbeef") -> LandReport:
    return LandReport(
        ticket_id=ticket_id,
        final_id=ticket_id,
        dry_run=False,
        wip_committed=True,
        merged_main_into_worktree=True,
        ledger_spliced=True,
        commit_sha=commit_sha,
    )


class TestEnqueue:
    """T-1345: `enqueue` appends a `queued` entry and returns immediately."""

    def test_enqueue_returns_queued_entry(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::enqueue kind="unit"
        result = enqueue(tmp_path, "T-0001", tmp_path / "wt", "series-branch")
        assert result.is_ok
        entry = result.danger_ok
        assert entry.ticket_id == "T-0001"
        assert entry.branch == "series-branch"
        assert entry.status == "queued"

    def test_enqueue_persists_across_calls(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::enqueue kind="unit"
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        enqueue(tmp_path, "T-0002", tmp_path / "wt", "b2")
        loaded = queue_status(tmp_path)
        assert loaded.is_ok
        ids = [e.ticket_id for e in loaded.danger_ok]
        assert ids == ["T-0001", "T-0002"]

    def test_duplicate_enqueue_refused(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::enqueue kind="unit"
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        result = enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1-retry")
        assert result.is_err
        assert result.danger_err is QueueError.AlreadyQueued

    def test_enqueue_after_landed_is_allowed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::enqueue kind="unit"
        # A ticket that already landed once must be re-enqueue-able (e.g. a
        # second wave of work on the same ticket id in a fresh worktree) --
        # only "queued"/"landing" entries block a duplicate.
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        drain_next(tmp_path, lambda e: Ok(_report(e.ticket_id)))
        result = enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1-again")
        assert result.is_ok


class TestQueueStatus:
    """T-1345: `queue_status` is a read-only snapshot."""

    def test_empty_queue_is_empty_tuple(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::queue_status kind="unit"
        result = queue_status(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()


class TestDrainNext:
    """T-1345: `drain_next` pops the oldest `queued` entry, runs it through
    `land_fn`, and records the outcome without dropping it."""

    def test_empty_queue_returns_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::drain_next kind="unit"
        result = drain_next(tmp_path, lambda e: Ok(_report(e.ticket_id)))
        assert result.is_ok
        assert result.danger_ok is None

    def test_drains_fifo_order(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::drain_next kind="unit"
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        enqueue(tmp_path, "T-0002", tmp_path / "wt", "b2")
        seen: list[str] = []

        def _land_fn(entry):  # noqa: ANN001, ANN202
            seen.append(entry.ticket_id)
            return Ok(_report(entry.ticket_id))

        drain_next(tmp_path, _land_fn)
        drain_next(tmp_path, _land_fn)
        assert seen == ["T-0001", "T-0002"]

    def test_successful_land_marks_entry_landed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::drain_next kind="unit"
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        result = drain_next(tmp_path, lambda e: Ok(_report(e.ticket_id, "cafebabe")))
        assert result.is_ok
        entry = result.danger_ok
        assert entry is not None
        assert entry.status == "landed"
        assert entry.commit_sha == "cafebabe"
        # T-1345: the queue never drops an entry silently -- it stays
        # present, tagged with its outcome.
        remaining = queue_status(tmp_path).danger_ok
        assert len(remaining) == 1
        assert remaining[0].status == "landed"

    def test_failed_land_rejected_back_not_retried(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::drain_next kind="unit"
        # T-1345 acceptance[1]: a queued branch that no longer merges
        # cleanly is handled by a declared policy (reject back, dequeue,
        # never silently dropped) rather than silently vanishing.
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        result = drain_next(
            tmp_path,
            lambda e: Err(LandError.MergeConflict),  # noqa: ARG005
        )
        assert result.is_ok
        entry = result.danger_ok
        assert entry is not None
        assert entry.status == "failed"
        assert entry.error == LandError.MergeConflict.value
        remaining = queue_status(tmp_path).danger_ok
        assert len(remaining) == 1
        assert remaining[0].status == "failed"

    def test_failed_entry_is_not_redrained(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::drain_next kind="unit"
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        drain_next(tmp_path, lambda e: Err(LandError.MergeConflict))  # noqa: ARG005
        # Nothing else queued -- a second drain must find no candidate,
        # never automatically retry the failed entry.
        result = drain_next(tmp_path, lambda e: Ok(_report(e.ticket_id)))
        assert result.is_ok
        assert result.danger_ok is None

    def test_second_entry_still_drains_after_first_failure(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::drain_next kind="unit"
        # A failure in one entry must not block the drainer from reaching
        # later entries -- concurrency ceiling from T-1345's own body: a
        # blocked queue defeats the whole point.
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        enqueue(tmp_path, "T-0002", tmp_path / "wt", "b2")

        def _land_fn(entry):  # noqa: ANN001, ANN202
            if entry.ticket_id == "T-0001":
                return Err(LandError.MergeConflict)
            return Ok(_report(entry.ticket_id))

        drain_next(tmp_path, _land_fn)
        result = drain_next(tmp_path, _land_fn)
        assert result.is_ok
        entry = result.danger_ok
        assert entry is not None
        assert entry.ticket_id == "T-0002"
        assert entry.status == "landed"


class TestStoreCorrupt:
    """T-1345: a corrupt queue file fails loudly rather than silently
    resetting to empty."""

    def test_corrupt_queue_file_errors(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land_queue.py::queue_status kind="unit"
        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "land-queue.json").write_text("not json at all")
        result = queue_status(tmp_path)
        assert result.is_err
        assert result.danger_err is QueueError.StoreCorrupt
