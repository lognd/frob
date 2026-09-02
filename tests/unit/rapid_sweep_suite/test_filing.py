"""Regression-ticket filing and quarantine tests for `frob.app.ticket_runner._rapid_sweep`
(T-3595 split of the former tests/unit/test_rapid_sweep.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.app.ticket_runner._rapid_sweep import (
    _file_regression_ticket,
    _relativize_regression_scope_file,
)
from tests.conftest import (
    _seed_ticket,
)


# frob:ticket T-2352
class TestRelativizeRegressionScopeFile:
    """T-2352: `_relativize_regression_scope_file` normalizes a regression
    finding's `.file` at the producer's own return boundary -- the fix for
    T-2308's real incident (an absolute path written into a filed
    ticket's `scope:` crashed `frob ticket new` fleet-wide, T-2342's
    reader-side half). Same posture as T-2314's
    `_relativize_perf_violation_file`."""

    # frob:ticket T-2352
    # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile.test_absolute_under_root_is_relativized  # noqa: E501
    def test_absolute_under_root_is_relativized(self, tmp_path: Path) -> None:
        """Positive control 1 (T-2352): an absolute path under root
        becomes a repo-relative one."""
        abs_file = str(tmp_path / "src" / "frob" / "x.py")
        result = _relativize_regression_scope_file(tmp_path, abs_file)
        assert result == str(Path("src") / "frob" / "x.py")
        assert not Path(result).is_absolute()

    # frob:ticket T-2352
    # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile.test_already_relative_is_unchanged  # noqa: E501
    def test_already_relative_is_unchanged(self, tmp_path: Path) -> None:
        """Must-still-pass control: an already-relative path is returned
        unchanged (no double-processing, no accidental corruption)."""
        result = _relativize_regression_scope_file(tmp_path, "scripts/fleet_status.py")
        assert result == "scripts/fleet_status.py"

    # frob:ticket T-2352
    # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile.test_absolute_outside_root_is_kept_and_logged  # noqa: E501
    def test_absolute_outside_root_is_kept_and_logged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Positive control 2 (T-2352, must-still-pass): a genuinely
        anomalous absolute path that does NOT resolve under root is kept
        as-is -- never silently coerced into a wrong-but-plausible
        relative path -- and logged loudly."""
        import logging

        outside = str(Path("/definitely/not/under/tmp_path/x.py"))
        with caplog.at_level(logging.WARNING):
            result = _relativize_regression_scope_file(tmp_path, outside)
        assert result == outside
        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert outside in messages

    # frob:ticket T-2352
    # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile.test_filed_ticket_scope_is_relative_end_to_end  # noqa: E501
    def test_filed_ticket_scope_is_relative_end_to_end(self, tmp_path: Path) -> None:
        """Positive control 3 (T-2352): a ticket filed by
        `_file_regression_ticket` with an ABSOLUTE finding path gets a
        RELATIVE `scope:` entry -- the actual T-2308 incident shape,
        exercised end-to-end through the real filer, not just the helper
        in isolation. This MUST FAIL before this ticket's fix (scope would
        carry the raw absolute path)."""
        from frob.tickets._store import load_all

        abs_file = str(tmp_path / "src" / "frob" / "x.py")
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", abs_file)})
        )
        assert filed is not None
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        ticket = loaded.danger_ok[filed]
        assert list(ticket.scope) == [str(Path("src") / "frob" / "x.py")]


