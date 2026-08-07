"""Unit tests for `frob.verify._watermark` (T-1687)."""

from __future__ import annotations

from pathlib import Path

from frob.verify._watermark import (
    WatermarkError,
    advance_watermark,
    compact_queue,
    load_watermark,
    queue_status,
    record_intent,
)


class TestQueueStatus:
    """`queue_status`: a read-only snapshot of `.frob/verify-queue.json`."""

    def test_empty_queue_is_empty_tuple(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::queue_status kind="unit"
        result = queue_status(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

    def test_corrupt_queue_errors(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::queue_status kind="unit"
        path = tmp_path / ".frob" / "verify-queue.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{", encoding="utf-8")
        result = queue_status(tmp_path)
        assert result.is_err
        assert result.danger_err is WatermarkError.StoreCorrupt


class TestRecordIntent:
    """`record_intent`: append exactly one queue entry per call."""

    def test_appends_one_entry_with_resolvable_symbols(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::record_intent kind="unit"
        result = record_intent(
            tmp_path,
            commit_sha="deadbeef",
            ticket_id="T-0001",
            touched_symbols=("src/frob/foo.py::bar", "src/frob/foo.py::Baz.qux"),
            profile="rapid",
        )
        assert result.is_ok
        entry = result.danger_ok
        assert entry.commit_sha == "deadbeef"
        assert entry.ticket_id == "T-0001"
        assert entry.touched_symbols == (
            "src/frob/foo.py::bar",
            "src/frob/foo.py::Baz.qux",
        )
        assert entry.profile == "rapid"
        loaded = queue_status(tmp_path)
        assert loaded.is_ok
        assert len(loaded.danger_ok) == 1

    def test_persists_across_calls_in_order(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::record_intent kind="unit"
        record_intent(
            tmp_path,
            commit_sha="c1",
            ticket_id="T-0001",
            touched_symbols=("a::b",),
            profile="standard",
        )
        record_intent(
            tmp_path,
            commit_sha="c2",
            ticket_id="T-0002",
            touched_symbols=("c::d",),
            profile="standard",
        )
        loaded = queue_status(tmp_path)
        assert loaded.is_ok
        shas = [e.commit_sha for e in loaded.danger_ok]
        assert shas == ["c1", "c2"]

    def test_empty_touched_symbols_refused(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::record_intent kind="unit"
        result = record_intent(
            tmp_path,
            commit_sha="deadbeef",
            ticket_id="T-0001",
            touched_symbols=(),
            profile="rapid",
        )
        assert result.is_err
        assert result.danger_err is WatermarkError.EmptyTouchedSymbols
        loaded = queue_status(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok == ()

    def test_corrupt_queue_refuses_to_append(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::record_intent kind="unit"
        path = tmp_path / ".frob" / "verify-queue.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{", encoding="utf-8")
        result = record_intent(
            tmp_path,
            commit_sha="deadbeef",
            ticket_id="T-0001",
            touched_symbols=("a::b",),
            profile="rapid",
        )
        assert result.is_err
        assert result.danger_err is WatermarkError.StoreCorrupt
        # The corrupt file must be untouched, not silently overwritten.
        assert path.read_text(encoding="utf-8") == "not json{{{"


class TestLoadWatermark:
    """`load_watermark`: "cannot verify" is never "verified"."""

    def test_missing_file_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::load_watermark kind="unit"
        result = load_watermark(tmp_path)
        assert result.is_ok
        assert result.danger_ok is None

    def test_round_trips(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::load_watermark kind="unit"
        advance_watermark(
            tmp_path, commit_sha="deadbeef", run_id="run-1", baseline_digest="base-1"
        )
        result = load_watermark(tmp_path)
        assert result.is_ok
        watermark = result.danger_ok
        assert watermark is not None
        assert watermark.commit_sha == "deadbeef"
        assert watermark.run_id == "run-1"
        assert watermark.baseline_digest == "base-1"

    def test_corrupt_file_reads_as_none_not_verified(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::load_watermark kind="unit"
        path = tmp_path / ".frob" / "verify-watermark.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json{{{", encoding="utf-8")
        result = load_watermark(tmp_path)
        # Never Err, never a stale-looking record -- degrades to the SAME
        # Ok(None) a fresh, never-verified repo would return.
        assert result.is_ok
        assert result.danger_ok is None


class TestAdvanceWatermark:
    """`advance_watermark`: unconditionally overwrite the current record."""

    def test_advance_then_load_round_trips(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::advance_watermark kind="unit"
        result = advance_watermark(
            tmp_path, commit_sha="c1", run_id="r1", baseline_digest="b1"
        )
        assert result.is_ok
        assert result.danger_ok.commit_sha == "c1"

    def test_advance_overwrites_prior_watermark(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::advance_watermark kind="unit"
        advance_watermark(tmp_path, commit_sha="c1", run_id="r1", baseline_digest="b1")
        advance_watermark(tmp_path, commit_sha="c2", run_id="r2", baseline_digest="b2")
        loaded = load_watermark(tmp_path)
        assert loaded.is_ok
        watermark = loaded.danger_ok
        assert watermark is not None
        assert watermark.commit_sha == "c2"


class TestCompactQueue:
    """`compact_queue`: the ONE operation that shortens the queue file."""

    def test_drops_entries_at_or_before_watermark(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::compact_queue kind="unit"
        record_intent(
            tmp_path,
            commit_sha="c1",
            ticket_id="T-0001",
            touched_symbols=("a::b",),
            profile="rapid",
        )
        record_intent(
            tmp_path,
            commit_sha="c2",
            ticket_id="T-0002",
            touched_symbols=("c::d",),
            profile="rapid",
        )
        record_intent(
            tmp_path,
            commit_sha="c3",
            ticket_id="T-0003",
            touched_symbols=("e::f",),
            profile="rapid",
        )
        advance_watermark(tmp_path, commit_sha="c2", run_id="r1", baseline_digest="b1")
        result = compact_queue(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 2
        remaining = queue_status(tmp_path)
        assert remaining.is_ok
        assert [e.commit_sha for e in remaining.danger_ok] == ["c3"]

    def test_keeps_entries_after_watermark(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::compact_queue kind="unit"
        record_intent(
            tmp_path,
            commit_sha="c1",
            ticket_id="T-0001",
            touched_symbols=("a::b",),
            profile="rapid",
        )
        advance_watermark(tmp_path, commit_sha="c1", run_id="r1", baseline_digest="b1")
        record_intent(
            tmp_path,
            commit_sha="c2",
            ticket_id="T-0002",
            touched_symbols=("c::d",),
            profile="rapid",
        )
        compact_queue(tmp_path)
        remaining = queue_status(tmp_path)
        assert remaining.is_ok
        assert [e.commit_sha for e in remaining.danger_ok] == ["c2"]

    def test_watermark_commit_absent_from_queue_is_a_noop(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::compact_queue kind="unit"
        record_intent(
            tmp_path,
            commit_sha="c1",
            ticket_id="T-0001",
            touched_symbols=("a::b",),
            profile="rapid",
        )
        advance_watermark(
            tmp_path, commit_sha="not-in-queue", run_id="r1", baseline_digest="b1"
        )
        result = compact_queue(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 0
        remaining = queue_status(tmp_path)
        assert remaining.is_ok
        assert len(remaining.danger_ok) == 1

    def test_no_watermark_yet_is_a_noop(self, tmp_path: Path) -> None:
        # frob:tests src/frob/verify/_watermark.py::compact_queue kind="unit"
        record_intent(
            tmp_path,
            commit_sha="c1",
            ticket_id="T-0001",
            touched_symbols=("a::b",),
            profile="rapid",
        )
        result = compact_queue(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 0
