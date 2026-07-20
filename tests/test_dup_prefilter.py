"""Tests for the R4 candidate pre-filters (T-0197, docs/modules/dup-sota-survey.md
survey items 2/4/6): DECKARD characteristic vectors, Oreo metric ratios, NiCad
size ratios, all applied as additive pruning in front of `_r4_verify_pair`.

Two kinds of coverage, per the ticket's own instruction ("prefilters only
prune pairs, never add false positives -- test that enabling them never
changes the verified-clone set on fixtures, only the pair count examined"):

- Unit tests on the three predicate functions directly (`_nicad_size_ratio_ok`,
  `_oreo_metric_ratio_ok`, `_deckard_vector_ok`, `_characteristic_vector`,
  `_cosine_similarity`) -- fast, no `frob_core` dependency.
- Recall-preservation tests: run `find_clones` over every existing dup
  fixture with `prefilter_enabled=True` (default) and `prefilter_enabled=
  False`, and assert the two runs report the EXACT same set of
  `(rung, left.ref, right.ref, similarity)` tuples. This is the actual
  regression guard for "a prefilter that changes results is a bug".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DupConfig, find_clones
from frob.dup import _core as dup_core
from frob.dup._pipeline import (
    _characteristic_vector,
    _cosine_similarity,
    _deckard_vector_ok,
    _FpState,
    _nicad_size_ratio_ok,
    _oreo_metric_ratio_ok,
)
from frob.graph import build_graph

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)

FIXTURES_ROOT = Path(__file__).parent / "fixtures"
DUP_FIXTURE_DIRS = ("dup_smart", "dup_rungs", "dup_region", "dup_inline")


def _all_pairs(report):
    """Every `(rung, left.ref, right.ref, similarity)` in a `CloneReport`,
    order-independent (refs sorted per pair) so set comparison is exact."""
    out = set()
    for group in report.groups:
        for p in group.pairs:
            # frob:waive PERF004 reason="sorts each pair's own 2-tuple; data differs per iteration, O(1), cannot be hoisted"
            refs = tuple(sorted((p.left.ref, p.right.ref)))
            out.add((p.rung, refs[0], refs[1], round(p.similarity, 6)))
    return out


class TestCharacteristicVector:
    # frob:tests tests/test_dup_prefilter.py::TestCharacteristicVector kind="unit"
    def test_identical_streams_have_identical_vectors(self):
        toks = ("def", "_v0", "(", "_v1", ")", ":", "return", "_v1")
        assert _characteristic_vector(toks) == _characteristic_vector(toks)

    def test_placeholder_count_position_does_not_matter_only_bucket_count(self):
        # Two differently-numbered but same-COUNT placeholder streams collapse
        # to the same IDENT bucket total -- DECKARD's rename-invariance.
        a = ("_v0", "+", "_v1")
        b = ("_v3", "+", "_v9")
        assert _characteristic_vector(a) == _characteristic_vector(b)

    def test_empty_stream_is_empty_vector(self):
        assert _characteristic_vector(()) == {}


class TestCosineSimilarity:
    # frob:tests tests/test_dup_prefilter.py::TestCosineSimilarity kind="unit"
    def test_identical_vectors_are_similarity_one(self):
        vec = {"IDENT": 3, "+": 1}
        assert _cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_disjoint_vectors_are_similarity_zero(self):
        assert _cosine_similarity({"IDENT": 3}, {"return": 2}) == 0.0

    def test_both_empty_is_similarity_one(self):
        assert _cosine_similarity({}, {}) == 1.0

    def test_one_empty_is_similarity_zero(self):
        assert _cosine_similarity({"IDENT": 1}, {}) == 0.0


def _state(**cfg_kwargs) -> _FpState:
    return _FpState(root=Path("."), cfg=DupConfig(**cfg_kwargs))


class TestNicadSizeRatio:
    # frob:tests tests/test_dup_prefilter.py::TestNicadSizeRatio kind="unit"
    def test_similar_sizes_pass(self):
        state = _state()
        state.size_by_ref = {"a": 100, "b": 90}
        assert _nicad_size_ratio_ok(state, "a", "b") is True

    def test_wildly_different_sizes_rejected(self):
        state = _state()
        state.size_by_ref = {"a": 500, "b": 5}
        assert _nicad_size_ratio_ok(state, "a", "b") is False

    def test_missing_size_passes_through(self):
        state = _state()
        state.size_by_ref = {"a": 100}
        assert _nicad_size_ratio_ok(state, "a", "b") is True


class TestOreoMetricRatio:
    # frob:tests tests/test_dup_prefilter.py::TestOreoMetricRatio kind="unit"
    def test_similar_branch_counts_pass(self):
        state = _state()
        state.metric_by_ref = {"a": 3, "b": 4}
        assert _oreo_metric_ratio_ok(state, "a", "b") is True

    def test_both_zero_branch_count_passes(self):
        state = _state()
        state.metric_by_ref = {"a": 0, "b": 0}
        assert _oreo_metric_ratio_ok(state, "a", "b") is True

    def test_wildly_different_branch_counts_rejected(self):
        state = _state()
        state.metric_by_ref = {"a": 40, "b": 0}
        assert _oreo_metric_ratio_ok(state, "a", "b") is False


class TestDeckardVector:
    # frob:tests tests/test_dup_prefilter.py::TestDeckardVector kind="unit"
    def test_similar_shape_passes(self):
        state = _state()
        state.vector_by_ref = {
            "a": {"IDENT": 5, "return": 1, "+": 2},
            "b": {"IDENT": 5, "return": 1, "+": 2},
        }
        assert _deckard_vector_ok(state, "a", "b") is True

    def test_disjoint_shape_rejected(self):
        state = _state()
        state.vector_by_ref = {
            "a": {"IDENT": 5, "return": 1},
            "b": {"for": 3, "while": 2},
        }
        assert _deckard_vector_ok(state, "a", "b") is False

    def test_missing_vector_passes_through(self):
        state = _state()
        state.vector_by_ref = {"a": {"IDENT": 1}}
        assert _deckard_vector_ok(state, "a", "b") is True


@pytest.mark.parametrize("fixture_dir", DUP_FIXTURE_DIRS)
class TestPrefilterPreservesRecall:
    """The ticket's own instruction: enabling the prefilters must never
    change the verified-clone set, only the pair count examined."""

    def test_verified_clone_set_unchanged(self, fixture_dir, tmp_path):
        root = FIXTURES_ROOT / fixture_dir
        cache = tmp_path / "graph-cache"
        snapshot_result = build_graph(root, cache)
        assert snapshot_result.is_ok, snapshot_result.err
        snapshot = snapshot_result.danger_ok

        with_prefilter = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85, prefilter_enabled=True)
        )
        without_prefilter = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85, prefilter_enabled=False)
        )
        assert with_prefilter.is_ok, with_prefilter.err
        assert without_prefilter.is_ok, without_prefilter.err

        assert _all_pairs(with_prefilter.danger_ok) == _all_pairs(
            without_prefilter.danger_ok
        )

    def test_prefilter_never_exceeds_unfiltered_verification_count(
        self, fixture_dir, tmp_path
    ):
        # frob:tests tests/test_dup_prefilter.py::TestPrefilterPreservesRecall kind="unit"
        root = FIXTURES_ROOT / fixture_dir
        cache = tmp_path / "graph-cache"
        snapshot_result = build_graph(root, cache)
        assert snapshot_result.is_ok, snapshot_result.err
        snapshot = snapshot_result.danger_ok

        with_prefilter = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85, prefilter_enabled=True)
        ).danger_ok
        without_prefilter = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85, prefilter_enabled=False)
        ).danger_ok

        # Pure additive pruning: never MORE verification work with the
        # prefilters on than off.
        assert (
            with_prefilter.stats.pairs_verified
            <= without_prefilter.stats.pairs_verified
        )
        assert without_prefilter.stats.pairs_prefiltered == 0