# frob:ticket T-1791
# frob:ticket T-1847
class TestRaiseQuarantineForRedBatch:
    """T-1791: wiring `raise_quarantine` into the shared "a red batch
    verification came back" seam both drivers (`_file_regression_ticket`)
    call through."""

    # frob:ticket T-1791
    def test_raises_with_attributed_and_unattributed_findings(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_raises_with_attributed_and_unattributed_findings  # noqa: E501
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        # No graph patched -- attribution degrades to "unavailable",
        # exactly the pre-T-1690 fallback `_file_regression_ticket`'s own
        # docstring already documents; every pair is filed, and every
        # QuarantinedFinding here carries no commit_sha/ticket_id.
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py"), ("RULE2", "b.py")}),
        )
        assert filed is not None

        # T-2208: the regression ticket this call filed covers BOTH
        # pairs, so the auto-dispose that follows filing clears the
        # quarantine it just raised in the same operation -- the raise
        # itself (this test's own T-1791 subject) is still verified via
        # the record's own content, just post-clear rather than
        # is_quarantined() staying True.
        assert is_quarantined(tmp_path).danger_ok is False
        record = load_quarantine(tmp_path)
        assert record.is_ok
        assert record.danger_ok is not None
        assert record.danger_ok.batch_commit_shas == ("commitA",)
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("RULE1", "a.py"),
            ("RULE2", "b.py"),
        }
        assert all(f.disposition == "filed" for f in record.danger_ok.findings)
        assert all(f.disposition_ref == filed for f in record.danger_ok.findings)

    # frob:ticket T-1791
    def test_empty_queue_logs_and_skips_the_raise(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_empty_queue_logs_and_skips_the_raise  # noqa: E501
        from frob.verify._quarantine import is_quarantined

        # No verify queue at all -- nothing to name as the raising batch.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2604
    def test_open_ticket_attribution_clears_the_quarantine_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_open_ticket_attribution_clears_the_quarantine_raise  # noqa: E501
        """T-2604: every pair attributes to an already-open ticket -- no
        NEW regression ticket is filed (that half was already correct,
        T-1690), and the batch must NOT trip the quarantine circuit
        breaker either, since a still-open owner means the finding
        already has a home and someone is on it."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-2604
    def test_closed_ticket_attribution_still_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_closed_ticket_attribution_still_raises  # noqa: E501
        """T-2604: a pair attributed to a CLOSED/DROPPED ticket is a real
        regression against work believed finished -- it must still trip
        quarantine, exactly as before this ticket. Without this case the
        fix would be indistinguishable from disabling quarantine
        outright."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.tickets._models import TicketState
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None  # closed owner -- refiled as a new ticket
        # T-2208: the freshly filed ticket covers this pair, so
        # auto-dispose clears the quarantine flag in the same operation
        # -- the raise itself (this test's own T-2604 subject: a
        # closed-ticket attribution must still trip quarantine) is
        # verified via the record's own content, same pattern as
        # test_raises_with_attributed_and_unattributed_findings above.
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("RULE1", "a.py"),
        }

    # frob:ticket T-2604
    def test_unattributed_still_raises_alongside_open_ticket_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_unattributed_still_raises_alongside_open_ticket_finding  # noqa: E501
        """T-2604: a batch mixing one open-ticket finding with one
        unattributed finding must still raise, naming only the
        unattributed one -- an unowned finding is exactly what
        quarantine exists to catch, and the open-ticket finding's
        presence in the same batch must not mask it."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        # RULE1/a.py attributes to the open ticket via a.py::fn;
        # RULE2/b.py has no symbol in the snapshot, so it stays
        # UNATTRIBUTED.
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py"), ("RULE2", "b.py")}),
        )
        assert filed is not None  # the unattributed pair gets a new ticket
        # T-2208: the filed ticket covers exactly the unattributed pair,
        # so auto-dispose clears the flag in the same operation -- the
        # raise itself (named only the unattributed pair, per this
        # test's own subject) is verified via the record's own content.
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("RULE2", "b.py"),
        }

    # frob:ticket T-1791
    def test_raise_failure_is_logged_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_raise_failure_is_logged_not_raised  # noqa: E501
        from typani.result import Err

        from frob.verify import _quarantine as quarantine_mod
        from frob.verify import record_intent
        from frob.verify._quarantine import QuarantineError

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        monkeypatch.setattr(
            quarantine_mod,
            "raise_quarantine",
            lambda root, **kw: Err(QuarantineError.StoreCorrupt),
        )
        # Must not raise or otherwise fail the caller -- the regression
        # ticket filing is the durable record; a quarantine write failure
        # is logged and swallowed.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    # frob:ticket T-1847
    def test_warm_tree_recheck_drops_cold_worktree_native_noise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_drops_cold_worktree_native_noise  # noqa: E501
        from frob.strata import _native_staleness
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        # Every declared native imports cleanly RIGHT NOW -- the sole
        # finding is UNATTRIBUTED + "unresolved-import", the exact
        # cold-worktree-noise shape, so the warm re-check must clear it
        # and the raise must be skipped entirely.
        monkeypatch.setattr(_native_staleness, "unimportable_natives", lambda root: ())
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is not None  # still filed as a regression ticket
        assert is_quarantined(tmp_path).danger_ok is False

    # frob:ticket T-1847
    def test_warm_tree_recheck_keeps_finding_when_native_still_broken(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_keeps_finding_when_native_still_broken  # noqa: E501
        from frob.strata import _native_staleness
        from frob.testing._models import NativeSpec
        from frob.verify import record_intent
        from frob.verify._quarantine import is_quarantined, load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-9000",
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        broken = (NativeSpec(name="strata_core", build_cmd="true"),)
        monkeypatch.setattr(
            _native_staleness, "unimportable_natives", lambda root: broken
        )
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is not None
        # T-2208: this pair is fully covered by the ticket just filed,
        # so auto-dispose clears the quarantine the raise (this test's
        # own T-1847 subject) put up.
        assert is_quarantined(tmp_path).danger_ok is False
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("unresolved-import", "a.py"),
        }
        assert all(f.disposition == "filed" for f in record.danger_ok.findings)

    # frob:ticket T-1847
    def test_warm_tree_recheck_never_drops_an_attributed_finding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch.test_warm_tree_recheck_never_drops_an_attributed_finding  # noqa: E501
        """T-2604: the owning ticket here is CLOSED (not open) so this
        stays an isolated test of the T-1847 warm-tree filter alone --
        an open owner would ALSO be cleared by the new T-2604 open-ticket
        filter, which would make a pass here ambiguous about which filter
        is actually responsible."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.strata import _native_staleness
        from frob.tickets._models import TicketState
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, CallGraph(calls={})),
        )
        # unimportable_natives says everything is warm -- if the finding
        # were unattributed this would clear it, but this pair reaches
        # a.py::fn and must attribute to a CLOSED ticket (owner), a
        # wholly different case than "unattributed". The finding must NOT
        # be treated as cold-worktree noise just because the rule id
        # matches.
        monkeypatch.setattr(_native_staleness, "unimportable_natives", lambda root: ())
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("unresolved-import", "a.py")}),
        )
        assert filed is not None  # closed owner -- refiled as a new ticket
        # T-2208: the filed ticket covers this pair, so auto-dispose
        # clears the flag -- verify the raise itself via the record's
        # own content, same pattern as the other T-2604/T-1847 tests.
        record = load_quarantine(tmp_path)
        assert record.danger_ok is not None
        assert {(f.rule_id, f.file) for f in record.danger_ok.findings} == {
            ("unresolved-import", "a.py"),
        }


