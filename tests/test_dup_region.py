"""Tests for the R1.5 exact-region kernel (docs/modules/dup.md's rung table,
T-0193): a generalized-suffix-array pass that finds a copy-pasted block
living inside two otherwise-different symbol bodies -- the exact shape
R1/R2 (whole-symbol-body hashing, `frob.dup._pipeline._r1_hash`/
`_r2_hash`) structurally cannot see, because neither whole body is
identical or an alpha-rename of the other.

`tests/fixtures/dup_region/src/{mod_a,mod_b}.py` plant exactly that shape:
`alpha_process`/`beta_transform` share one identical 6-line block (the
`items`/`for entry`/`if entry is None`/`cleaned`/`result.append` sequence)
but differ everywhere else (different call names before/after, different
function/parameter names) -- enough that neither R1's exact hash nor R2's
alpha-renamed hash of the *whole* body collides.

Skips (rather than fails) when `frob_core` is not installed -- same
posture as tests/test_dup_smart.py/tests/test_dup_rungs.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DupConfig, find_clones
from frob.dup import _core as dup_core
from frob.graph import build_graph

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dup_region"


@pytest.fixture()
def snapshot(tmp_path):
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURE_ROOT, cache)
    assert result.is_ok, result.err
    return result.danger_ok


def _r1_5_pairs(report):
    return [
        (p.left.ref, p.right.ref, p)
        for group in report.groups
        for p in group.pairs
        if p.rung == "r1.5"
    ]


def _whole_symbol_pairs(report):
    """Every ClonePair from a rung that hashes whole bodies (R1/R2/R3)."""
    return [
        (p.left.ref, p.right.ref, p)
        for group in report.groups
        for p in group.pairs
        if p.rung in ("r1", "r2", "r3")
    ]


class TestRegionKernelOffByDefault:
    def test_disabled_by_default_finds_no_region_pairs(self, snapshot):
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_clones kind="unit"
        report = find_clones(snapshot, DupConfig(min_tokens=5)).danger_ok
        assert _r1_5_pairs(report) == []

    def test_whole_symbol_rungs_miss_the_partial_clone(self, snapshot):
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::_hash_rung_groups kind="unit"
        # The whole point of this ticket: R1 (exact) and R2 (alpha-rename)
        # hash entire bodies, so alpha_process/beta_transform -- which
        # differ outside their shared block -- never collide on either.
        report = find_clones(snapshot, DupConfig(min_tokens=5)).danger_ok
        whole_symbol_refs = {
            frozenset((a, b)) for a, b, _ in _whole_symbol_pairs(report)
        }
        target = {
            r
            for r in whole_symbol_refs
            if any("alpha_process" in x for x in r)
            and any("beta_transform" in x for x in r)
        }
        assert not target, f"R1/R2/R3 unexpectedly matched the partial clone: {target}"


class TestRegionKernelFindsPartialClone:
    def test_enabled_finds_shared_region_between_otherwise_different_functions(
        self, snapshot
    ):
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::_region_groups kind="unit"
        # frob:tests src/frob/dup/_core.py::_exact_regions kind="unit"
        report = find_clones(
            snapshot,
            DupConfig(min_tokens=5, region_kernel_enabled=True, region_min_tokens=15),
        ).danger_ok
        pairs = _r1_5_pairs(report)
        matched = [
            (a, b, p)
            for a, b, p in pairs
            if ("alpha_process" in a and "beta_transform" in b)
            or ("alpha_process" in b and "beta_transform" in a)
        ]
        assert matched, (
            f"expected an r1.5 region match, got rungs: {[p.rung for _, _, p in pairs]}"
        )
        _, _, pair = matched[0]
        assert pair.similarity == pytest.approx(1.0)
        # The reported span must be a proper sub-range of the whole
        # function, not the whole symbol span (region-granular, not
        # whole-symbol like R1-R3's _pair()) -- both functions span more
        # lines than their shared block.
        left_span_len = pair.left.span[1] - pair.left.span[0]
        right_span_len = pair.right.span[1] - pair.right.span[0]
        assert left_span_len < 10
        assert right_span_len < 10

    def test_min_len_floor_excludes_too_short_a_region(self, snapshot):
        report = find_clones(
            snapshot,
            DupConfig(
                min_tokens=5, region_kernel_enabled=True, region_min_tokens=10_000
            ),
        ).danger_ok
        assert _r1_5_pairs(report) == []
