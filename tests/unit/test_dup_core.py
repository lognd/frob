"""Unit tests for frob.dup._core's frob_core shims (docs/modules/dup.md's Rust core).

Skips when the `frob_core` native extension is not importable -- the
no-silent-fallback rule means these functions themselves already return
`Err(DupError.CoreUnavailable)` in that case, which
`test_core_unavailable_path_is_err_not_exception` exercises directly.
"""

# frob:waive OPAQUE001 reason="T-1038: the getattr(...) below resolves a \
# fixture-module attribute by a name this test itself constructs, standard \
# test-fixture introspection -- deliberate test infrastructure, not an evasion risk \
# over untrusted input"

from __future__ import annotations

import pytest

from frob.dup import _core
from frob.dup._models import DupError

HAS_CORE = _core.core_available()
pytestmark = pytest.mark.skipif(not HAS_CORE, reason="frob_core not installed")


# frob:tests src/frob/dup/_core.py::core_available kind="unit"
def test_core_available_returns_bool():
    assert isinstance(_core.core_available(), bool)


# frob:tests frob-core/src/lib.rs::frob_core kind="unit"
def test_frob_core_module_registers_exported_kernels():
    # frob:tests frob-core/src/lib.rs kind="integration"
    # The #[pymodule] registration entry is what wires the Rust kernels into
    # Python; assert the module imports and exposes its exported surface.
    import frob_core

    for name in (
        "r3_canonical_hash",
        "winnow_fingerprints",
        "candidate_pairs",
        "tree_edit_similarity",
        "apted_similarity",
        "anti_unify",
        "wl_hash",
        "exact_regions",
    ):
        assert callable(getattr(frob_core, name))


class TestR3CanonicalHash:
    def test_identical_token_streams_hash_equal(self):
        # frob:tests src/frob/dup/_core.py::_r3_canonical_hash kind="unit"
        # frob:tests frob-core/src/lib.rs::r3_canonical_hash kind="unit"
        tokens = ("def", "_v0", "return", "_v0")
        a = _core._r3_canonical_hash(tokens)
        b = _core._r3_canonical_hash(tokens)
        assert a.is_ok and b.is_ok
        assert a.danger_ok == b.danger_ok

    def test_different_token_streams_hash_differently(self):
        a = _core._r3_canonical_hash(("def", "_v0", "return", "_v0"))
        b = _core._r3_canonical_hash(("def", "_v0", "return", "_N_"))
        assert a.danger_ok != b.danger_ok


# frob:tests src/frob/dup/_core.py::_winnow_fingerprints kind="unit"
def test_winnow_fingerprints_nonempty_for_long_stream():
    tokens = tuple(f"t{i}" for i in range(20))
    result = _core._winnow_fingerprints(tokens, 4, 4)
    assert result.is_ok
    assert result.danger_ok


# frob:tests src/frob/dup/_core.py::_candidate_pairs kind="unit"
def test_candidate_pairs_finds_shared_bucket():
    sets = ((1, 2, 3), (2, 3, 4), (99,))
    result = _core._candidate_pairs(sets, 2)
    assert result.is_ok
    assert result.danger_ok == ((0, 1),)


# frob:tests frob-core/src/lib.rs::candidate_pairs kind="unit"
def test_candidate_pairs_never_returns_a_self_pair():
    # Regression for T-0268: a region whose own fingerprint set contains a
    # duplicate value indexes itself twice into one bucket, which previously
    # surfaced as a self-pair (i, i) once the self-collision count reached
    # min_shared. Guards every Python caller of the kernel, not just the one
    # _r4_groups site T-0191 patched.
    result = _core._candidate_pairs(((7, 7, 7), (99,)), 2)
    assert result.is_ok
    assert all(i != j for i, j in result.danger_ok)
    assert result.danger_ok == ()


# frob:tests src/frob/dup/_core.py::_tree_edit_similarity kind="unit"
def test_tree_edit_similarity_identical_sequences_is_one():
    result = _core._tree_edit_similarity((1, 2, 3), (1, 2, 3))
    assert result.is_ok
    sim, alignment = result.danger_ok
    assert sim == pytest.approx(1.0)
    assert alignment == ((0, 0), (1, 1), (2, 2))