# frob:ticket T-2450
class TestFileRegressionTicketPublicSeam:
    """T-2450: `file_regression_ticket` is a thin public wrapper around
    `_file_regression_ticket` -- the cross-node seam `frob.verify._worker`
    imports instead of reaching across the node boundary to call the
    private name directly."""

    # frob:ticket T-2450
    # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicketPublicSeam.test_delegates_to_the_private_implementation  # noqa: E501
    def test_delegates_to_the_private_implementation(self, tmp_path: Path) -> None:
        from frob.app.ticket_runner._rapid_sweep import file_regression_ticket

        filed = file_regression_ticket(
            tmp_path, "T-9001", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None


# frob:ticket T-1791
# frob:ticket T-2744
# frob:ticket T-3051
class TestFileRegressionTicket:
    """T-1690: attributed findings owned by a still-open ticket are not
    re-filed; everything else is filed with a full attribution trail."""

    def _patch_graph(
        self, monkeypatch: pytest.MonkeyPatch, snapshot, call_graph
    ) -> None:
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod,
            "_load_snapshot_and_call_graph",
            lambda root: (snapshot, call_graph),
        )

    # frob:ticket T-1791
    def test_no_attribution_files_everything_as_before(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_no_attribution_files_everything_as_before  # noqa: E501
        # No verify queue at all -- attribution unavailable, falls back to
        # the pre-T-1690 behavior of filing every pair.
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    # frob:ticket T-3245
    def test_concurrent_sweeps_file_only_one_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_concurrent_sweeps_file_only_one_ticket  # noqa: E501
        """T-3245 must-fire: two sweeps racing to file the SAME (rule,
        file) identity for the same land must produce exactly ONE
        ticket, not the byte-identical duplicate pair T-3236/T-3237
        (also T-3158/T-3159, T-3022/T-3023) measured live. Both threads
        open their own file descriptor onto the same `allocator_lock`/
        `ledger_lock` paths -- a real cross-process-shaped `flock`
        contention, not merely two calls in sequence -- so this exercises
        the actual TOCTOU window the fix closes: `new_ticket`'s duplicate
        check now runs only after the lock guarantees any sibling write
        is already on disk."""
        import threading

        barrier = threading.Barrier(2)
        results: list[str | None] = []
        results_lock = threading.Lock()

        def _worker() -> None:
            barrier.wait()
            filed = _file_regression_ticket(
                tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
            )
            with results_lock:
                results.append(filed)

        threads = [threading.Thread(target=_worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 2
        assert None not in results
        assert len(set(results)) == 1, f"expected one shared ticket id, got {results}"

        from frob.tickets._store import load_all

        tickets = load_all(tmp_path).danger_ok
        assert tickets is not None
        matching = [t for t in tickets.values() if ("RULE1", "a.py") in t.findings]
        assert len(matching) == 1, f"expected exactly one ticket, found {matching}"

    # frob:ticket T-3245
    def test_reappearing_finding_after_closed_ticket_files_a_new_one(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_reappearing_finding_after_closed_ticket_files_a_new_one  # noqa: E501
        """T-3245 must-stay-quiet: the SAME (rule, file) identity
        reappearing at a LATER commit, after the ticket that owned it
        closed, is legitimately a NEW regression, not a duplicate --
        proof the T-3245 lock only serializes concurrent writers, it
        does not change `_find_finding_duplicate`'s existing DONE/
        DROPPED-exclusion identity logic (T-2760), which must keep
        filing a fresh ticket here rather than silently suppressing it."""
        from frob.tickets import drop_ticket

        first = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert first is not None
        dropped = drop_ticket(tmp_path, first, reason="fixed")
        assert dropped.is_ok

        second = _file_regression_ticket(
            tmp_path, "T-9001", "c0ffee00", frozenset({("RULE1", "a.py")})
        )
        assert second is not None
        assert second != first

    # frob:ticket T-3222
    def test_still_reproducing_finding_files_a_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_still_reproducing_finding_files_a_ticket  # noqa: E501
        # Must-fire: a finding that STILL reproduces at file time must
        # still result in a filed ticket.
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "RULE1", "file": "a.py", "severity": "error"},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: Ok(_Proc(json.dumps(payload))),
        )
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    # frob:ticket T-3222
    def test_vanished_finding_files_no_ticket(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_vanished_finding_files_no_ticket  # noqa: E501
        # Must-stay-quiet: a finding fixed between spawn and file time
        # (an independent re-measure that finds nothing for it) must NOT
        # be filed as a ticket -- T-3222's exact defect, reproduced here
        # as T-3188/T-3210/T-3215's shape.
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        payload = {"results": [{"tool": "gate-summary", "diagnostics": []}]}
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: Ok(_Proc(json.dumps(payload))),
        )
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None

    def test_commit_failure_skips_auto_dispose_and_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-2744: the T-2736 incident -- if the regression ticket's
        ledger write never lands, `_file_regression_ticket` must not
        proceed to dispose/clear quarantine against an id that does not
        exist on `root`. It must return `None` (no id to report as
        filed) and quarantine must be left exactly as it was."""
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_commit_failure_skips_auto_dispose_and_returns_none  # noqa: E501
        import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
        from frob.verify._quarantine import (
            QuarantinedFinding,
            load_quarantine,
            raise_quarantine,
        )

        raise_quarantine(
            tmp_path,
            batch_commit_shas=("deadbeef",),
            findings=(QuarantinedFinding(rule_id="RULE1", file="a.py", line=1),),
        )

        monkeypatch.setattr(
            rapid_sweep_mod, "_commit_regression_ticket", lambda *a, **k: False
        )
        disposed_calls: list[object] = []
        monkeypatch.setattr(
            rapid_sweep_mod,
            "_auto_dispose_filed_findings",
            lambda *a, **k: disposed_calls.append(a),
        )

        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )

        assert filed is None
        assert disposed_calls == []
        record = load_quarantine(tmp_path).danger_ok
        assert record is not None
        assert record.cleared_at is None  # still raised, not phantom-cleared

    def test_attributed_to_open_ticket_is_not_refiled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_attributed_to_open_ticket_is_not_refiled  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None

    def test_attributed_to_closed_ticket_is_refiled(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_attributed_to_closed_ticket_is_refiled  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.tickets._models import TicketState
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    def test_unattributed_is_filed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_unattributed_is_filed  # noqa: E501
        from frob.graph import CallGraph, GraphSnapshot
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

    # frob:ticket T-2672
    def test_causally_implicated_land_still_names_itself_as_the_cause(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_causally_implicated_land_still_names_itself_as_the_cause  # noqa: E501
        """T-2672 positive control (must-still-pass direction): when the
        spawning land's OWN commit genuinely reaches the finding via the
        reference graph (the exact shape `test_attributed_to_closed_
        ticket_is_refiled` already covers for filing, this asserts the
        TITLE too), the fix must not become indistinguishable from
        disabling attribution -- the title still names the land as the
        cause, unqualified."""
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.tickets import load_queue
        from frob.tickets._models import TicketState
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path, state=TicketState.DONE)
        record_intent(
            tmp_path,
            commit_sha="deadbeef",
            ticket_id=owner,
            touched_symbols=("a.py::fn",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                )
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))

        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

        ticket = load_queue(tmp_path).danger_ok.tickets[filed]
        assert "regression from T-9000" in ticket.title, (
            f"a genuinely reaching land must still be named plainly: {ticket.title!r}"
        )
        assert "unattributed" not in ticket.title.lower(), (
            f"must not hedge a real attribution: {ticket.title!r}"
        )

    # frob:ticket T-2672
    def test_unattributed_finding_does_not_name_the_spawning_land_as_cause(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_unattributed_finding_does_not_name_the_spawning_land_as_cause  # noqa: E501
        """T-2672: six real sweep-filed tickets all named the spawning
        land (`final_id`, the one commit in a single-land window) as the
        cause in their title even though `_attribution.py`'s own
        per-finding reachability check reported every one of them
        UNATTRIBUTED -- `git show --stat` on the blamed commit showed it
        touched none of the flagged files. This reproduces the single-
        land-but-unattributed shape directly: a verify-queue entry exists
        (so attribution actually runs) but its touched symbols cannot
        reach the finding's file, so `_partition_findings_by_attribution`
        must report every pair UNATTRIBUTED -- yet the filed ticket's own
        title must not read as if T-9000 caused it."""
        from frob.graph import CallGraph, GraphSnapshot
        from frob.tickets import load_queue
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))

        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is not None

        ticket = load_queue(tmp_path).danger_ok.tickets[filed]
        assert "regression from T-9000" not in ticket.title, (
            "every finding attributed UNATTRIBUTED for this batch -- the "
            f"title must not claim T-9000 as the cause: {ticket.title!r}"
        )
        assert "unattributed" in ticket.title.lower(), (
            "the title must positively disclose that these findings "
            f"could not be attributed to any land: {ticket.title!r}"
        )

    # frob:ticket T-2312
    def test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_duplicate_title_disposes_to_existing_ticket_instead_of_dropping  # noqa: E501
        """T-2312 acceptance [0]: findings whose equivalent ticket already
        exists (same title+scope `new_ticket` would refuse as an exact
        duplicate) get disposed to that ticket -- and quarantine clears --
        instead of being silently abandoned when the auto-filer declines
        to file a second one. Calling `_file_regression_ticket` twice with
        identical arguments and no attribution reproduces the real
        incident directly: the first call files a regression ticket, the
        second computes the SAME deterministic title+scope and hits the
        exact-duplicate refusal `new_ticket` already enforces."""
        from frob.graph import CallGraph, GraphSnapshot
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        pairs = frozenset({("RULE1", "a.py")})

        first = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", pairs)
        assert first is not None

        second = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", pairs)
        assert second == first, (
            "a refused duplicate must dispose to the EXISTING ticket, "
            "never return None and abandon the findings"
        )

        record = load_quarantine(tmp_path).danger_ok
        assert record is not None
        assert record.cleared_at is not None, (
            "quarantine must clear once the duplicate-owned findings are "
            "disposed to the existing ticket"
        )

    # frob:ticket T-3051
    def test_duplicate_finding_disposes_to_declaring_ticket_instead_of_dropping(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_duplicate_finding_disposes_to_declaring_ticket_instead_of_dropping  # noqa: E501
        """T-3051 (H4) acceptance [0] (must-work): the routine, encouraged
        workflow of a fix ticket declaring the finding it fixes must not
        deadlock a later sweep's re-measurement of that SAME finding. An
        open ticket with a DIFFERENT title (so `_find_exact_duplicate`'s
        title+scope check does not fire at all) that already declares
        `("RULE1", "a.py")` in its structured `findings` field reproduces
        the real T-2977 incident directly: `_file_regression_ticket`'s own
        `new_ticket(...)` call is refused with `DuplicateFinding`
        (T-2760), and before this fix that refusal fell through to the
        generic ERROR branch and returned `None` -- an unfiled regression
        with no owner, which pins the watermark (T-2324) and leaves
        quarantine undisposable (T-2744) even though the finding already
        has a perfectly good owner. The fix must resolve that owner via
        `_find_finding_duplicate` and dispose to it, exactly as the
        DuplicateTicket branch already does."""
        from frob.graph import CallGraph, GraphSnapshot
        from frob.tickets import TicketSpec, new_ticket
        from frob.tickets._models import Origin, TicketKind
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))

        # An open ticket, filed under a title sharing no words with the
        # sweep's own generated title, that already declares the finding
        # this sweep is about to re-measure -- the "fix ticket declares
        # its own findings" shape T-2760's docstring names explicitly.
        declaring = new_ticket(
            tmp_path,
            TicketSpec(
                title="fix the F401 unused import",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                scope=("a.py",),
                findings=(("RULE1", "a.py"),),
            ),
            no_commit=True,
            warn_if_dirty=False,
        )
        assert declaring.is_ok
        declaring_id = declaring.danger_ok.id

        pairs = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", pairs)

        assert filed == declaring_id, (
            "a DuplicateFinding refusal must dispose to the ticket that "
            "already declares the finding, never return None and "
            "abandon it"
        )

        record = load_quarantine(tmp_path).danger_ok
        assert record is not None
        assert record.cleared_at is not None, (
            "quarantine must clear once the duplicate-owned findings are "
            "disposed to the declaring ticket"
        )

    # frob:ticket T-3051
    def test_unrelated_duplicate_finding_in_a_different_file_still_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_unrelated_duplicate_finding_in_a_different_file_still_refuses  # noqa: E501
        """T-3051 (H4) acceptance [1] (must-still-refuse positive
        control): a ticket declaring a DIFFERENT (rule, file) pair must
        not be mistaken for the owner of this sweep's finding -- the fix
        must resolve the ACTUAL declaring ticket via `_find_finding_
        duplicate`, never accept any open ticket as a stand-in. With no
        ticket declaring the real pair, filing genuinely fails (no
        DuplicateFinding refusal fires at all here, since the identities
        never overlap) and this must file its own new ticket rather than
        silently disposing to the unrelated one."""
        from frob.graph import CallGraph, GraphSnapshot
        from frob.tickets import TicketSpec, load_queue, new_ticket
        from frob.tickets._models import Origin, TicketKind
        from frob.verify import record_intent

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))

        unrelated = new_ticket(
            tmp_path,
            TicketSpec(
                title="fix an unrelated finding",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                scope=("b.py",),
                findings=(("RULE2", "b.py"),),
            ),
            no_commit=True,
            warn_if_dirty=False,
        )
        assert unrelated.is_ok

        pairs = frozenset({("RULE1", "a.py")})
        filed = _file_regression_ticket(tmp_path, "T-9000", "deadbeef", pairs)

        assert filed is not None
        assert filed != unrelated.danger_ok.id, (
            "a ticket declaring an unrelated (rule, file) pair must "
            "never be treated as this finding's owner"
        )
        queue = load_queue(tmp_path).danger_ok
        assert queue is not None
        assert queue.tickets[filed].findings == (("RULE1", "a.py"),)

    # frob:ticket T-2312
    def test_non_duplicate_filing_failure_still_leaves_quarantine_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_non_duplicate_filing_failure_still_leaves_quarantine_raised  # noqa: E501
        """T-2312 acceptance [1] (must-still-pass positive control): a
        filing failure that is NOT a duplicate refusal (no existing
        ticket owns these findings at all) must still leave quarantine
        RAISED and still return `None` -- the T-2312 fix only reroutes
        the DUPLICATE branch to disposal, it must never make an
        ownerless finding's filing failure look disposed."""
        from typani import Err

        import frob.tickets as tickets_mod
        from frob.graph import CallGraph, GraphSnapshot
        from frob.tickets._models import TicketError
        from frob.verify import record_intent
        from frob.verify._quarantine import load_quarantine

        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id="T-0001",
            touched_symbols=("unrelated.py::other",),
            profile="rapid",
        )
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        monkeypatch.setattr(
            tickets_mod, "new_ticket", lambda *a, **k: Err(TicketError.WriteFailed)
        )

        filed = _file_regression_ticket(
            tmp_path, "T-9000", "deadbeef", frozenset({("RULE1", "a.py")})
        )
        assert filed is None

        record = load_quarantine(tmp_path).danger_ok
        assert record is not None
        assert record.cleared_at is None, (
            "an ownerless finding's failed filing must NOT clear "
            "quarantine -- that is the guard's real job"
        )

    def test_all_attributed_to_open_tickets_files_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/rapid_sweep_suite/test_filing.py::TestFileRegressionTicket.test_all_attributed_to_open_tickets_files_nothing  # noqa: E501
        from frob.graph import CallGraph, Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.lang import SymbolKind
        from frob.verify import record_intent

        owner = _seed_ticket(tmp_path)
        record_intent(
            tmp_path,
            commit_sha="commitA",
            ticket_id=owner,
            touched_symbols=("a.py::fn", "b.py::fn2"),
            profile="rapid",
        )
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn": SymbolRecord(
                    id=SymbolId(path="a.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                ),
                "b.py::fn2": SymbolRecord(
                    id=SymbolId(path="b.py", qualname="fn2"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 5),
                ),
            },
            edges=(),
        )
        self._patch_graph(monkeypatch, snapshot, CallGraph(calls={}))
        filed = _file_regression_ticket(
            tmp_path,
            "T-9000",
            "deadbeef",
            frozenset({("RULE1", "a.py"), ("RULE2", "b.py")}),
        )
        assert filed is None
