"""Tests for helper-inlining / call-graph-aware dup triage (T-0288).

Covers docs/modules/dup.md's "Helper-inlining triage" section: two
functions whose shared logic is split into differently-named private
helpers are only detected as a clone group WITH inlining (litmus 1); a
family of near-identical tiny private helpers is caught by the dedicated
`find_helper_clones` population pass (litmus 2); the inlining bounds
(depth, node cap, cycle guard, public-API stop) are exercised directly
against `frob.graph.callgraph`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DupConfig, find_clones, find_helper_clones
from frob.dup import _core as dup_core
from frob.graph import build_graph
from frob.graph.callgraph import CallGraph, build_call_graph, closure

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dup_inline"


@pytest.fixture()
def snapshot(tmp_path):
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURE_ROOT, cache)
    assert result.is_ok, result.err
    return result.danger_ok


def _pair_refs(report):
    return {
        frozenset((p.left.ref, p.right.ref))
        for group in report.groups
        for p in group.pairs
    }


class TestHelperInliningLitmus:
    def test_split_helpers_detected_with_inlining(self, snapshot):
        # frob:tests \
        # tests/test_dup_inline.py::TestHelperInliningLitmus.test_split_helpers_detecte\
        # d_with_inlining
        result = find_clones(
            snapshot, DupConfig(min_tokens=12, threshold=0.7, inline_calls=True)
        )
        assert result.is_ok, result.err
        refs = _pair_refs(result.danger_ok)
        matched = {
            r
            for r in refs
            if any("process_orders" in x for x in r)
            and any("process_receipts" in x for x in r)
        }
        assert matched, (
            f"expected process_orders/process_receipts clone pair, got {refs}"
        )

    def test_split_helpers_missed_without_inlining(self, snapshot):
        # frob:tests \
        # tests/test_dup_inline.py::TestHelperInliningLitmus.test_split_helpers_missed_\
        # without_inlining
        result = find_clones(
            snapshot, DupConfig(min_tokens=12, threshold=0.7, inline_calls=False)
        )
        assert result.is_ok, result.err
        refs = _pair_refs(result.danger_ok)
        matched = {
            r
            for r in refs
            if any("process_orders" in x for x in r)
            and any("process_receipts" in x for x in r)
        }
        assert not matched, (
            "process_orders/process_receipts should NOT be flagged without "
            f"inlining (arch-forced split hides it), got {refs}"
        )


class TestSharedHelperNotDuplication:
    """T-0288 reviewer-reproduced false positive: two UNRELATED functions
    (distinct own-logic -- different var names, different arithmetic) that
    both call the SAME shared private helper (`_validate` in
    tests/fixtures/dup_inline/src/mod_c.py) must never be reported as a
    clone pair, at any threshold that would otherwise catch it. Sharing a
    helper is normal code reuse; only DIFFERENTLY-NAMED, near-identical
    helpers (`_finalize_a`/`_finalize_b`, covered above) are split-
    duplication."""

    def test_shared_helper_not_flagged_at_default_threshold(self, snapshot):
        # frob:tests \
        # tests/test_dup_inline.py::TestSharedHelperNotDuplication.test_shared_helper_n\
        # ot_flagged_at_default_threshold
        result = find_clones(snapshot, DupConfig(inline_calls=True))
        assert result.is_ok, result.err
        refs = _pair_refs(result.danger_ok)
        matched = {
            r
            for r in refs
            if any("handle_shipping" in x for x in r)
            and any("handle_greeting" in x for x in r)
        }
        assert not matched, (
            "handle_shipping/handle_greeting share only the _validate "
            f"helper (code reuse, not duplication) -- must not be flagged, got {refs}"
        )

    def test_shared_helper_not_flagged_at_threshold_0_7(self, snapshot):
        # frob:tests \
        # tests/test_dup_inline.py::TestSharedHelperNotDuplication.test_shared_helper_n\
        # ot_flagged_at_threshold_0_7
        result = find_clones(snapshot, DupConfig(threshold=0.7, inline_calls=True))
        assert result.is_ok, result.err
        refs = _pair_refs(result.danger_ok)
        matched = {
            r
            for r in refs
            if any("handle_shipping" in x for x in r)
            and any("handle_greeting" in x for x in r)
        }
        assert not matched, (
            "reviewer-reproduced FP: shared-helper inlining pushed "
            f"similarity to 0.708 at threshold=0.7, got {refs}"
        )


class TestHelperPop:
    def test_tiny_helpers(self, snapshot):
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_helper_clones kind="unit"
        result = find_helper_clones(snapshot, DupConfig(threshold=0.7))
        assert result.is_ok, result.err
        refs = _pair_refs(result.danger_ok)
        matched = {r for r in refs if any("_clamp_" in x for x in r) and len(r) == 2}
        assert matched, f"expected a _clamp_* clone pair, got {refs}"

    def test_helper_pass_excludes_public_symbols(self, snapshot):
        # frob:tests \
        # tests/test_dup_inline.py::TestHelperPop.test_helper_pass_excludes_public_symb\
        # ols
        result = find_helper_clones(snapshot, DupConfig(threshold=0.7))
        assert result.is_ok, result.err
        refs = _pair_refs(result.danger_ok)
        for pair in refs:
            for ref in pair:
                assert "public_entry" not in ref
                assert "unrelated_thing" not in ref


class TestCallGraphBounds:
    def test_call_edge(self):
        # frob:tests src/frob/graph/callgraph.py::build_call_graph kind="unit"
        graph = build_call_graph(FIXTURE_ROOT, ["src/mod_a.py"])
        callees = graph.calls.get("src/mod_a.py::process_orders", ())
        assert "src/mod_a.py::_finalize_a" in callees

    def test_closure_is_cycle_guarded(self):
        # frob:tests \
        # tests/test_dup_inline.py::TestCallGraphBounds.test_closure_is_cycle_guarded
        graph = CallGraph(
            calls={
                "a.py::_x": ("a.py::_y",),
                "a.py::_y": ("a.py::_x",),
            }
        )
        result = closure(graph, "a.py::_x", max_depth=10, max_nodes=10)
        assert result == ("a.py::_y",)

    def test_closure_respects_node_cap(self):
        # frob:tests \
        # tests/test_dup_inline.py::TestCallGraphBounds.test_closure_respects_node_cap
        calls = {"a.py::_root": tuple(f"a.py::_h{i}" for i in range(10))}
        graph = CallGraph(calls=calls)
        result = closure(graph, "a.py::_root", max_depth=5, max_nodes=3)
        assert len(result) == 3

    def test_closure_respects_depth_cap(self):
        # frob:tests \
        # tests/test_dup_inline.py::TestCallGraphBounds.test_closure_respects_depth_cap
        graph = CallGraph(
            calls={
                "a.py::_a": ("a.py::_b",),
                "a.py::_b": ("a.py::_c",),
                "a.py::_c": ("a.py::_d",),
            }
        )
        result = closure(graph, "a.py::_a", max_depth=1, max_nodes=10)
        assert result == ("a.py::_b",)

    # invariant spec: [INV-014](invariants/INV-014.md)
    def test_public_callee_never_becomes_an_edge(self):
        # frob:tests \
        # tests/test_dup_inline.py::TestCallGraphBounds.test_public_callee_never_become\
        # s_an_edge
        graph = build_call_graph(FIXTURE_ROOT, ["src/mod_b.py"])
        callees = graph.calls.get("src/mod_b.py::public_entry", ())
        assert "src/mod_b.py::normalize" not in callees
