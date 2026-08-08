"""Unit tests for `frob.verify._selection` (T-1689): batch test
selection -- a batch's union touched-set run in ONE pytest process."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.testing._models import RunnerOutcome, SelectionReport, TestRunReport
from frob.verify._selection import (
    BatchSelectionError,
    run_batch_selected_tests,
    select_batch_tests,
)
from tests.unit.verify.conftest import make_queue_entry, make_symbol


class TestSelectBatchTests:
    """The pure union-touched-set selection algorithm."""

    def test_union_of_two_entries_selects_once(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_selection.py::TestSelectBatchTests.test_union_of_two_entries_selects_once  # noqa: E501
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::foo": make_symbol("a.py", "foo", 1, 5),
                "b.py::bar": make_symbol("b.py", "bar", 1, 5),
            },
            edges=(
                Edge(
                    kind=EdgeKind.TESTS,
                    src="a.py::foo",
                    target="tests/test_a.py::test_foo",
                    origin="a.py:1",
                ),
                Edge(
                    kind=EdgeKind.TESTS,
                    src="b.py::bar",
                    target="tests/test_b.py::test_bar",
                    origin="b.py:1",
                ),
            ),
        )
        batch = (
            make_queue_entry("c1", "T-0001", ("a.py::foo",)),
            make_queue_entry("c2", "T-0002", ("b.py::bar",)),
        )
        result = select_batch_tests(snapshot, batch)
        assert result.entry_count == 2
        assert result.touched_symbol_count == 2
        selected_ids = {i for ids in result.report.selected.values() for i in ids}
        assert "tests/test_a.py::test_foo" in selected_ids
        assert "tests/test_b.py::test_bar" in selected_ids

    def test_empty_batch_selects_nothing(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_selection.py::TestSelectBatchTests.test_empty_batch_selects_nothing  # noqa: E501
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        result = select_batch_tests(snapshot, ())
        assert result.entry_count == 0
        assert result.touched_symbol_count == 0
        assert all(len(ids) == 0 for ids in result.report.selected.values())

    def test_unresolvable_symbol_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_selection.py::TestSelectBatchTests.test_unresolvable_symbol_is_skipped_not_fatal  # noqa: E501
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"a.py::foo": make_symbol("a.py", "foo", 1, 5)},
            edges=(
                Edge(
                    kind=EdgeKind.TESTS,
                    src="a.py::foo",
                    target="tests/test_a.py::test_foo",
                    origin="a.py:1",
                ),
            ),
        )
        batch = (
            make_queue_entry("c1", "T-0001", ("a.py::foo",)),
            # gone.py::deleted was recorded when it existed, but this
            # snapshot no longer has it (renamed/deleted since) -- must
            # not crash or drop the OTHER entry's real selection.
            make_queue_entry("c2", "T-0002", ("gone.py::deleted",)),
        )
        result = select_batch_tests(snapshot, batch)
        assert result.touched_symbol_count == 2  # union counts both, resolvable or not
        selected_ids = {i for ids in result.report.selected.values() for i in ids}
        assert "tests/test_a.py::test_foo" in selected_ids


class TestRunBatchSelectedTests:
    """The end-to-end entry point: graph load -> selection -> run_selected."""

    def test_graph_unavailable_is_an_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/verify/test_selection.py::TestRunBatchSelectedTests.test_graph_unavailable_is_an_error  # noqa: E501
        from typani.result import Err

        import frob.graph as graph_mod

        monkeypatch.setattr(graph_mod, "load_graph", lambda cache: Err("stale"))
        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Err("cannot build")
        )
        entries = (make_queue_entry("c1", "T-0001", ("a.py::foo",)),)
        result = run_batch_selected_tests(tmp_path, entries)
        assert result.is_err
        assert result.danger_err == BatchSelectionError.GraphUnavailable

    def test_selects_and_runs_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/verify/test_selection.py::TestRunBatchSelectedTests.test_selects_and_runs_once  # noqa: E501
        from typani.result import Ok

        import frob.graph as graph_mod
        import frob.testing._runners as runners_mod

        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"a.py::foo": make_symbol("a.py", "foo", 1, 5)},
            edges=(
                Edge(
                    kind=EdgeKind.TESTS,
                    src="a.py::foo",
                    target="tests/test_a.py::test_foo",
                    origin="a.py:1",
                ),
            ),
        )
        monkeypatch.setattr(graph_mod, "load_graph", lambda cache: Ok(snapshot))

        run_selected_calls: list[SelectionReport] = []

        def fake_run_selected(selection, runners, root):  # noqa: ANN001
            run_selected_calls.append(selection)
            return Ok(
                TestRunReport(
                    selection=selection,
                    outcomes=(
                        RunnerOutcome(
                            language="python",
                            argv=("pytest",),
                            exit_code=0,
                            duration_s=0.1,
                            stdout_tail="",
                            stderr_tail="",
                        ),
                    ),
                    ok=True,
                )
            )

        monkeypatch.setattr(runners_mod, "load_runners", lambda root: Ok(()))
        monkeypatch.setattr(runners_mod, "run_selected", fake_run_selected)

        entries = (make_queue_entry("c1", "T-0001", ("a.py::foo",)),)
        result = run_batch_selected_tests(tmp_path, entries)
        assert result.is_ok
        assert result.danger_ok.ok
        # ONE run_selected call for the whole batch, never one per entry.
        assert len(run_selected_calls) == 1
