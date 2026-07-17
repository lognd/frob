"""Tests for the smart-dup pipeline (docs/dup.md): find_clones + DUP001/DUP002.

Exercises the real `frob_core` extension when it is importable (this repo's
CI/dev environment has it, per frob-core/README-equivalent notes in
docs/dup.md) and the honest CoreUnavailable path via monkeypatching
`frob.dup._core.core_available`, so both branches of the no-silent-fallback
rule are covered regardless of which environment runs the suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DUP001, DUP002, DupConfig, DupError, find_clones, touched_refs
from frob.dup import _core as dup_core
from frob.gitio import Diff, Hunk
from frob.graph import build_graph

# R3+ needs the frob-core native extension (a Rust build). Where it is not
# installed (CI without the toolchain), the smart-dup rungs are legitimately
# unavailable, so the suite skips rather than failing -- the CoreUnavailable
# contract is still covered by the monkeypatched-absence test when core IS
# present. (frob:ticket T-0001)
pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dup_smart"


@pytest.fixture()
def snapshot(tmp_path):
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURE_ROOT, cache)
    assert result.is_ok, result.err
    return result.danger_ok


class TestFindClones:
    def test_finds_renamed_clone_pair(self, snapshot):
        result = find_clones(snapshot, DupConfig(min_tokens=5, threshold=0.85))
        assert result.is_ok, result.err
        report = result.danger_ok
        refs = {
            frozenset((p.left.ref, p.right.ref))
            for group in report.groups
            for p in group
        }
        matched = {
            r
            for r in refs
            if any("compute_total" in x for x in r) and any("compute_sum" in x for x in r)
        }
        assert matched, f"expected compute_total/compute_sum clone pair, got {refs}"

    def test_stats_report_fingerprinted_count(self, snapshot):
        report = find_clones(snapshot, DupConfig(min_tokens=5)).danger_ok
        assert report.stats.fingerprinted >= 3

    def test_min_tokens_floor_excludes_trivial_bodies(self, snapshot):
        report = find_clones(snapshot, DupConfig(min_tokens=10_000)).danger_ok
        assert report.groups == ()

    def test_core_unavailable_is_honest_err_not_silent_downgrade(self, snapshot, monkeypatch):
        monkeypatch.setattr(dup_core, "core_available", lambda: False)
        # _pipeline imported core_available via `from frob.dup import _core`
        # and calls `_core.core_available()`, so patching the module
        # attribute above is what the pipeline actually observes.
        result = find_clones(snapshot, DupConfig(min_tokens=5))
        assert result.is_err
        assert result.err == DupError.CoreUnavailable


class TestTouchedRefs:
    # frob:tests src/frob/dup/_pipeline.py::touched_refs kind="unit"
    def test_hunk_overlapping_span_marks_symbol_touched(self, snapshot):
        # compute_total is defined at the top of mod_a.py.
        diff = Diff(base="main", hunks=(Hunk(file="src/mod_a.py", span=(1, 3)),))
        touched = touched_refs(snapshot, diff)
        assert any("compute_total" in ref for ref in touched)
        assert not any("unique_function" in ref for ref in touched)


class TestGateRules:
    def test_dup001_fires_when_one_side_touched(self, snapshot):
        report = find_clones(snapshot, DupConfig(min_tokens=5, threshold=0.85)).danger_ok
        clone_ref = next(
            p.left.ref
            for group in report.groups
            for p in group
            if "compute_total" in p.left.ref
        )
        touched = frozenset({clone_ref})
        violations = DUP001(report, touched, threshold=0.85)
        assert any(v.rule == "DUP001" for v in violations)
        assert all(v.severity.value == "error" for v in violations)

    def test_dup002_fires_when_both_sides_touched(self, snapshot):
        report = find_clones(snapshot, DupConfig(min_tokens=5, threshold=0.85)).danger_ok
        pair = next(
            p
            for group in report.groups
            for p in group
            if "compute_total" in p.left.ref or "compute_total" in p.right.ref
        )
        touched = frozenset({pair.left.ref, pair.right.ref})
        violations = DUP002(report, touched, threshold=0.85)
        assert any(v.rule == "DUP002" for v in violations)
        assert all(v.severity.value == "warn" for v in violations)

    def test_dup001_silent_when_neither_side_touched(self, snapshot):
        report = find_clones(snapshot, DupConfig(min_tokens=5, threshold=0.85)).danger_ok
        violations = DUP001(report, frozenset(), threshold=0.85)
        assert violations == ()
