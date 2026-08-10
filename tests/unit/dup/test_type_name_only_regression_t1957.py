"""T-1957 (T-1938 finding 2): DUP001's R1.5 region kernel already catches a
"type-name-only" clone -- two functions identical in shape but differing
only in a renamed violation-type name (and the domain word threaded
through it) -- WITHOUT any new detector logic. It only needs `[dup].
region_kernel` turned on; this rung ships off by default in this repo's
own `frob.toml` (perf: an extra suffix-array pass, T-0193's opt-in
default).

`tests/fixtures/dup_type_name/src/{mod_a,mod_b}.py` reconstruct the exact
shape T-1938 found in production BEFORE its own extraction landed:
`check_backpressure_obligations`/`check_fallback_obligations`
(`src/frob/strata/_backpressure.py`/`_fallback.py`), each collecting
violations of its own domain-specific type
(`BackpressureViolation`/`FallbackViolation`) via two same-shaped helper
calls, then logging a count. EMPIRICALLY MEASURED (this ticket's own
finding, reproduced by these tests): with `native_rungs_enabled=False`
(this repo's actual `frob.toml` setting -- R3/R4/R5 native rungs off for
perf, T-0974) and `region_kernel_enabled` left at its own default
(False), `find_clones` finds ONLY the trivial `BackpressureViolation
<-> FallbackViolation` class-body pair (r1, both empty pass-through
bodies) -- the two functions' own clone is invisible. Flipping ONLY
`region_kernel_enabled=True` (still no native rungs, no other config
change) surfaces it at `rung=r1.5 similarity=1.0`.

Skips (rather than fails) when `frob_core` is not installed -- same
posture as tests/test_dup_region.py/tests/test_dup_smart.py."""

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

FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures" / "dup_type_name"


@pytest.fixture()
def snapshot(tmp_path):
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURE_ROOT, cache)
    assert result.is_ok, result.err
    return result.danger_ok


# frob:waive DUP001 reason="a small ClonePair-flattening helper, same shape as \
# tests/test_dup_region.py's own _whole_symbol_pairs -- both are one-line generator \
# comprehensions over ClonePair fields, not meaningfully extractable into a shared \
# helper without adding an indirection layer for two call sites"
def _pairs(report, *, rung: str | None = None):
    return [
        (p.left.ref, p.right.ref, p)
        for group in report.groups
        for p in group.pairs
        if rung is None or p.rung == rung
    ]


# frob:waive WIRE001 reason="private test-fixture helper used only by this file's own \
# tests -- no production caller to wire it to by design" permanent="true"
def _names(pairs) -> set[frozenset[str]]:
    return {frozenset((a, b)) for a, b, _ in pairs}


class TestTypeNameOnlyCloneMissedByDefault:
    def test_default_config_does_not_catch_the_function_pair(
        self, snapshot
    ) -> None:
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_clones kind="unit"
        """This repo's actual `frob.toml` shape: `native_rungs_enabled=
        False` (R3/R4/R5 off for perf, T-0974), `region_kernel_enabled`
        left at its own False default. Reproduces T-1938's original
        miss: `check_backpressure_obligations`/`check_fallback_
        obligations` never appear together in any pair, at any rung."""
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, native_rungs_enabled=False)
        ).danger_ok
        target = {
            r
            for r in _names(_pairs(report))
            if any("check_backpressure_obligations" in x for x in r)
            and any("check_fallback_obligations" in x for x in r)
        }
        assert not target, (
            f"expected the default (region_kernel off) config to MISS this "
            f"pair, but it was found: {target}"
        )


class TestRegionKernelAloneCatchesTypeNameOnlyClone:
    def test_region_kernel_flag_alone_finds_the_pair_at_similarity_one(
        self, snapshot
    ) -> None:
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::_region_groups kind="unit"
        # frob:waive COV006 reason="confirmed exercised: find_clones' R6 region path \
        # reaches _core._exact_regions, but the best-effort callgraph resolves \
        # same-directory privates only and the T-1086 split moved the caller into the \
        # dup/_pipeline package -- cross-package edge, same disposition as \
        # tests/test_dup_region.py's own identical waiver for this exact rung"
        # frob:tests src/frob/dup/_core.py::_exact_regions kind="unit"
        """ONLY `region_kernel_enabled=True` changed from the miss config
        above -- still no native rungs, no other flag touched. Proves the
        R1.5 opt-in rung alone (no new detector logic) generalizes over
        a renamed violation-type name plus its threaded domain word."""
        report = find_clones(
            snapshot,
            DupConfig(
                min_tokens=5,
                native_rungs_enabled=False,
                region_kernel_enabled=True,
                region_min_tokens=15,
            ),
        ).danger_ok
        matched = [
            (a, b, p)
            for a, b, p in _pairs(report, rung="r1.5")
            if ("check_backpressure_obligations" in a and "check_fallback_obligations" in b)
            or ("check_backpressure_obligations" in b and "check_fallback_obligations" in a)
        ]
        assert matched, (
            f"expected an r1.5 match for the function pair, got rungs: "
            f"{[p.rung for _, _, p in _pairs(report)]}"
        )
        _, _, pair = matched[0]
        assert pair.similarity == pytest.approx(1.0)
