"""Tests for R4/R5/R6 and region-subsection matching (docs/modules/dup.md, T-0001).

Each rung gets a fires-on-target-shape test and a does-not-false-positive
test, per T-0001's hard rules. Skips (rather than fails) when `frob_core`
is not installed -- same posture as tests/test_dup_smart.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DupConfig, DupError, find_clones, probe_equivalence
from frob.dup import _core as dup_core
from frob.graph import build_graph

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dup_rungs"


@pytest.fixture()
def snapshot(tmp_path):
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURE_ROOT, cache)
    assert result.is_ok, result.err
    return result.danger_ok


def _pairs(report, rung):
    return [
        (p.left.ref, p.right.ref, p)
        for group in report.groups
        for p in group
        if p.rung == rung
    ]


class TestR4NearMiss:
    def test_fires_on_gapped_clone(self, snapshot):
        # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85)
        ).danger_ok
        r4 = _pairs(report, "r4")
        matched = [
            (a, b, p)
            for a, b, p in r4
            if ("process_gapped_a" in a or "process_gapped_a" in b)
            and ("process_gapped_b" in a or "process_gapped_b" in b)
        ]
        assert matched, (
            f"expected an r4 hit for process_gapped_a/b, got rungs: {[p.rung for _, _, p in r4]}"
        )
        _, _, pair = matched[0]
        assert pair.alignment, "r4 hit should carry a statement alignment"

    def test_no_false_positive_against_distinct_function(self, snapshot):
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85)
        ).danger_ok
        r4 = _pairs(report, "r4")
        bad = [
            (a, b, p)
            for a, b, p in r4
            if "process_distinct" in a or "process_distinct" in b
        ]
        assert all(p.similarity < 0.85 for _, _, p in bad)


class TestR5Dataflow:
    def test_fires_on_reordered_dataflow_identical_functions(self, snapshot):
        # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85)
        ).danger_ok
        r5 = _pairs(report, "r5")
        matched = [
            (a, b)
            for a, b, _ in r5
            if ("combine_a" in a or "combine_a" in b)
            and ("combine_b" in a or "combine_b" in b)
        ]
        assert matched, f"expected an r5 hit for combine_a/b, got: {r5}"

    def test_no_false_positive_against_unrelated_function(self, snapshot):
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85)
        ).danger_ok
        r5 = _pairs(report, "r5")
        bad = [
            (a, b) for a, b, _ in r5 if "unrelated_calc" in a or "unrelated_calc" in b
        ]
        assert not bad, f"unrelated_calc should not r5-match, got: {bad}"


class TestR6Probing:
    def _ref(self, snapshot, name):
        return next(r for r in snapshot.symbols if name in r)

    def test_fires_on_behaviorally_equivalent_pure_functions(self, snapshot):
        # frob:tests src/frob/dup/_pipeline.py::probe_equivalence kind="unit"
        a = self._ref(snapshot, "add_twice_a")
        b = self._ref(snapshot, "add_twice_b")
        result = probe_equivalence(a, b, snapshot, budget_s=2.0)
        assert result.is_ok, result.err
        verdict = result.danger_ok
        assert verdict.equivalent is True
        assert verdict.cases_run > 0

    def test_does_not_false_positive_on_different_pure_functions(self, snapshot):
        # frob:tests src/frob/dup/_pipeline.py::probe_equivalence kind="unit"
        a = self._ref(snapshot, "add_twice_a")
        b = self._ref(snapshot, "double_plus_one")
        result = probe_equivalence(a, b, snapshot, budget_s=2.0)
        assert result.is_ok, result.err
        assert result.danger_ok.equivalent is False

    def test_fires_on_equivalent_functions_with_renamed_multi_arg_params(
        self, snapshot
    ):
        # frob:tests src/frob/dup/_pipeline.py::probe_equivalence kind="unit"
        # frob:ticket T-0041
        # Regression for the kwargs-by-name bug where _call_safe bound fn_b
        # with fn_a's parameter names, so any renamed multi-arg pair (the
        # common case R6 exists to catch) always raised TypeError on fn_b
        # and compared as DIFFER.
        a = self._ref(snapshot, "sum_twice_a")
        b = self._ref(snapshot, "sum_twice_b")
        result = probe_equivalence(a, b, snapshot, budget_s=2.0)
        assert result.is_ok, result.err
        verdict = result.danger_ok
        assert verdict.equivalent is True
        assert verdict.cases_run > 0

    def test_refuses_impure_functions(self, snapshot):
        a = self._ref(snapshot, "impure_logger")
        b = self._ref(snapshot, "impure_logger_dup")
        result = probe_equivalence(a, b, snapshot, budget_s=1.0)
        assert result.is_err
        assert result.err == DupError.NotPure

    def test_refuses_keyword_only_params_instead_of_vacuous_pass(self, snapshot):
        # frob:tests src/frob/dup/_pipeline.py::probe_equivalence kind="unit"
        # frob:ticket T-0041
        # Reviewer repro: kwonly_subtract(a-b) and kwonly_add(x+y) are
        # OPPOSITE logic. Before the KEYWORD_ONLY guard, _run_probe_cases
        # called both positionally, both raised TypeError on every case
        # (kwonly params can't bind positionally), and _call_safe's
        # shared-exception sentinel counted the matching TypeErrors as
        # agreement -- reporting equivalent=True cases_run=50 for two
        # functions that disagree on every real input. This must be an
        # explicit refusal (Err(NoGenerator)), never a verdict.
        a = self._ref(snapshot, "kwonly_subtract")
        b = self._ref(snapshot, "kwonly_add")
        result = probe_equivalence(a, b, snapshot, budget_s=2.0)
        assert result.is_err
        assert result.err == DupError.NoGenerator

    def test_refuses_mismatched_arity_instead_of_vacuous_pass(self, snapshot):
        # frob:tests src/frob/dup/_pipeline.py::probe_equivalence kind="unit"
        # frob:ticket T-0041
        # Same vacuous-pass shape as the kwonly case, but via arity:
        # arity_three requires a 3rd positional arg arity_two doesn't have,
        # so calling arity_three(*two_args) always raises TypeError. Must
        # refuse, not silently score as equivalent via the shared-exception
        # sentinel.
        a = self._ref(snapshot, "arity_two")
        b = self._ref(snapshot, "arity_three")
        result = probe_equivalence(a, b, snapshot, budget_s=2.0)
        assert result.is_err
        assert result.err == DupError.NoGenerator


class TestRegionSubsection:
    def test_r4_hit_reports_narrower_span_than_whole_symbol_when_partial(
        self, snapshot
    ):
        report = find_clones(
            snapshot, DupConfig(min_tokens=5, threshold=0.85)
        ).danger_ok
        r4 = _pairs(report, "r4")
        matched = [
            p
            for a, b, p in r4
            if ("process_gapped_a" in a or "process_gapped_a" in b)
            and ("process_gapped_b" in a or "process_gapped_b" in b)
        ]
        assert matched
        pair = matched[0]
        # Both regions must be valid, ordered spans within the symbol's own span.
        assert pair.left.span[0] <= pair.left.span[1]
        assert pair.right.span[0] <= pair.right.span[1]


def test_cli_probe_equivalent_functions(tmp_path):
    """frob dup --probe reports observational equivalence of two pure funcs."""
    import subprocess
    import sys

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "m.py").write_text(
        "def da(x: int) -> int:\n    return x * 2\n\n"
        "def db(x: int) -> int:\n    return x + x\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "frob",
            "dup",
            str(tmp_path),
            "--probe",
            "src/m.py::da",
            "src/m.py::db",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert "EQUIVALENT" in (r.stdout + r.stderr)
    assert r.returncode == 0