class TestAptedSimilarity:
    def test_identical_trees_similarity_one(self):
        # frob:tests src/frob/dup/_core.py::_apted_similarity kind="unit"
        # frob:tests frob-core/src/lib.rs::apted_similarity kind="unit"
        labels = ("def", "return", "name")
        parents = (-1, 0, 0)
        result = _core._apted_similarity(labels, parents, labels, parents)
        assert result.is_ok
        assert result.danger_ok == pytest.approx(1.0)

    def test_disjoint_single_node_trees_similarity_zero(self):
        result = _core._apted_similarity(("a",), (-1,), ("b",), (-1,))
        assert result.is_ok
        assert result.danger_ok == pytest.approx(0.0)


class TestAntiUnify:
    def test_identical_trees_zero_holes(self):
        # frob:tests src/frob/dup/_core.py::anti_unify kind="unit"
        # frob:tests frob-core/src/lib.rs::anti_unify kind="unit"
        labels = ("def", "return", "name")
        parents = (-1, 0, 0)
        result = _core.anti_unify(labels, parents, labels, parents)
        assert result.is_ok
        tpl = result.danger_ok
        assert tpl.labels == labels
        assert tpl.parents == parents
        assert tpl.bindings_a == ()
        assert tpl.bindings_b == ()

    def test_two_near_identical_trees_bind_one_hole(self):
        # frob:tests src/frob/dup/_core.py::anti_unify kind="unit"
        # Trees differing in exactly one leaf ("x" vs "y") -- template
        # keeps the shared "def"/"return" shape and binds one hole to the
        # two diverging leaves.
        labels_a = ("def", "return", "x")
        parents_a = (-1, 0, 0)
        labels_b = ("def", "return", "y")
        parents_b = (-1, 0, 0)
        result = _core.anti_unify(labels_a, parents_a, labels_b, parents_b)
        assert result.is_ok
        tpl = result.danger_ok
        assert tpl.labels == ("def", "return", "$hole_0")
        assert tpl.bindings_a == ((0, 2),)
        assert tpl.bindings_b == ((0, 2),)

    def test_arity_divergence_is_a_hole_not_a_crash(self):
        # frob:tests src/frob/dup/_core.py::anti_unify kind="unit"
        labels_a = ("root", "shared", "mid", "a")
        parents_a = (-1, 0, 0, 2)
        labels_b = ("root", "shared", "mid", "a", "b")
        parents_b = (-1, 0, 0, 2, 2)
        result = _core.anti_unify(labels_a, parents_a, labels_b, parents_b)
        assert result.is_ok
        tpl = result.danger_ok
        assert tpl.labels == ("root", "shared", "$hole_0")

    def test_wildly_different_trees_exceed_hole_ceiling(self):
        # frob:tests src/frob/dup/_core.py::anti_unify kind="unit"
        labels_a = ("def", "x", "y")
        parents_a = (-1, 0, 0)
        labels_b = ("class", "p", "q", "r")
        parents_b = (-1, 0, 0, 0)
        result = _core.anti_unify(labels_a, parents_a, labels_b, parents_b)
        assert result.err == DupError.HoleCeilingExceeded

    def test_deterministic_across_repeated_calls(self):
        # frob:tests src/frob/dup/_core.py::anti_unify kind="unit"
        labels_a = ("root", "s1", "dA1", "s2", "dA2")
        parents_a = (-1, 0, 0, 0, 0)
        labels_b = ("root", "s1", "dB1", "s2", "dB2")
        parents_b = (-1, 0, 0, 0, 0)
        first = _core.anti_unify(labels_a, parents_a, labels_b, parents_b)
        second = _core.anti_unify(labels_a, parents_a, labels_b, parents_b)
        assert first.is_ok and second.is_ok
        assert first.danger_ok == second.danger_ok


