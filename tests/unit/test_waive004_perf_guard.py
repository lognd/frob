"""T-2011: the perf-family WAIVE004 examined-sites guard.

`tests/test_gates.py` (where `TestWaive004ExaminedSitesGuard`, T-1942's own
archgate precedent, lives) was under T-1959's live cross-worktree lease for
this ticket's entire window, so this ticket's own acceptance tests live in
this standalone file instead -- same fixtures/shape as the archgate class,
targeting the perf family this ticket adds
(`frob.gates._fix_engine_sync._drop_unexamined_perf_candidates`).
"""
# frob:ticket T-2011

from __future__ import annotations

from pathlib import Path

import pytest
from typani.result import Ok

from frob.gates import GateReport, GateStats, Severity, Violation
from frob.gates._fix_engine_sync import fix_waive004_stale_waiver
from frob.tickets import TicketQueue


def _snap(root: Path):
    """Build a real `GraphSnapshot` for `root` -- `fix_waive004_stale_waiver`
    needs one as its second positional argument, though this handler's own
    verification pass never reads it (it re-derives everything from its
    self-manufactured `run_gates()` call)."""
    from frob.graph import build_graph

    return build_graph(root, root / ".frob" / "cache.db").danger_ok


# frob:ticket T-2011
class TestWaive004PerfExaminedSitesGuard:
    """T-2011: a FOURTH additive WAIVE004 guard, stacked on the mass-
    invalidation/degraded-run guards and T-1942's archgate guard -- a
    perf-family candidate (`_PERF_RULE_IDS`) must not be deleted unless
    this run's real per-site examined-sites substrate positively confirms
    the candidate's own file was parsed by the perf family this run."""

    # frob:tests \
    # tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard.test_e\
    # xamined_perf_site_is_deleted
    def test_examined_perf_site_is_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A waiver on a perf-rule site that a real `_perf_examined_sites
        (root)` call DOES confirm was parsed this run behaves exactly as
        before T-2011 -- the guard grants deletion, it does not
        additionally refuse a genuinely examined site."""
        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        (root / "src" / "good.py").write_text(
            '# frob:waive PERF001 reason="fixture, T-2011"\ndef f():\n    return 1\n',
            encoding="utf-8",
        )
        snapshot = _snap(root)

        report = GateReport(
            violations=(
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/good.py",
                    line=1,
                    message="WAIVE004: frob:waive PERF001 matches 0 findings",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        waive004_applied = [a for a in applied if a.rule == "WAIVE004"]
        assert len(waive004_applied) == 1
        rewritten = (root / "src" / "good.py").read_text(encoding="utf-8")
        assert "frob:waive PERF001" not in rewritten

    # frob:tests \
    # tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard.test_u\
    # nexamined_perf_site_refuses
    def test_unexamined_perf_site_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """perf IS instrumented (it always is, in this handler's
        self-manufactured run), but the candidate's own file is NOT a
        member of the real, freshly-computed perf-examined set (no
        registered tree-sitter grammar for its extension) -- the guard
        must refuse to delete it, even though the WAIVE004 finding itself
        looks completely ordinary."""
        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        # A real, single-line, well-formed frob:waive comment -- the exact
        # shape `_remove_waiver_line` deletes -- but in a file whose
        # extension has no registered tree-sitter grammar, so the perf
        # family's real parse pass never reaches it this run.
        (root / "src" / "bad.bin").write_bytes(
            b'# frob:waive PERF001 reason="fixture, T-2011"\n'
        )
        snapshot = _snap(root)

        report = GateReport(
            violations=(
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/bad.bin",
                    line=1,
                    message="WAIVE004: frob:waive PERF001 matches 0 findings",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        assert applied == []

    # frob:tests \
    # tests/unit/test_waive004_perf_guard.py::TestWaive004PerfExaminedSitesGuard.test_p\
    # erf009_is_excluded_from_the_guard
    def test_perf009_is_excluded_from_the_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PERF009 (the ratchet-artifact rule, `frob.perf._ratchet.
        ratchet_violations`) is deliberately NOT in `_PERF_RULE_IDS` --
        unlike PERF001-008/010-014, it is never derived from this run's
        own parse pass (it reads `.frob/perf/ratchet_findings.json`
        instead), so the perf-examined-sites substrate says nothing
        trustworthy about it. A PERF009 candidate must behave exactly as
        it did before T-2011 (grant-nothing -- deletion proceeds on the
        strength of the other pre-existing guards alone) even for a file
        the perf parse pass never touched at all, proving this guard is
        gated on `rule in _PERF_RULE_IDS`, not an unconditional
        `site_examined` call that a substrate never built to answer for
        this rule could accidentally veto (or, more dangerously, wrongly
        confirm)."""
        root = tmp_path / "repo"
        (root / "src").mkdir(parents=True)
        (root / "tickets.md").write_text("", encoding="utf-8")
        # No grammar for this extension either -- if PERF009 were wrongly
        # folded into `_PERF_RULE_IDS`, this candidate would be refused
        # just like `test_unexamined_perf_site_refuses` above; the
        # assertion below proves it is NOT refused.
        (root / "src" / "unparseable.bin").write_bytes(
            b'# frob:waive PERF009 reason="fixture"\n'
        )
        snapshot = _snap(root)

        report = GateReport(
            violations=(
                Violation(
                    rule="WAIVE004",
                    severity=Severity.ERROR,
                    file="src/unparseable.bin",
                    line=1,
                    message="WAIVE004: frob:waive PERF009 matches 0 findings",
                ),
            ),
            waived=(),
            stats=GateStats(),
        )
        monkeypatch.setattr("frob.gates.run_gates", lambda cfg, **kw: Ok(report))

        applied = fix_waive004_stale_waiver(root, snapshot, TicketQueue(tickets={}))

        waive004_applied = [a for a in applied if a.rule == "WAIVE004"]
        assert len(waive004_applied) == 1
        rewritten = (root / "src" / "unparseable.bin").read_text(encoding="utf-8")
        assert "frob:waive PERF009" not in rewritten
