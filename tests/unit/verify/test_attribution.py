"""Unit tests for `frob.verify._attribution` (T-1690): symbolic
attribution of a red batch's findings to the commit that caused them."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.graph import CallGraph, GraphSnapshot
from frob.verify._attribution import AttributionError, attribute_batch
from tests.unit.verify.conftest import make_queue_entry, make_symbol


class TestAttributeBatch:
    """The graph-reachability rule: a finding attributes to the batch
    commit whose touched symbols REACH it, never a lexical file match or
    a newest-commit tiebreak."""

    def test_caller_break_attributes_to_the_caller_commit(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_caller_break_attributes_to_the_caller_commit  # noqa: E501
        # Commit A touches `caller`, which calls `callee` -- commit B
        # touched `callee` itself, unrelated to the finding. The finding
        # is anchored at `caller` (a broken caller, not the callee), so it
        # must attribute to A, not B.
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::caller": make_symbol("a.py", "caller", 1, 5),
                "b.py::callee": make_symbol("b.py", "callee", 1, 5),
            },
            edges=(),
        )
        call_graph = CallGraph(calls={"a.py::caller": ("b.py::callee",)})
        batch = (
            make_queue_entry("commitA", "T-0001", ("a.py::caller",)),
            make_queue_entry("commitB", "T-0002", ("b.py::callee",)),
        )
        result = attribute_batch(
            tmp_path,
            [("RULE1", "a.py", 3)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "attributed"
        assert attribution.commit_sha == "commitA"
        assert attribution.ticket_id == "T-0001"
        assert attribution.reachability_path == ("a.py::caller",)

    def test_direct_touch_attributes_at_depth_zero(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_direct_touch_attributes_at_depth_zero  # noqa: E501
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"a.py::fn": make_symbol("a.py", "fn", 1, 5)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        batch = (make_queue_entry("commitA", "T-0001", ("a.py::fn",)),)
        result = attribute_batch(
            tmp_path,
            [("RULE1", "a.py", 2)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "attributed"
        assert attribution.commit_sha == "commitA"
        assert attribution.reachability_path == ("a.py::fn",)

    def test_two_reaching_commits_is_unattributed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_two_reaching_commits_is_unattributed  # noqa: E501
        # Both commits touch symbols that reach the same finding -- never
        # pick the newest as a tiebreak; report UNATTRIBUTED with both
        # candidates named.
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"shared.py::fn": make_symbol("shared.py", "fn", 1, 5)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        batch = (
            make_queue_entry("commitA", "T-0001", ("shared.py::fn",)),
            make_queue_entry("commitB", "T-0002", ("shared.py::fn",)),
        )
        result = attribute_batch(
            tmp_path,
            [("RULE1", "shared.py", 2)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "unattributed"
        assert set(attribution.candidate_commits) == {"commitA", "commitB"}
        assert attribution.commit_sha is None
        assert attribution.ticket_id is None

    def test_zero_reaching_commits_is_unattributed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_zero_reaching_commits_is_unattributed  # noqa: E501
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={"orphan.py::fn": make_symbol("orphan.py", "fn", 1, 5)},
            edges=(),
        )
        call_graph = CallGraph(calls={})
        batch = (make_queue_entry("commitA", "T-0001", ("unrelated.py::other",)),)
        result = attribute_batch(
            tmp_path,
            [("RULE1", "orphan.py", 2)],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "unattributed"
        assert attribution.candidate_commits == ()

    def test_missing_line_falls_back_to_whole_file_candidates(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_missing_line_falls_back_to_whole_file_candidates  # noqa: E501
        # No line number: the finding's candidate set is every symbol in
        # the file. One of two symbols is reachable from commit A -- still
        # a clean single-candidate attribution.
        snapshot = GraphSnapshot(
            root=str(tmp_path),
            symbols={
                "a.py::fn_one": make_symbol("a.py", "fn_one", 1, 5),
                "a.py::fn_two": make_symbol("a.py", "fn_two", 6, 10),
            },
            edges=(),
        )
        call_graph = CallGraph(calls={"caller.py::caller": ("a.py::fn_two",)})
        batch = (make_queue_entry("commitA", "T-0001", ("caller.py::caller",)),)
        result = attribute_batch(
            tmp_path,
            [("RULE1", "a.py")],
            batch,
            graph_and_calls=(snapshot, call_graph),
        )
        assert result.is_ok
        (attribution,) = result.danger_ok
        assert attribution.status == "attributed"
        assert attribution.commit_sha == "commitA"
        assert attribution.symbol is None  # no line -> no single-symbol resolution

    def test_graph_unavailable_is_an_error_for_the_whole_batch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/verify/test_attribution.py::TestAttributeBatch.test_graph_unavailable_is_an_error_for_the_whole_batch  # noqa: E501
        import frob.verify._attribution as attribution_mod

        monkeypatch.setattr(
            attribution_mod, "_load_snapshot_and_call_graph", lambda root: None
        )
        result = attribute_batch(
            tmp_path,
            [("RULE1", "a.py", 1)],
            (make_queue_entry("commitA", "T-0001", ("a.py::fn",)),),
        )
        assert result.is_err
        assert result.danger_err is AttributionError.GraphUnavailable