class TestWlHash:
    def test_relabeled_isomorphic_graphs_collide(self):
        # frob:tests src/frob/dup/_core.py::_wl_hash kind="unit"
        # frob:tests frob-core/src/lib.rs::wl_hash kind="unit"
        labels_a = ("def", "use", "use")
        adj_a = ((0, 1), (1, 2), (2, 0))
        labels_b = ("use", "def", "use")
        adj_b = ((1, 0), (0, 2), (2, 1))
        a = _core._wl_hash(adj_a, labels_a, 2)
        b = _core._wl_hash(adj_b, labels_b, 2)
        assert a.is_ok and b.is_ok
        assert a.danger_ok == b.danger_ok

    def test_empty_graph_is_zero(self):
        result = _core._wl_hash((), (), 2)
        assert result.is_ok
        assert result.danger_ok == 0


class TestExactRegions:
    def test_finds_shared_block_inside_different_documents(self):
        # frob:tests src/frob/dup/_core.py::_exact_regions kind="unit"
        # frob:tests frob-core/src/lib.rs::exact_regions kind="unit"
        shared = ("if", "x", ">", "0", "return", "x")
        doc_a = ("def", "foo", "(", *shared, "else", "return", "0")
        doc_b = ("def", "bar", "(", "y", ")", *shared, "print", "y")
        result = _core._exact_regions((doc_a, doc_b), len(shared))
        assert result.is_ok
        regions, truncated = result.danger_ok
        assert truncated is False
        assert len(regions) == 1
        doc_a_idx, start_a, doc_b_idx, start_b, length = regions[0]
        assert (doc_a_idx, doc_b_idx, length) == (0, 1, len(shared))
        assert doc_a[start_a : start_a + length] == shared
        assert doc_b[start_b : start_b + length] == shared

    def test_below_min_len_finds_nothing(self):
        shared = ("a", "b", "c")
        result = _core._exact_regions((shared, shared), 10)
        assert result.is_ok
        regions, truncated = result.danger_ok
        assert regions == ()
        assert truncated is False

    def test_no_shared_tokens_finds_nothing(self):
        result = _core._exact_regions((("a", "b"), ("x", "y")), 1)
        assert result.is_ok
        regions, truncated = result.danger_ok
        assert regions == ()
        assert truncated is False

    def test_run_size_guard_bounds_pair_emission_and_signals_truncation(self):
        # frob:tests src/frob/dup/_core.py::_exact_regions kind="unit"
        # frob:tests frob-core/src/lib.rs::exact_regions kind="unit"
        # T-0273: a run of 500 identical documents must not emit the
        # unbounded C(500, 2) = 124,750 pairs -- with a cap of 50 it must
        # emit at most C(50, 2) = 1,225 and report truncated=True.
        block = ("a", "b", "c", "d")
        docs = tuple(block for _ in range(500))
        result = _core._exact_regions(docs, 2, max_run_size=50)
        assert result.is_ok
        regions, truncated = result.danger_ok
        assert truncated is True
        assert len(regions) <= 50 * 49 // 2
        assert len(regions) > 0

    def test_run_size_guard_does_not_trip_below_the_cap(self):
        block = ("a", "b", "c", "d")
        docs = tuple(block for _ in range(5))
        result = _core._exact_regions(docs, 2, max_run_size=50)
        assert result.is_ok
        regions, truncated = result.danger_ok
        assert truncated is False
        assert len(regions) == 5 * 4 // 2


def test_core_unavailable_path_is_err_not_exception(monkeypatch: pytest.MonkeyPatch):
    """The no-silent-fallback rule: a missing extension is a Result error,
    never a raised exception, for every _core function."""
    _core.core_available.cache_clear()
    monkeypatch.setattr(_core, "core_available", lambda: False)
    assert _core._r3_canonical_hash(("a",)).err == DupError.CoreUnavailable
    assert _core._winnow_fingerprints(("a", "b"), 1, 1).err == DupError.CoreUnavailable
    assert _core._candidate_pairs(((1,),), 1).err == DupError.CoreUnavailable
    assert _core._tree_edit_similarity((1,), (1,)).err == DupError.CoreUnavailable
    assert _core._apted_similarity((), (), (), ()).err == DupError.CoreUnavailable
    assert _core.anti_unify((), (), (), ()).err == DupError.CoreUnavailable
    assert _core._wl_hash((), (), 1).err == DupError.CoreUnavailable
    assert _core._exact_regions((("a",), ("a",)), 1).err == DupError.CoreUnavailable
