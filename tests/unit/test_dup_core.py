"""Unit tests for frob.dup._core's frob_core shims (docs/modules/dup.md's Rust core).

Skips when the `frob_core` native extension is not importable -- the
no-silent-fallback rule means these functions themselves already return
`Err(DupError.CoreUnavailable)` in that case, which
`test_core_unavailable_path_is_err_not_exception` exercises directly.
"""

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
        "wl_hash",
    ):
        assert callable(getattr(frob_core, name))


class TestR3CanonicalHash:
    def test_identical_token_streams_hash_equal(self):
        # frob:tests src/frob/dup/_core.py::r3_canonical_hash kind="unit"
        # frob:tests frob-core/src/lib.rs::r3_canonical_hash kind="unit"
        tokens = ("def", "_v0", "return", "_v0")
        a = _core.r3_canonical_hash(tokens)
        b = _core.r3_canonical_hash(tokens)
        assert a.is_ok and b.is_ok
        assert a.danger_ok == b.danger_ok

    def test_different_token_streams_hash_differently(self):
        a = _core.r3_canonical_hash(("def", "_v0", "return", "_v0"))
        b = _core.r3_canonical_hash(("def", "_v0", "return", "_N_"))
        assert a.danger_ok != b.danger_ok


# frob:tests src/frob/dup/_core.py::winnow_fingerprints kind="unit"
def test_winnow_fingerprints_nonempty_for_long_stream():
    tokens = tuple(f"t{i}" for i in range(20))
    result = _core.winnow_fingerprints(tokens, 4, 4)
    assert result.is_ok
    assert result.danger_ok


# frob:tests src/frob/dup/_core.py::candidate_pairs kind="unit"
def test_candidate_pairs_finds_shared_bucket():
    sets = ((1, 2, 3), (2, 3, 4), (99,))
    result = _core.candidate_pairs(sets, 2)
    assert result.is_ok
    assert result.danger_ok == ((0, 1),)


# frob:tests src/frob/dup/_core.py::tree_edit_similarity kind="unit"
def test_tree_edit_similarity_identical_sequences_is_one():
    result = _core.tree_edit_similarity((1, 2, 3), (1, 2, 3))
    assert result.is_ok
    sim, alignment = result.danger_ok
    assert sim == pytest.approx(1.0)
    assert alignment == ((0, 0), (1, 1), (2, 2))


class TestAptedSimilarity:
    def test_identical_trees_similarity_one(self):
        # frob:tests src/frob/dup/_core.py::apted_similarity kind="unit"
        # frob:tests frob-core/src/lib.rs::apted_similarity kind="unit"
        labels = ("def", "return", "name")
        parents = (-1, 0, 0)
        result = _core.apted_similarity(labels, parents, labels, parents)
        assert result.is_ok
        assert result.danger_ok == pytest.approx(1.0)

    def test_disjoint_single_node_trees_similarity_zero(self):
        result = _core.apted_similarity(("a",), (-1,), ("b",), (-1,))
        assert result.is_ok
        assert result.danger_ok == pytest.approx(0.0)


class TestWlHash:
    def test_relabeled_isomorphic_graphs_collide(self):
        # frob:tests src/frob/dup/_core.py::wl_hash kind="unit"
        # frob:tests frob-core/src/lib.rs::wl_hash kind="unit"
        labels_a = ("def", "use", "use")
        adj_a = ((0, 1), (1, 2), (2, 0))
        labels_b = ("use", "def", "use")
        adj_b = ((1, 0), (0, 2), (2, 1))
        a = _core.wl_hash(adj_a, labels_a, 2)
        b = _core.wl_hash(adj_b, labels_b, 2)
        assert a.is_ok and b.is_ok
        assert a.danger_ok == b.danger_ok

    def test_empty_graph_is_zero(self):
        result = _core.wl_hash((), (), 2)
        assert result.is_ok
        assert result.danger_ok == 0


def test_core_unavailable_path_is_err_not_exception(monkeypatch: pytest.MonkeyPatch):
    """The no-silent-fallback rule: a missing extension is a Result error,
    never a raised exception, for every _core function."""
    _core.core_available.cache_clear()
    monkeypatch.setattr(_core, "core_available", lambda: False)
    assert _core.r3_canonical_hash(("a",)).err == DupError.CoreUnavailable
    assert _core.winnow_fingerprints(("a", "b"), 1, 1).err == DupError.CoreUnavailable
    assert _core.candidate_pairs(((1,),), 1).err == DupError.CoreUnavailable
    assert _core.tree_edit_similarity((1,), (1,)).err == DupError.CoreUnavailable
    assert _core.apted_similarity((), (), (), ()).err == DupError.CoreUnavailable
    assert _core.wl_hash((), (), 1).err == DupError.CoreUnavailable
