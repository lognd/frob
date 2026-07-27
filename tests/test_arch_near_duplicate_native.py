"""Golden-parity coverage for T-0953: `frob_core.near_duplicate_indices`
(archgate's `_near_duplicate_cluster` body-similarity clustering, ported to
a `frob_core` kernel) must return cluster output byte-identical to
`difflib.SequenceMatcher.ratio()` at `_BODY_SIMILARITY_THRESHOLD`, both on a
synthetic archgate-triggering fixture and on this repo's own real
`src/frob/arch` tree."""

from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from frob.arch._python import (
    _BODY_MIN_TOKENS,
    _BODY_SIMILARITY_THRESHOLD,
    _near_duplicate_cluster,
)
from frob.dup._core import core_available

pytestmark = pytest.mark.skipif(
    not core_available(), reason="frob_core native extension not built"
)


def _python_reference_indices(bodies: list[str], threshold: float) -> list[int]:
    """Reference implementation: the exact pairwise `difflib` loop
    `_near_duplicate_cluster` ran before T-0953 -- independent of both the
    native kernel and `_near_duplicate_cluster`'s own current dispatch, so
    this cannot pass by construction."""
    idx: set[int] = set()
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            ratio = difflib.SequenceMatcher(None, bodies[i], bodies[j]).ratio()
            if ratio >= threshold:
                idx.add(i)
                idx.add(j)
    return sorted(idx)


def test_native_kernel_matches_difflib_on_synthetic_archgate_fixture():
    # frob:tests frob-core/src/lib.rs::near_duplicate_indices
    # Mirrors the shape of tests/unit/test_arch.py's
    # test_accidental_same_signature_still_flagged fixture: two genuine
    # near-duplicate bodies (validate-then-transform, differing only in
    # which str method is called) plus unrelated members in the same group.
    import frob_core

    bodies = [
        "_S_ cleaned = _v0 . strip ( ) if not cleaned : raise _S_ return cleaned",
        "_S_ cleaned = _v0 . lower ( ) if not cleaned : raise _S_ return cleaned",
        "_S_ total = _N_ for _v0 in _v1 : total += _v0 return total",
        "_S_ return _v0 + _v1",
    ]
    expected = _python_reference_indices(bodies, _BODY_SIMILARITY_THRESHOLD)
    actual = sorted(
        frob_core.near_duplicate_indices(bodies, _BODY_SIMILARITY_THRESHOLD)
    )
    assert actual == expected
    assert actual == [0, 1]


def test_near_duplicate_cluster_dispatches_to_native_and_matches_reference():
    # frob:tests src/frob/arch/_python.py::_near_duplicate_cluster
    # Exercises the public `_near_duplicate_cluster` entry point (native
    # dispatch included) against the same fixture, proving the wired
    # function -- not just the raw kernel -- is byte-identical to the
    # pure-Python reference.
    members = [
        ("a.py", "normalize_alpha", "_S_ cleaned = _v0 . strip ( ) return cleaned _S_"),
        ("b.py", "normalize_beta", "_S_ cleaned = _v0 . lower ( ) return cleaned _S_"),
        ("c.py", "unrelated_one", "_S_ total = _N_ for _v0 in _v1 : total += _v0"),
        ("d.py", "unrelated_two", "_S_ return _v0 + _v1"),
    ]
    bodies = [m[2] for m in members]
    expected_idx = _python_reference_indices(bodies, _BODY_SIMILARITY_THRESHOLD)
    result = _near_duplicate_cluster(members)
    assert [members[i] for i in expected_idx] == result


def test_native_kernel_matches_difflib_over_this_repos_own_arch_tree():
    # frob:tests frob-core/src/lib.rs::near_duplicate_indices
    # Real-data parity sweep: every same-signature group this repo's own
    # archgate run over src/frob/arch actually produces, native vs the
    # pure-Python `difflib` reference, must agree exactly.
    import frob_core

    from frob.arch import _python as ap

    root = Path(__file__).resolve().parents[1] / "src" / "frob" / "arch"
    groups: list[list[str]] = []
    original = ap._near_duplicate_cluster

    def _capture(members: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
        eligible = [m for m in members if len(m[2].split()) >= _BODY_MIN_TOKENS]
        if len(eligible) >= 2:
            groups.append([m[2] for m in eligible])
        return original(members)

    ap._near_duplicate_cluster = _capture  # ty: ignore[invalid-assignment]
    try:
        from frob.arch import analyze_project

        analyze_project(root)
    finally:
        ap._near_duplicate_cluster = original

    assert groups, "expected at least one same-signature group over src/frob/arch"
    for bodies in groups:
        expected = _python_reference_indices(bodies, _BODY_SIMILARITY_THRESHOLD)
        actual = sorted(
            frob_core.near_duplicate_indices(bodies, _BODY_SIMILARITY_THRESHOLD)
        )
        assert actual == expected
