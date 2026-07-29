"""Tests for `DupConfig.native_rungs_enabled` (T-0974): gating R3/R4/R5
independently of the whole-symbol rung ladder's cheap R1/R2 pure-Python
rungs, added so the GATE path (`frob.gates.dup_gate`) can ship `[dup].
enforce=true` on for R1/R2 without paying the R3-R5 native-call-per-symbol
cost that made a whole-snapshot cold run exceed this repo's own foreground
check budget (docs/modules/dup.md's "[dup].native_rungs" section,
T-0399/T-0974).

`DupConfig.native_rungs_enabled` itself defaults `True` (preserving R3-R5
always running for every pre-existing direct `find_clones` caller, same
as before this field existed) -- it is `frob.gates._dup_config`'s
`[dup].native_rungs` toml default (absent/false) that actually keeps the
GATE path cheap by default; see that function's docstring.

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

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dup_rungs"


@pytest.fixture()
def snapshot(tmp_path):
    """The shared R4/R5 fixture snapshot (also used by test_dup_rungs.py)."""
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURE_ROOT, cache)
    assert result.is_ok, result.err
    return result.danger_ok


def _rungs_present(report) -> set[str]:
    """Every distinct `ClonePair.rung` string reported."""
    return {p.rung for group in report.groups for p in group.pairs}


class TestNativeRungsDefaultsOnForDirectCallers:
    """`DupConfig()`'s own default is `native_rungs_enabled=True` -- R3-R5
    still fire for any direct `find_clones` caller that does not opt out,
    preserving pre-T-0974 behavior (only the GATE path's frob.toml default
    turns this off; see frob.gates._dup_config)."""

    def test_default_config_still_reports_native_rungs(self, snapshot):
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::_fingerprint_symbol \
        # kind="unit"
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85)
        ).danger_ok
        assert _rungs_present(report) & {"r3", "r4", "r5"}


class TestNativeRungsOffWhenDisabled:
    """R3/R4/R5 never fire when `native_rungs_enabled` is explicitly False
    (the shape `frob.gates.dup_gate` requests by default)."""

    def test_explicit_false_reports_no_native_rungs(self, snapshot):
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::_fingerprint_symbol \
        # kind="unit"
        report = find_clones(
            snapshot,
            DupConfig(min_tokens=5, threshold=0.85, native_rungs_enabled=False),
        ).danger_ok
        assert _rungs_present(report) & {"r3", "r4", "r5"} == set()


class TestNativeRungsEnabled:
    """Enabling `native_rungs_enabled` restores the full R3-R5 ladder,
    matching the always-on behavior test_dup_rungs.py exercises."""

    def test_enabled_finds_the_r4_gapped_clone(self, snapshot):
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_clones kind="unit"
        report = find_clones(
            snapshot,
            DupConfig(min_tokens=5, threshold=0.85, native_rungs_enabled=True),
        ).danger_ok
        r4 = [
            (a, b)
            for group in report.groups
            for p in group.pairs
            if p.rung == "r4"
            for a, b in [(p.left.ref, p.right.ref)]
        ]
        matched = [
            (a, b)
            for a, b in r4
            if ("process_gapped_a" in a or "process_gapped_a" in b)
            and ("process_gapped_b" in a or "process_gapped_b" in b)
        ]
        assert matched, f"expected an r4 hit for process_gapped_a/b, got: {r4}"

    def test_enabled_finds_the_r5_dataflow_clone(self, snapshot):
        # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_clones kind="unit"
        report = find_clones(
            snapshot,
            DupConfig(min_tokens=5, threshold=0.85, native_rungs_enabled=True),
        ).danger_ok
        r5 = [
            (a, b)
            for group in report.groups
            for p in group.pairs
            if p.rung == "r5"
            for a, b in [(p.left.ref, p.right.ref)]
        ]
        matched = [
            (a, b)
            for a, b in r5
            if ("combine_a" in a or "combine_a" in b)
            and ("combine_b" in a or "combine_b" in b)
        ]
        assert matched, f"expected an r5 hit for combine_a/b, got: {r5}"
