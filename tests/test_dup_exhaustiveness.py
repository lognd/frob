"""Tests for `frob.dup._exhaustiveness` (T-0199): the (rung x clone-type x
language) matrix registry, plus per-claimed-cell litmus proof that the
named rung actually fires the expected pair -- the T-0158 capability-
matrix mold applied to dup detection.

Every claim below reuses an EXISTING fixture directory already exercised
by `tests/test_dup_rungs.py`/`tests/test_dup_region.py`/
`tests/test_dup_smart.py` -- no new fixtures are authored here (T-0199
scope explicitly reuses, not duplicates, existing dup test infrastructure).

Skips (rather than fails) when `frob_core` is not installed -- same
posture as every other dup rung test file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DupConfig, find_clones, probe_equivalence
from frob.dup import _core as dup_core
from frob.dup._exhaustiveness import (
    CLONE_TYPES,
    DUP_CLAIMS,
    DUP_MATRIX_EXCUSES,
    LANGUAGES,
    RUNG_SPECS,
    dup_matrix,
    unclaimed_cells,
    validate_claim_rungs,
)
from frob.graph import build_graph

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)

FIXTURES = Path(__file__).parent / "fixtures"


def _snapshot(fixture_dir: str, tmp_path: Path):
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURES / fixture_dir, cache)
    assert result.is_ok, result.err
    return result.danger_ok


# frob:waive DUP001 reason="identical tiny CloneReport-flattening helper to \
# tests/test_dup_rungs.py::_pairs -- both are private per-file test utilities over the \
# same report shape (same convention test_dup_region.py uses under different names); \
# not worth a shared conftest fixture for one 4-line comprehension"
def _pairs(report, rung: str):
    return [
        (p.left.ref, p.right.ref, p)
        for group in report.groups
        for p in group.pairs
        if p.rung == rung
    ]


class TestMatrixExhaustiveness:
    # frob:tests src/frob/dup/_exhaustiveness.py::unclaimed_cells kind="unit"
    def test_no_unclaimed_cells(self) -> None:
        """T-0199's core exhaustiveness claim: every (rung, clone_type,
        language) cell the registry puts in play is either claimed (a
        firing litmus fixture) or excused (a written reason). Any
        unclaimed cell fails loudly here."""
        assert unclaimed_cells() == ()

    # frob:tests src/frob/dup/_exhaustiveness.py::dup_matrix kind="unit"
    def test_matrix_covers_every_rung_clone_type_and_language(self) -> None:
        cells = dup_matrix()
        expected = sum(
            len(spec.claimed_clone_types) * len(LANGUAGES) for spec in RUNG_SPECS
        )
        assert len(cells) == expected
        seen = {(c.rung, c.clone_type, c.language) for c in cells}
        for spec in RUNG_SPECS:
            for clone_type in spec.claimed_clone_types:
                for language in LANGUAGES:
                    assert (spec.rung, clone_type, language) in seen

    # frob:tests src/frob/dup/_exhaustiveness.py::dup_matrix kind="unit"
    def test_no_cell_is_both_claimed_and_excused(self) -> None:
        """A cell is excused BECAUSE it has no claim -- both present is a
        drift bug (the excuse should have been removed when the claim
        landed), mirroring the T-0158 capability-matrix precedent."""
        for cell in dup_matrix():
            assert not (cell.claimed and cell.excused)

    # frob:tests src/frob/dup/_exhaustiveness.py::validate_claim_rungs kind="unit"
    def test_every_claim_names_a_registered_rung_and_claimed_type(self) -> None:
        assert validate_claim_rungs() == ()

    def test_every_excuse_names_a_registered_rung_and_claimed_type(self) -> None:
        registered = {
            (spec.rung, ct) for spec in RUNG_SPECS for ct in spec.claimed_clone_types
        }
        for excuse in DUP_MATRIX_EXCUSES:
            assert (excuse.rung, excuse.clone_type) in registered
            assert excuse.language in LANGUAGES

    def test_every_rung_names_only_registered_clone_types(self) -> None:
        for spec in RUNG_SPECS:
            for clone_type in spec.claimed_clone_types:
                assert clone_type in CLONE_TYPES

    def test_every_claim_reason_and_note_nonempty(self) -> None:
        for claim in DUP_CLAIMS:
            assert claim.note
            assert claim.fixture_root
        for excuse in DUP_MATRIX_EXCUSES:
            assert excuse.reason


# ---------------------------------------------------------------------------
# per-claimed-cell fire fixtures (T-0145/T-0158 drift-lock style): each
# `DUP_CLAIMS` entry above must actually fire through `find_clones`/
# `probe_equivalence` over the fixture directory it names -- a claim
# without a firing test is as good as absent.
# ---------------------------------------------------------------------------


class TestMatrixClaimsFire:
    def test_r1_python_type1(self, tmp_path) -> None:
        """mod_r6.py::impure_logger/impure_logger_dup -- byte-identical
        bodies, only the symbol name differs; r1 must claim the pair
        before r2/r3 get a chance (`_hash_rung_groups`'s seen_pairs dedup)."""
        snapshot = _snapshot("dup_rungs", tmp_path)
        report = find_clones(snapshot, DupConfig(min_tokens=1)).danger_ok
        r1 = _pairs(report, "r1")
        matched = [
            (a, b, p)
            for a, b, p in r1
            if ("impure_logger_dup" in a or "impure_logger_dup" in b)
            and ("impure_logger" in a or "impure_logger" in b)
        ]
        assert matched, f"expected an r1 hit for impure_logger[_dup], got: {r1}"
        assert matched[0][2].similarity == 1.0

    def test_r1_5_python_type1(self, tmp_path) -> None:
        """mod_a.py::alpha_process / mod_b.py::beta_transform -- one exact
        6-line region inside two otherwise-different bodies, only visible
        with [dup].region_kernel opted in."""
        snapshot = _snapshot("dup_region", tmp_path)
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, region_kernel_enabled=True)
        ).danger_ok
        r1_5 = _pairs(report, "r1.5")
        matched = [
            (a, b, p)
            for a, b, p in r1_5
            if ("alpha_process" in a or "alpha_process" in b)
            and ("beta_transform" in a or "beta_transform" in b)
        ]
        assert matched, (
            f"expected an r1.5 hit for alpha_process/beta_transform, got: {r1_5}"
        )

    def test_r2_python_type2(self, tmp_path) -> None:
        """mod_a.py::compute_total/compute_sum -- identical shape, renamed
        identifiers."""
        snapshot = _snapshot("dup_smart", tmp_path)
        report = find_clones(snapshot, DupConfig(min_tokens=5)).danger_ok
        r2 = _pairs(report, "r2")
        matched = [
            (a, b, p)
            for a, b, p in r2
            if ("compute_total" in a or "compute_total" in b)
            and ("compute_sum" in a or "compute_sum" in b)
        ]
        assert matched, f"expected an r2 hit for compute_total/compute_sum, got: {r2}"

    @pytest.mark.parametrize(
        "rung,name_a,name_b",
        [
            # mod_r4.py::process_gapped_a/process_gapped_b -- statements
            # inserted/removed between the two bodies (near-miss).
            ("r4", "process_gapped_a", "process_gapped_b"),
            # mod_r5.py::combine_a/combine_b -- reordered but dataflow-
            # identical logic.
            ("r5", "combine_a", "combine_b"),
        ],
    )
    def test_r4_r5_python_type3(
        self, tmp_path, rung: str, name_a: str, name_b: str
    ) -> None:
        snapshot = _snapshot("dup_rungs", tmp_path)
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85)
        ).danger_ok
        pairs = _pairs(report, rung)
        matched = [
            (a, b, p)
            for a, b, p in pairs
            if (name_a in a or name_a in b) and (name_b in a or name_b in b)
        ]
        assert matched, f"expected a {rung} hit for {name_a}/{name_b}, got: {pairs}"

    def test_r6_python_type4(self, tmp_path) -> None:
        """mod_r6.py::add_twice_a/add_twice_b -- different algorithm
        (`x + x` vs `2 * x`), same observed behavior."""
        snapshot = _snapshot("dup_rungs", tmp_path)
        a = "src/mod_r6.py::add_twice_a"
        b = "src/mod_r6.py::add_twice_b"
        result = probe_equivalence(a, b, snapshot, budget_s=1.0)
        assert result.is_ok, result.err
        verdict = result.danger_ok
        assert verdict.equivalent, verdict
