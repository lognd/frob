"""Tests for frob.ci_validity -- CI result validity against the affects
graph (docs/modules/ci_validity.md). Graph fixtures follow
tests/test_graph_affects.py's own minimal-snapshot pattern; git/gh
boundaries are monkeypatched so this file never depends on a real repo
history or a real `gh` call."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Err, Ok

import frob.ci_validity as ci_validity_mod
from frob.ci_report import JobReport, RunReport, TestFailure
from frob.ci_validity import (
    Validity,
    classify_test,
    job_validity,
    run_validity,
    validity_for_run_head_sha,
)
from frob.gitio import Diff, GitError, Hunk
from frob.graph._models import (
    Digests,
    Edge,
    EdgeKind,
    GraphSnapshot,
    SymbolId,
    SymbolRecord,
)
from frob.lang import SymbolKind


def _record(symref: str, *, span: tuple[int, int] = (1, 3)) -> SymbolRecord:
    path, qualname = symref.split("::", 1)
    return SymbolRecord(
        id=SymbolId(path=path, qualname=qualname),
        kind=SymbolKind.FUNCTION,
        public=True,
        digests=Digests(sig="s", body="b", doc="d"),
        span=span,
    )


def _snapshot(records: dict[str, tuple[int, int]], edges: tuple[Edge, ...]) -> GraphSnapshot:
    return GraphSnapshot(
        root="/repo",
        symbols={ref: _record(ref, span=span) for ref, span in records.items()},
        edges=edges,
        malformed=(),
        file_hashes={},
    )


class TestClassifyTest:
    def test_still_valid_when_nothing_relevant_changed(self) -> None:
        # frob:tests src/frob/ci_validity.py::classify_test
        snap = _snapshot(
            {"a.py::foo": (1, 3), "tests/test_a.py::test_foo": (1, 2)},
            (
                Edge(
                    src="tests/test_a.py::test_foo",
                    kind=EdgeKind.TESTS,
                    target="a.py::foo",
                    origin="tests/test_a.py:1",
                ),
            ),
        )
        result = classify_test(snap, frozenset(), "tests/test_a.py::test_foo")
        assert result.status == Validity.STILL_VALID

    def test_stale_when_reached_by_a_touched_symbol(self) -> None:
        # frob:tests src/frob/ci_validity.py::classify_test
        snap = _snapshot(
            {"a.py::foo": (1, 3), "tests/test_a.py::test_foo": (1, 2)},
            (
                Edge(
                    src="tests/test_a.py::test_foo",
                    kind=EdgeKind.TESTS,
                    target="a.py::foo",
                    origin="tests/test_a.py:1",
                ),
            ),
        )
        result = classify_test(snap, frozenset({"a.py::foo"}), "tests/test_a.py::test_foo")
        assert result.status == Validity.STALE
        assert "a.py::foo" in result.reason

    def test_stale_when_test_itself_touched(self) -> None:
        # frob:tests src/frob/ci_validity.py::classify_test
        snap = _snapshot({"tests/test_a.py::test_foo": (1, 2)}, ())
        result = classify_test(
            snap, frozenset({"tests/test_a.py::test_foo"}), "tests/test_a.py::test_foo"
        )
        assert result.status == Validity.STALE

    def test_unknown_when_symbol_unresolvable(self) -> None:
        # frob:tests src/frob/ci_validity.py::classify_test
        snap = _snapshot({}, ())
        result = classify_test(snap, frozenset(), "tests/test_a.py::test_missing")
        assert result.status == Validity.UNKNOWN

    def test_unknown_when_closure_truncated(self) -> None:
        # frob:tests src/frob/ci_validity.py::classify_test
        # a.py::foo -> (uses-contract) -> b.py::bar -> tests/test_b.py::test_bar,
        # so the test edge is only reachable ONE hop past the touched
        # symbol; capping max_depth at 0 truncates before that hop, and
        # the walk must report UNKNOWN rather than a false STILL_VALID.
        snap = _snapshot(
            {
                "a.py::foo": (1, 3),
                "b.py::bar": (1, 3),
                "tests/test_b.py::test_bar": (1, 2),
            },
            (
                Edge(
                    src="b.py::bar",
                    kind=EdgeKind.USES_CONTRACT,
                    target="a.py::foo",
                    origin="b.py:1",
                ),
                Edge(
                    src="tests/test_b.py::test_bar",
                    kind=EdgeKind.TESTS,
                    target="b.py::bar",
                    origin="tests/test_b.py:1",
                ),
            ),
        )
        result = classify_test(
            snap,
            frozenset({"a.py::foo"}),
            "tests/test_b.py::test_bar",
            _max_depth=0,
        )
        assert result.status == Validity.UNKNOWN

        # sanity: the SAME graph with the default (deep enough) bound
        # correctly reaches the test edge and reports STALE.
        result_unbounded = classify_test(
            snap, frozenset({"a.py::foo"}), "tests/test_b.py::test_bar"
        )
        assert result_unbounded.status == Validity.STALE


class TestValidityForRunHeadSha:
    def test_diff_failure_is_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_validity.py::validity_for_run_head_sha
        monkeypatch.setattr(
            ci_validity_mod, "working_diff", lambda root, base: Err(GitError.GitFailed)
        )
        snap = _snapshot({}, ())
        result = validity_for_run_head_sha(tmp_path, snap, "deadbeef", ("x.py::test_x",))
        assert result.is_err

    def test_classifies_every_failing_node(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_validity.py::validity_for_run_head_sha
        snap = _snapshot(
            {"a.py::foo": (1, 3), "tests/test_a.py::test_foo": (1, 2)},
            (
                Edge(
                    src="tests/test_a.py::test_foo",
                    kind=EdgeKind.TESTS,
                    target="a.py::foo",
                    origin="tests/test_a.py:1",
                ),
            ),
        )
        monkeypatch.setattr(
            ci_validity_mod,
            "working_diff",
            lambda root, base: Ok(Diff(base=base, hunks=(Hunk(file="a.py", span=(1, 3)),))),
        )
        result = validity_for_run_head_sha(
            tmp_path, snap, "deadbeef", ("tests/test_a.py::test_foo",)
        )
        assert result.is_ok
        assert result.danger_ok[0].status == Validity.STALE


class TestJobAndRunValidity:
    def _snap_and_diff(self, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN001, ANN201
        snap = _snapshot(
            {"a.py::foo": (1, 3), "tests/test_a.py::test_foo": (1, 2)},
            (
                Edge(
                    src="tests/test_a.py::test_foo",
                    kind=EdgeKind.TESTS,
                    target="a.py::foo",
                    origin="tests/test_a.py:1",
                ),
            ),
        )
        monkeypatch.setattr(
            ci_validity_mod, "working_diff", lambda root, base: Ok(Diff(base=base, hunks=()))
        )
        return snap

    def test_job_validity_covers_named_failures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_validity.py::job_validity
        snap = self._snap_and_diff(monkeypatch)
        job = JobReport(
            job_id="j1",
            name="ubuntu",
            conclusion="failure",
            outcome="failures",
            failures=(
                TestFailure(
                    node_id="tests/test_a.py::test_foo",
                    kind="failed",
                    reason="boom",
                    signature="failed:boom",
                ),
            ),
            clusters=(),
            truncated=False,
        )
        result = job_validity(tmp_path, snap, "deadbeef", job)
        assert result.is_ok
        jv = result.danger_ok
        assert jv.job_id == "j1"
        assert len(jv.tests) == 1
        assert jv.tests[0].status == Validity.STILL_VALID

    def test_run_validity_covers_every_job(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/ci_validity.py::run_validity
        snap = self._snap_and_diff(monkeypatch)
        job = JobReport(
            job_id="j1",
            name="ubuntu",
            conclusion="success",
            outcome="clean",
            failures=(),
            clusters=(),
            truncated=False,
        )
        run = RunReport(run_id="r1", conclusion="success", jobs=(job,))
        result = run_validity(tmp_path, snap, "deadbeef", run)
        assert result.is_ok
        rv = result.danger_ok
        assert rv.run_id == "r1"
        assert len(rv.jobs) == 1
        assert rv.jobs[0].tests == ()
